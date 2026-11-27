"""Websocket API used by the Lovelace card.

The card prefers this API over entity attributes because it returns the full
shared package document (including history and sibling shipments) without
bloating every state update.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .const import (
    ATTR_ENTRY_ID,
    ATTR_PACKAGE_ID,
    DOMAIN,
    EVENT_PACKAGE_UPDATED,
    VERSION,
)
from .runtime import get_runtimes

WS_PACKAGES = f"{DOMAIN}/packages"
WS_PACKAGE = f"{DOMAIN}/package"
WS_SUBSCRIBE = f"{DOMAIN}/subscribe"

_WS_REGISTERED = f"{DOMAIN}_ws_registered"


def _merge_snapshots(runtimes: list[Any]) -> dict[str, Any]:
    packages: list[dict[str, Any]] = []
    orders: list[dict[str, Any]] = []
    gmail_connected = False
    last_sync: str | None = None
    emails_processed = 0
    account = None
    for runtime in runtimes:
        snapshot = runtime.manager.snapshot(dt_util.utcnow())
        for package in snapshot["packages"]:
            package["config_entry_id"] = runtime.entry.entry_id
            packages.append(package)
        for order in snapshot["orders"]:
            order["config_entry_id"] = runtime.entry.entry_id
            orders.append(order)
        gmail = snapshot.get("gmail", {})
        gmail_connected = gmail_connected or bool(gmail.get("connected"))
        emails_processed += int(gmail.get("emails_processed") or 0)
        if gmail.get("last_sync") and (
            last_sync is None or gmail["last_sync"] > last_sync
        ):
            last_sync = gmail["last_sync"]
        account = account or gmail.get("account")

    packages.sort(
        key=lambda item: (
            item.get("is_terminal", False),
            item.get("expected_delivery") or "9999-12-31",
            item.get("created_at") or "",
        )
    )
    active = [
        package
        for package in packages
        if not package.get("completed") and not package.get("is_terminal")
    ]
    stats = {
        "total": len(packages),
        "active": len(active),
        "in_transit": sum(
            1
            for package in active
            if package.get("status")
            in {"shipped", "in_transit", "out_for_delivery", "delayed"}
        ),
        "delivery_today": sum(
            1
            for package in active
            if package.get("expected_delivery") == dt_util.now().date().isoformat()
        ),
        "delivered_today": sum(
            1
            for package in packages
            if package.get("status") == "delivered"
            and package.get("actual_delivery") == dt_util.now().date().isoformat()
        ),
        "delayed": sum(1 for package in active if package.get("status") == "delayed"),
        "ready_for_pickup": sum(
            1 for package in active if package.get("status") == "ready_for_pickup"
        ),
        "next_delivery": None,
    }
    upcoming = [
        package
        for package in active
        if package.get("expected_delivery")
        and package["expected_delivery"] >= dt_util.now().date().isoformat()
        and package.get("status") != "ready_for_pickup"
    ]
    upcoming.sort(key=lambda item: item.get("expected_delivery") or "9999-12-31")
    if upcoming:
        stats["next_delivery"] = upcoming[0]

    return {
        "version": VERSION,
        "generated_at": dt_util.utcnow().isoformat(),
        "packages": packages,
        "orders": orders,
        "stats": stats,
        "gmail": {
            "connected": gmail_connected,
            "account": account,
            "last_sync": last_sync,
            "emails_processed": emails_processed,
        },
    }


def _runtimes(hass: HomeAssistant, entry_id: str | None) -> list[Any]:
    runtimes = get_runtimes(hass)
    if entry_id:
        runtime = runtimes.get(entry_id)
        return [runtime] if runtime is not None else []
    return list(runtimes.values())


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_PACKAGES,
        vol.Optional(ATTR_ENTRY_ID): str,
    }
)
@websocket_api.async_response
async def websocket_packages(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    runtimes = _runtimes(hass, msg.get(ATTR_ENTRY_ID))
    if not runtimes:
        connection.send_error(msg["id"], "not_found", "Package Tracker ist nicht eingerichtet")
        return
    connection.send_result(msg["id"], _merge_snapshots(runtimes))


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_PACKAGE,
        vol.Required(ATTR_PACKAGE_ID): str,
        vol.Optional(ATTR_ENTRY_ID): str,
    }
)
@websocket_api.async_response
async def websocket_package(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    for runtime in _runtimes(hass, msg.get(ATTR_ENTRY_ID)):
        payload = runtime.manager.package_payload(msg[ATTR_PACKAGE_ID])
        if payload is not None:
            payload["config_entry_id"] = runtime.entry.entry_id
            connection.send_result(msg["id"], payload)
            return
    connection.send_error(msg["id"], "not_found", "Paket nicht gefunden")


@websocket_api.websocket_command(
    {
        vol.Required("type"): WS_SUBSCRIBE,
        vol.Optional(ATTR_ENTRY_ID): str,
    }
)
@callback
def websocket_subscribe(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict[str, Any],
) -> None:
    entry_id = msg.get(ATTR_ENTRY_ID)

    @callback
    def forward_event(event: Any) -> None:
        connection.send_message(
            websocket_api.event_message(msg["id"], event.data)
        )

    unsub = hass.bus.async_listen(EVENT_PACKAGE_UPDATED, forward_event)
    connection.subscriptions[msg["id"]] = unsub
    connection.send_result(msg["id"], {"subscribed": True, "entry_id": entry_id})


async def async_register_websocket_api(hass: HomeAssistant) -> None:
    if hass.data.get(_WS_REGISTERED):
        return
    hass.data[_WS_REGISTERED] = True
    websocket_api.async_register_command(hass, websocket_packages)
    websocket_api.async_register_command(hass, websocket_package)
    websocket_api.async_register_command(hass, websocket_subscribe)
