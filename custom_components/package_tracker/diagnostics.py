"""Diagnostics support with redaction of secrets and PII."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.redact import async_redact_data
from homeassistant.util import dt as dt_util

from .const import DOMAIN, VERSION
from .runtime import get_runtime
from .util import mask_email, mask_tracking

TO_REDACT = {
    "access_token",
    "refresh_token",
    "token",
    "client_secret",
    "tracking_api_key",
    "tracking_header_value",
    "api_key",
    "authorization",
    "password",
    "id_token",
    "gmail_account",
    "emailAddress",
    "email",
}


def _redact_package(package: dict[str, Any]) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in package.items()
        if key
        not in {
            "emails",
            "order",
            "siblings",
            "tracking_url",
            "config_entry_id",
            "last_email_subject",
        }
    }
    payload["tracking_number"] = mask_tracking(package.get("tracking_number"))
    payload["email_count"] = len(package.get("emails") or [])
    history = []
    for event in package.get("status_history") or []:
        if isinstance(event, dict):
            history.append(
                {
                    "status": event.get("status"),
                    "timestamp": event.get("timestamp"),
                    "source": event.get("source"),
                }
            )
    payload["status_history"] = history
    tracking = package.get("tracking")
    if isinstance(tracking, dict):
        payload["tracking"] = {
            "provider": tracking.get("provider"),
            "last_checked": tracking.get("last_checked"),
            "status": tracking.get("status"),
            "error": tracking.get("error"),
            "event_count": len(tracking.get("events") or []),
        }
    return payload


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    runtime = get_runtime(hass, entry.entry_id)
    if runtime is None:
        return {"error": "runtime_unavailable"}
    snapshot = runtime.manager.snapshot(dt_util.utcnow())
    return {
        "version": VERSION,
        "domain": DOMAIN,
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "gmail": {
            "account": mask_email(runtime.manager.gmail_account),
            "last_sync": runtime.manager.last_sync,
            "processed_emails": len(runtime.manager.processed_emails),
            "connected": bool(runtime.manager.gmail_account),
        },
        "storage": {
            "orders": len(runtime.manager.orders),
            "packages": len(runtime.manager.shipments),
            "notifications_sent": len(runtime.manager.last_notified),
        },
        "stats": snapshot["stats"],
        "packages": [
            _redact_package(package) for package in snapshot["packages"]
        ],
        "orders": [
            {
                "id": order.get("id"),
                "merchant": order.get("merchant"),
                "order_number": order.get("order_number"),
                "status": order.get("status"),
                "shipment_count": len(order.get("shipment_ids") or []),
            }
            for order in snapshot["orders"]
        ],
        "coordinator": {
            "last_update_success": runtime.coordinator.last_update_success,
            "last_exception": type(runtime.coordinator.last_exception).__name__
            if runtime.coordinator.last_exception
            else None,
            "sync": runtime.coordinator.last_summary,
        },
    }
