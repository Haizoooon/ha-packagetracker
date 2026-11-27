"""DataUpdateCoordinator for Package Tracker."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_GMAIL_QUERY,
    CONF_INITIAL_SYNC_DAYS,
    CONF_MAX_MESSAGES,
    CONF_ORDER_PLACEHOLDER_DAYS,
    CONF_RETENTION_DAYS,
    CONF_STORE_EMAIL_SUBJECTS,
    CONF_SYNC_INTERVAL,
    DEFAULT_INITIAL_SYNC_DAYS,
    DEFAULT_MAX_MESSAGES,
    DEFAULT_ORDER_PLACEHOLDER_DAYS,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_SYNC_INTERVAL,
    DOMAIN,
    EVENT_PACKAGE_UPDATED,
)
from .email_parser import EmailParser
from .gmail_client import (
    GmailAuthError,
    GmailClient,
    GmailConnectionError,
    GmailError,
    GmailQueryError,
    GmailRateLimitError,
    GmailScopeError,
)
from .models import PackageChange
from .notifications import async_handle_notifications, fire_package_events
from .package_manager import PackageManager
from .storage import PackageTrackerStore
from .tracking import async_refresh_tracking
from .util import parse_iso, utcnow_iso

_LOGGER = logging.getLogger(__name__)


class PackageTrackerCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Single data source for all entities, services and the dashboard."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        manager: PackageManager,
        store: PackageTrackerStore,
        gmail: GmailClient | None,
        *,
        setup_error: str | None = None,
    ) -> None:
        self.entry = entry
        self.manager = manager
        self.store = store
        self.gmail = gmail
        self.options: dict[str, Any] = {**entry.options}
        self._tz = dt_util.get_time_zone(hass.config.time_zone) or dt_util.UTC
        self._lock = asyncio.Lock()
        self._force_next = False
        self._setup_error = setup_error
        self.last_summary: dict[str, Any] = {
            "messages_fetched": 0,
            "messages_processed": 0,
            "packages_found": 0,
            "packages_updated": 0,
            "tracking_updates": 0,
            "errors": 0,
        }
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=self._interval(),
            config_entry=entry,
            always_update=False,
        )

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    @property
    def sync_interval_minutes(self) -> int:
        try:
            return max(1, min(int(self.options.get(CONF_SYNC_INTERVAL, DEFAULT_SYNC_INTERVAL)), 1440))
        except (TypeError, ValueError):
            return DEFAULT_SYNC_INTERVAL

    def _interval(self) -> timedelta:
        try:
            minutes = max(
                1,
                min(
                    int(self.options.get(CONF_SYNC_INTERVAL, DEFAULT_SYNC_INTERVAL)),
                    1440,
                ),
            )
        except (TypeError, ValueError):
            minutes = DEFAULT_SYNC_INTERVAL
        return timedelta(minutes=minutes)

    def apply_options(self, options: dict[str, Any]) -> None:
        """Apply changed options without reloading the whole entry."""
        previous = self.options
        self.options = dict(options)
        self.update_interval = self._interval()
        self.manager.store_email_subjects = bool(
            options.get(CONF_STORE_EMAIL_SUBJECTS, True)
        )
        try:
            self.manager.order_placeholder_days = max(
                0,
                int(
                    options.get(
                        CONF_ORDER_PLACEHOLDER_DAYS,
                        DEFAULT_ORDER_PLACEHOLDER_DAYS,
                    )
                    or 0
                ),
            )
        except (TypeError, ValueError):
            self.manager.order_placeholder_days = DEFAULT_ORDER_PLACEHOLDER_DAYS
        if options.get(CONF_STORE_EMAIL_SUBJECTS, True) != previous.get(
            CONF_STORE_EMAIL_SUBJECTS, True
        ):
            # Remove already stored subjects when the user turns this off.
            if not options.get(CONF_STORE_EMAIL_SUBJECTS, True):
                for shipment in self.manager.iter_shipments():
                    shipment.last_email_subject = None
                    for email in shipment.emails:
                        email.subject = None
                for order in self.manager.orders.values():
                    for email in order.emails:
                        email.subject = None
                self.hass.async_create_task(self._async_save())
        _LOGGER.debug("Package Tracker options updated")

    # ------------------------------------------------------------------
    # Data update
    # ------------------------------------------------------------------

    async def _async_update_data(self) -> dict[str, Any]:
        if self._setup_error:
            raise UpdateFailed(self._setup_error)

        async with self._lock:
            force = self._force_next
            self._force_next = False
            summary = {
                "messages_fetched": 0,
                "messages_processed": 0,
                "packages_found": 0,
                "packages_updated": 0,
                "tracking_updates": 0,
                "errors": 0,
            }
            changes: list[PackageChange] = []
            now = dt_util.utcnow()

            if self.gmail is not None:
                changes.extend(await self._async_sync_gmail(summary))

            try:
                tracking_changes = await async_refresh_tracking(
                    self.hass,
                    self.manager,
                    self.options,
                    force=force,
                )
            except Exception as err:  # noqa: BLE001 - tracking is optional
                _LOGGER.warning(
                    "Tracking refresh failed without affecting Gmail sync: %s",
                    type(err).__name__,
                )
                summary["errors"] += 1
            else:
                if tracking_changes:
                    changes.extend(tracking_changes)
                    summary["tracking_updates"] += len(tracking_changes)

            try:
                removed = self.manager.purge_terminal(
                    int(self.options.get(CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS) or 0),
                    dt_util.now(),
                )
                stale = self.manager.purge_stale_order_placeholders(
                    int(
                        self.options.get(
                            CONF_ORDER_PLACEHOLDER_DAYS,
                            DEFAULT_ORDER_PLACEHOLDER_DAYS,
                        )
                        or 0
                    ),
                    dt_util.utcnow(),
                )
                if removed or stale:
                    _LOGGER.debug(
                        "Removed %s old terminal packages and %s stale order placeholders",
                        removed,
                        stale,
                    )
            except (TypeError, ValueError):
                pass

            if changes:
                summary["packages_found"] = sum(1 for change in changes if change.created)
                summary["packages_updated"] = sum(
                    1 for change in changes if not change.created
                )
                fire_package_events(self.hass, changes)
                await async_handle_notifications(
                    self.hass, self.manager, changes, self.options
                )

            await self._async_save()
            snapshot = self.manager.snapshot(now)
            snapshot["sync"] = summary
            self.last_summary = summary
            if changes or summary["messages_processed"]:
                self.hass.bus.async_fire(
                    EVENT_PACKAGE_UPDATED,
                    {
                        "packages": snapshot["stats"],
                        "changes": len(changes),
                        "messages_processed": summary["messages_processed"],
                        "last_sync": snapshot["gmail"]["last_sync"],
                    },
                )
            return snapshot

    async def _async_sync_gmail(self, summary: dict[str, Any]) -> list[PackageChange]:
        assert self.gmail is not None
        last_sync = parse_iso(self.manager.last_sync)
        try:
            fetch = await self.gmail.async_fetch_messages(
                last_sync=last_sync,
                base_query=self.options.get(CONF_GMAIL_QUERY),
                initial_days=int(
                    self.options.get(CONF_INITIAL_SYNC_DAYS, DEFAULT_INITIAL_SYNC_DAYS)
                ),
                max_messages=int(
                    self.options.get(CONF_MAX_MESSAGES, DEFAULT_MAX_MESSAGES)
                ),
            )
        except GmailAuthError as err:
            self._async_create_issue("auth", "Gmail-Zugriff wurde verweigert")
            raise ConfigEntryAuthFailed(str(err)) from err
        except GmailScopeError as err:
            self._async_create_issue(
                "scope", "Gmail-Leseberechtigung fehlt"
            )
            raise ConfigEntryAuthFailed(str(err)) from err
        except GmailRateLimitError as err:
            raise UpdateFailed(f"Gmail Rate Limit: {err}") from err
        except GmailQueryError as err:
            raise UpdateFailed(f"Invalid Gmail search query: {err}") from err
        except GmailConnectionError as err:
            raise UpdateFailed(f"Gmail unreachable: {err}") from err
        except GmailError as err:
            raise UpdateFailed(f"Gmail error: {err}") from err

        summary["messages_fetched"] = len(fetch.messages)
        parser = EmailParser(self._tz)
        changes: list[PackageChange] = []
        for message in fetch.messages:
            if self.manager.was_processed(message.id):
                continue
            try:
                parsed = parser.parse(message)
            except Exception as err:  # noqa: BLE001 - one bad mail must not stop sync
                summary["errors"] += 1
                _LOGGER.warning(
                    "Could not parse Gmail message %s (%s); skipping it",
                    message.id,
                    type(err).__name__,
                )
                self.manager.mark_processed(message.id, message.received_at.isoformat())
                continue
            if parsed is None:
                _LOGGER.debug(
                    "Ignored Gmail message %s (no parcel signal)", message.id
                )
                self.manager.mark_processed(message.id, message.received_at.isoformat())
                continue
            _LOGGER.debug(
                "Parsed Gmail message %s as %s (merchant=%s carrier=%s products=%s tracking=%s)",
                message.id,
                parsed.kind,
                parsed.merchant,
                parsed.carrier,
                len(parsed.product_names),
                len(parsed.tracking_numbers),
            )
            try:
                changes.extend(self.manager.apply_parsed(parsed))
                summary["messages_processed"] += 1
            except Exception as err:  # noqa: BLE001
                summary["errors"] += 1
                _LOGGER.warning(
                    "Could not merge Gmail message %s (%s); skipping it",
                    message.id,
                    type(err).__name__,
                )
                self.manager.mark_processed(message.id, message.received_at.isoformat())

        self.manager.last_sync = utcnow_iso()
        if fetch.truncated:
            _LOGGER.warning(
                "Gmail returned more messages than the configured limit (%s). "
                "Increase 'max_messages_per_sync' if packages are missing.",
                self.options.get(CONF_MAX_MESSAGES, DEFAULT_MAX_MESSAGES),
            )
        self._async_delete_issue("auth")
        self._async_delete_issue("scope")
        return changes

    # ------------------------------------------------------------------
    # Public actions
    # ------------------------------------------------------------------

    async def async_manual_sync(self) -> dict[str, Any]:
        self._force_next = True
        await self.async_refresh()
        if not self.last_update_success:
            error = self.last_exception
            raise HomeAssistantError(
                f"Gmail synchronization failed: {error}"
                if error
                else "Gmail synchronization failed"
            )
        return {
            "ok": True,
            "last_sync": self.data.get("gmail", {}).get("last_sync") if self.data else None,
            **self.last_summary,
        }

    async def async_apply_changes(self, changes: list[PackageChange]) -> None:
        """Persist and publish manual changes from services."""
        if changes:
            fire_package_events(self.hass, changes)
            await async_handle_notifications(
                self.hass, self.manager, changes, self.options
            )
        await self._async_save()
        snapshot = self.manager.snapshot(dt_util.utcnow())
        snapshot["sync"] = self.last_summary
        self.async_set_updated_data(snapshot)
        self.hass.bus.async_fire(
            EVENT_PACKAGE_UPDATED,
            {
                "packages": snapshot["stats"],
                "changes": len(changes),
                "messages_processed": 0,
                "last_sync": snapshot["gmail"]["last_sync"],
            },
        )

    async def async_refresh_tracking_now(
        self, package_id: str | None = None
    ) -> list[PackageChange]:
        changes = await async_refresh_tracking(
            self.hass,
            self.manager,
            self.options,
            force=True,
            only_package_id=package_id,
        )
        await self.async_apply_changes(changes)
        return changes

    async def async_mark_delivered(
        self, package_id: str, delivered_at: str | None = None
    ) -> PackageChange | None:
        change = self.manager.mark_delivered(package_id, delivered_at)
        if change is not None:
            await self.async_apply_changes([change])
        return change

    async def async_mark_completed(self, package_id: str, completed: bool = True) -> None:
        if self.manager.mark_completed(package_id, completed) is not None:
            await self.async_apply_changes([])

    async def async_update_package(self, package_id: str, **fields: Any) -> None:
        change = self.manager.update_shipment(package_id, **fields)
        await self.async_apply_changes([change] if change is not None else [])

    async def async_delete_package(self, package_id: str) -> bool:
        shipment = self.manager.delete_shipment(package_id)
        if shipment is None:
            return False
        self.hass.bus.async_fire(
            f"{DOMAIN}_package_deleted",
            {"package_id": package_id, "package": shipment.to_dict()},
        )
        await self.async_apply_changes([])
        return True

    async def async_delete_all(self, *, reset_sync: bool = False) -> None:
        self.manager.clear(reset_sync=reset_sync)
        await self._async_save()
        snapshot = self.manager.snapshot(dt_util.utcnow())
        snapshot["sync"] = self.last_summary
        self.async_set_updated_data(snapshot)
        self.hass.bus.async_fire(
            EVENT_PACKAGE_UPDATED,
            {
                "packages": snapshot["stats"],
                "changes": 0,
                "messages_processed": 0,
                "last_sync": snapshot["gmail"]["last_sync"],
            },
        )

    async def _async_save(self) -> None:
        try:
            await self.store.async_save(self.manager.to_dict())
        except OSError as err:
            _LOGGER.error("Could not save Package Tracker data: %s", type(err).__name__)
        except Exception as err:
            _LOGGER.exception("Unexpected error saving Package Tracker data: %s", type(err).__name__)

    async def async_shutdown(self) -> None:
        await super().async_shutdown()
        await self._async_save()

    # ------------------------------------------------------------------
    # Issues
    # ------------------------------------------------------------------

    def _async_create_issue(self, issue_id: str, message: str) -> None:
        ir.async_create_issue(
            self.hass,
            DOMAIN,
            f"{issue_id}_{self.entry.entry_id}",
            is_fixable=True,
            is_persistent=True,
            severity=ir.IssueSeverity.ERROR,
            translation_key=issue_id,
            translation_placeholders={
                "entry": self.entry.title,
                "message": message,
            },
            data={"entry_id": self.entry.entry_id, "issue": issue_id},
        )

    def _async_delete_issue(self, issue_id: str) -> None:
        ir.async_delete_issue(self.hass, DOMAIN, f"{issue_id}_{self.entry.entry_id}")


__all__ = ["PackageTrackerCoordinator"]
