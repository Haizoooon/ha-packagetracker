"""Package Tracker – intelligent parcel tracking for Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.config_entry_oauth2_flow import OAuth2Session
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_GMAIL_ACCOUNT,
    CONF_ORDER_PLACEHOLDER_DAYS,
    CONF_REDIRECT_URI,
    CONF_STORE_EMAIL_SUBJECTS,
    CONF_TOKEN,
    DEFAULT_ORDER_PLACEHOLDER_DAYS,
    DOMAIN,
    NAME,
    VERSION,
)
from .coordinator import PackageTrackerCoordinator
from .gmail_client import GmailClient
from .oauth import (
    GoogleOAuth2Implementation,
    NoRedirectUriError,
    async_revoke_token,
    resolve_redirect_uri,
)
from .package_manager import PackageManager
from .runtime import EntryRuntime, get_runtimes
from .services import async_setup_services, async_unload_services
from .storage import PackageTrackerStore
from .util import mask_email
from .websocket import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
]

FRONTEND_URL_PATH = "/package_tracker_static"
FRONTEND_FILE = "package-tracker-card.js"
FRONTEND_REGISTERED = f"{DOMAIN}_frontend_registered"
FRONTEND_STATIC_REGISTERED = f"{DOMAIN}_frontend_static_registered"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    await async_setup_services(hass)
    await async_register_websocket_api(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    await async_setup_services(hass)
    await async_register_websocket_api(hass)
    await _async_setup_frontend(hass)

    client_id = entry.data.get(CONF_CLIENT_ID)
    client_secret = entry.data.get(CONF_CLIENT_SECRET)
    token = entry.data.get(CONF_TOKEN)
    if not client_id or not client_secret or not token:
        raise ConfigEntryAuthFailed("Google OAuth-Zugangsdaten fehlen")

    try:
        redirect_uri = entry.data.get(CONF_REDIRECT_URI) or resolve_redirect_uri(hass)
    except NoRedirectUriError:
        redirect_uri = ""

    implementation = GoogleOAuth2Implementation(
        hass, str(client_id), str(client_secret), redirect_uri
    )
    session = OAuth2Session(hass, entry, implementation)
    gmail = GmailClient(hass, session)

    store = PackageTrackerStore(hass, entry.entry_id)
    load_result = await store.async_load()
    if load_result.error:
        ir.async_create_issue(
            hass,
            DOMAIN,
            f"storage_{entry.entry_id}",
            is_fixable=False,
            is_persistent=True,
            severity=ir.IssueSeverity.WARNING,
            translation_key="storage_corrupt",
            translation_placeholders={"entry": entry.title},
        )
    else:
        ir.async_delete_issue(hass, DOMAIN, f"storage_{entry.entry_id}")
    tz = dt_util.get_time_zone(hass.config.time_zone) or dt_util.UTC
    manager = PackageManager.from_dict(
        load_result.data,
        store_email_subjects=bool(entry.options.get(CONF_STORE_EMAIL_SUBJECTS, True)),
        tz=tz,
        order_placeholder_days=int(
            entry.options.get(
                CONF_ORDER_PLACEHOLDER_DAYS, DEFAULT_ORDER_PLACEHOLDER_DAYS
            )
        ),
    )
    manager.gmail_account = entry.data.get(CONF_GMAIL_ACCOUNT) or manager.gmail_account

    manager.purge_stale_order_placeholders(
        int(
            entry.options.get(
                CONF_ORDER_PLACEHOLDER_DAYS, DEFAULT_ORDER_PLACEHOLDER_DAYS
            )
        ),
        dt_util.utcnow(),
    )
    coordinator = PackageTrackerCoordinator(
        hass, entry, manager, store, gmail
    )
    runtime = EntryRuntime(
        entry=entry,
        coordinator=coordinator,
        manager=manager,
        gmail=gmail,
        implementation=implementation,
        store=store,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime

    try:
        # Validate the token / fetch the account and perform the initial sync.
        if not manager.gmail_account:
            profile = await gmail.async_get_profile()
            account = profile.get("emailAddress")
            if account:
                manager.gmail_account = str(account)
                hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_GMAIL_ACCOUNT: str(account)},
                )
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        raise
    except ConfigEntryAuthFailed:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        raise
    except Exception as err:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        raise ConfigEntryNotReady(
            f"Package Tracker konnte nicht gestartet werden: {type(err).__name__}"
        ) from err

    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, entry.entry_id)},
        name=NAME,
        manufacturer=NAME,
        model="Gmail",
        entry_type=dr.DeviceEntryType.SERVICE,
        sw_version=VERSION,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    _LOGGER.info(
        "Package Tracker started for %s with %s packages",
        mask_email(manager.gmail_account) or "Gmail",
        len(manager.shipments),
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    runtime = get_runtimes(hass).get(entry.entry_id)
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if runtime is not None:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
        await runtime.coordinator.async_shutdown()
    if unload_ok and not get_runtimes(hass):
        await async_unload_services(hass)
        await _async_remove_frontend(hass)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete local package data and revoke the Google token."""
    store = PackageTrackerStore(hass, entry.entry_id)
    await store.async_delete()
    await async_revoke_token(hass, entry.data.get(CONF_TOKEN))
    for issue_id in ("auth", "scope", "storage"):
        ir.async_delete_issue(hass, DOMAIN, f"{issue_id}_{entry.entry_id}")
    _LOGGER.info("Package Tracker entry removed and local data deleted")


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    _LOGGER.debug("Migrating Package Tracker entry from version %s", entry.version)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    runtime = get_runtimes(hass).get(entry.entry_id)
    if runtime is None:
        return
    runtime.coordinator.apply_options(dict(entry.options))


async def _async_setup_frontend(hass: HomeAssistant) -> None:
    if hass.data.get(FRONTEND_REGISTERED):
        return
    path = Path(__file__).parent / "frontend" / FRONTEND_FILE
    if not path.is_file():
        _LOGGER.warning(
            "Package Tracker frontend bundle is missing at %s; the card is not registered",
            path,
        )
        return
    asset_url = f"{FRONTEND_URL_PATH}/{FRONTEND_FILE}"
    if not hass.data.get(FRONTEND_STATIC_REGISTERED):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(asset_url, str(path), cache_headers=False)]
        )
        hass.data[FRONTEND_STATIC_REGISTERED] = True
    if "frontend" not in hass.config.components:
        _LOGGER.debug("Frontend not loaded; package tracker card resource not added yet")
        return
    try:
        from homeassistant.components import frontend

        frontend.add_extra_js_url(hass, f"{asset_url}?v={VERSION}")
    except (ImportError, AttributeError, KeyError):
        _LOGGER.warning("Home Assistant frontend is not available; card not auto-loaded")
        return
    hass.data[FRONTEND_REGISTERED] = True


async def _async_remove_frontend(hass: HomeAssistant) -> None:
    if not hass.data.pop(FRONTEND_REGISTERED, None):
        return
    try:
        from homeassistant.components import frontend

        frontend.remove_extra_js_url(
            hass, f"{FRONTEND_URL_PATH}/{FRONTEND_FILE}?v={VERSION}"
        )
    except (ImportError, AttributeError, KeyError, ValueError):
        pass
