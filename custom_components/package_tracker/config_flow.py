"""Config and options flow for Package Tracker."""

from __future__ import annotations

import logging
import time
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import selector

from .const import (
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_GMAIL_ACCOUNT,
    CONF_GMAIL_QUERY,
    CONF_INITIAL_SYNC_DAYS,
    CONF_MAX_MESSAGES,
    CONF_NOTIFY_EVENTS,
    CONF_NOTIFY_SERVICE,
    CONF_REDIRECT_URI,
    CONF_RETENTION_DAYS,
    CONF_STORE_EMAIL_SUBJECTS,
    CONF_SYNC_INTERVAL,
    CONF_TOKEN,
    CONF_TRACKING_API_KEY,
    CONF_TRACKING_EVENT_TEXT_PATH,
    CONF_TRACKING_EVENT_TIME_PATH,
    CONF_TRACKING_EVENTS_PATH,
    CONF_TRACKING_EXPECTED_PATH,
    CONF_TRACKING_HEADER,
    CONF_TRACKING_HEADER_VALUE,
    CONF_TRACKING_INTERVAL,
    CONF_TRACKING_PROVIDER,
    CONF_TRACKING_STATUS_PATH,
    CONF_TRACKING_URL,
    DEFAULT_GMAIL_QUERY,
    DEFAULT_INITIAL_SYNC_DAYS,
    DEFAULT_MAX_MESSAGES,
    DEFAULT_NOTIFY_EVENTS,
    DEFAULT_RETENTION_DAYS,
    DEFAULT_SYNC_INTERVAL,
    DEFAULT_TRACKING_INTERVAL,
    DOMAIN,
    NAME,
    NOTIFY_EVENT_OPTIONS,
    TRACKING_PROVIDER_CUSTOM,
    TRACKING_PROVIDER_DHL,
    TRACKING_PROVIDER_NONE,
)
from .gmail_client import (
    GmailAuthError,
    GmailConnectionError,
    GmailError,
    GmailScopeError,
    async_probe_account,
)
from .oauth import GoogleOAuth2Implementation, NoRedirectUriError, resolve_redirect_uri

_LOGGER = logging.getLogger(__name__)


def _default_options() -> dict[str, Any]:
    return {
        CONF_SYNC_INTERVAL: DEFAULT_SYNC_INTERVAL,
        CONF_INITIAL_SYNC_DAYS: DEFAULT_INITIAL_SYNC_DAYS,
        CONF_GMAIL_QUERY: DEFAULT_GMAIL_QUERY,
        CONF_MAX_MESSAGES: DEFAULT_MAX_MESSAGES,
        CONF_STORE_EMAIL_SUBJECTS: True,
        CONF_RETENTION_DAYS: DEFAULT_RETENTION_DAYS,
        CONF_NOTIFY_SERVICE: "",
        CONF_NOTIFY_EVENTS: list(DEFAULT_NOTIFY_EVENTS),
        CONF_TRACKING_PROVIDER: TRACKING_PROVIDER_NONE,
        CONF_TRACKING_API_KEY: "",
        CONF_TRACKING_INTERVAL: DEFAULT_TRACKING_INTERVAL,
        CONF_TRACKING_URL: "",
        CONF_TRACKING_HEADER: "",
        CONF_TRACKING_HEADER_VALUE: "",
        CONF_TRACKING_STATUS_PATH: "status",
        CONF_TRACKING_EXPECTED_PATH: "",
        CONF_TRACKING_EVENTS_PATH: "events",
        CONF_TRACKING_EVENT_TIME_PATH: "timestamp",
        CONF_TRACKING_EVENT_TEXT_PATH: "description",
    }


def _number_selector(minimum: int, maximum: int, unit: str | None = None) -> selector.NumberSelector:
    config = {
        "min": minimum,
        "max": maximum,
        "mode": selector.NumberSelectorMode.BOX,
    }
    if unit is not None:
        config["unit_of_measurement"] = unit
    return selector.NumberSelector(selector.NumberSelectorConfig(**config))


def _select(
    options: list[selector.SelectOptionDict],
    *,
    multiple: bool = False,
    custom_value: bool = False,
) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            multiple=multiple,
            custom_value=custom_value,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _settings_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_SYNC_INTERVAL,
                default=defaults.get(CONF_SYNC_INTERVAL, DEFAULT_SYNC_INTERVAL),
            ): _number_selector(1, 1440, "min"),
            vol.Required(
                CONF_INITIAL_SYNC_DAYS,
                default=defaults.get(CONF_INITIAL_SYNC_DAYS, DEFAULT_INITIAL_SYNC_DAYS),
            ): _number_selector(1, 365, "Tage"),
            vol.Optional(
                CONF_NOTIFY_SERVICE,
                default=defaults.get(CONF_NOTIFY_SERVICE, ""),
            ): cv.string,
            vol.Optional(
                CONF_NOTIFY_EVENTS,
                default=defaults.get(CONF_NOTIFY_EVENTS, list(DEFAULT_NOTIFY_EVENTS)),
            ): _select(
                [
                    selector.SelectOptionDict(value=value, label=label)
                    for value, label in NOTIFY_EVENT_OPTIONS.items()
                ],
                multiple=True,
            ),
        }
    )


class PackageTrackerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the initial Google OAuth setup."""

    VERSION = 1

    def __init__(self) -> None:
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._redirect_uri: str | None = None
        self._implementation: GoogleOAuth2Implementation | None = None
        self._external_data: dict[str, Any] | None = None
        self._token: dict[str, Any] | None = None
        self._profile: dict[str, Any] | None = None
        self._reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            client_id = str(user_input.get(CONF_CLIENT_ID, "")).strip()
            client_secret = str(user_input.get(CONF_CLIENT_SECRET, "")).strip()
            if not client_id or not client_secret:
                errors["base"] = "invalid_credentials"
            elif not client_id.endswith(".apps.googleusercontent.com"):
                errors["base"] = "invalid_client_id"
            else:
                try:
                    redirect_uri = resolve_redirect_uri(self.hass)
                except NoRedirectUriError:
                    errors["base"] = "no_url_available"
                else:
                    self._client_id = client_id
                    self._client_secret = client_secret
                    self._redirect_uri = redirect_uri
                    self._implementation = GoogleOAuth2Implementation(
                        self.hass, client_id, client_secret, redirect_uri
                    )
                    try:
                        url = await self._implementation.async_generate_authorize_url(
                            self.flow_id
                        )
                    except (TimeoutError, NoRedirectUriError):
                        errors["base"] = "no_url_available"
                    else:
                        return self.async_external_step(step_id="auth", url=url)

        redirect_hint = ""
        try:
            redirect_hint = resolve_redirect_uri(self.hass)
        except NoRedirectUriError:
            pass
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CLIENT_ID): cv.string,
                    vol.Required(CONF_CLIENT_SECRET): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                }
            ),
            errors=errors,
            description_placeholders={
                "redirect_uri": redirect_hint
                or "https://my.home-assistant.io/redirect/oauth",
            },
        )

    async def async_step_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is None:
            if self._implementation is None:
                return self.async_abort(reason="oauth_failed")
            url = await self._implementation.async_generate_authorize_url(self.flow_id)
            return self.async_external_step(step_id="auth", url=url)
        if "error" in user_input:
            return self.async_abort(
                reason="oauth_denied",
                description_placeholders={"error": str(user_input.get("error"))},
            )
        self._external_data = user_input
        return self.async_external_step_done(next_step_id="creation")

    async def async_step_creation(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if self._implementation is None or self._external_data is None:
            return self.async_abort(reason="oauth_failed")
        try:
            token = await self._implementation.async_resolve_external_data(
                self._external_data
            )
        except Exception as err:  # noqa: BLE001 - map to a safe abort reason
            _LOGGER.warning("OAuth token exchange failed: %s", type(err).__name__)
            return self.async_abort(reason="oauth_failed")
        if not isinstance(token, dict) or not token.get("access_token"):
            return self.async_abort(reason="oauth_failed")
        if not token.get("refresh_token"):
            return self.async_abort(reason="no_refresh_token")
        try:
            token["expires_in"] = int(token["expires_in"])
        except (KeyError, TypeError, ValueError):
            return self.async_abort(reason="oauth_failed")
        token["expires_at"] = time.time() + token["expires_in"]
        try:
            profile = await async_probe_account(self.hass, token)
        except GmailScopeError:
            return self.async_abort(reason="missing_scope")
        except GmailAuthError:
            return self.async_abort(reason="oauth_failed")
        except GmailConnectionError:
            return self.async_abort(reason="cannot_connect")
        except GmailError as err:
            _LOGGER.warning("Gmail probe failed: %s", err)
            return self.async_abort(reason="oauth_failed")

        account = str(profile.get("emailAddress") or "")
        if not account:
            return self.async_abort(reason="oauth_failed")
        await self.async_set_unique_id(account.casefold())
        self._abort_if_unique_id_configured()
        self._token = token
        self._profile = profile
        return await self.async_step_settings()

    async def async_step_settings(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if self._token is None or self._profile is None:
            return self.async_abort(reason="oauth_failed")
        account = str(self._profile.get("emailAddress"))
        if user_input is not None:
            options = _default_options()
            options[CONF_SYNC_INTERVAL] = int(
                user_input.get(CONF_SYNC_INTERVAL, DEFAULT_SYNC_INTERVAL)
            )
            options[CONF_INITIAL_SYNC_DAYS] = int(
                user_input.get(CONF_INITIAL_SYNC_DAYS, DEFAULT_INITIAL_SYNC_DAYS)
            )
            options[CONF_NOTIFY_SERVICE] = str(
                user_input.get(CONF_NOTIFY_SERVICE) or ""
            ).strip()
            options[CONF_NOTIFY_EVENTS] = list(
                user_input.get(CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS)
            )
            return self.async_create_entry(
                title=f"{NAME} ({account})",
                data={
                    CONF_CLIENT_ID: self._client_id,
                    CONF_CLIENT_SECRET: self._client_secret,
                    CONF_REDIRECT_URI: self._redirect_uri,
                    CONF_TOKEN: self._token,
                    CONF_GMAIL_ACCOUNT: account,
                },
                options=options,
            )
        return self.async_show_form(
            step_id="settings",
            data_schema=_settings_schema(_default_options()),
            description_placeholders={"account": account},
        )

    # ------------------------------------------------------------------
    # Reauth
    # ------------------------------------------------------------------

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> config_entries.ConfigFlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if self._reauth_entry is None:
            return self.async_abort(reason="reauth_failed")
        if user_input is not None:
            try:
                redirect_uri = self._reauth_entry.data.get(
                    CONF_REDIRECT_URI
                ) or resolve_redirect_uri(self.hass)
            except NoRedirectUriError:
                return self.async_abort(reason="no_url_available")
            self._client_id = self._reauth_entry.data.get(CONF_CLIENT_ID)
            self._client_secret = self._reauth_entry.data.get(CONF_CLIENT_SECRET)
            self._redirect_uri = redirect_uri
            if not self._client_id or not self._client_secret:
                return self.async_abort(reason="reauth_failed")
            self._implementation = GoogleOAuth2Implementation(
                self.hass,
                str(self._client_id),
                str(self._client_secret),
                redirect_uri,
            )
            url = await self._implementation.async_generate_authorize_url(self.flow_id)
            return self.async_external_step(step_id="reauth_auth", url=url)
        return self.async_show_form(
            step_id="reauth_confirm",
            description_placeholders={"account": self._reauth_entry.title},
        )

    async def async_step_reauth_auth(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is None:
            return self.async_abort(reason="reauth_failed")
        if "error" in user_input:
            return self.async_abort(
                reason="oauth_denied",
                description_placeholders={"error": str(user_input.get("error"))},
            )
        self._external_data = user_input
        return self.async_external_step_done(next_step_id="reauth_creation")

    async def async_step_reauth_creation(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if (
            self._reauth_entry is None
            or self._implementation is None
            or self._external_data is None
        ):
            return self.async_abort(reason="reauth_failed")
        try:
            token = await self._implementation.async_resolve_external_data(
                self._external_data
            )
            profile = await async_probe_account(self.hass, token)
        except GmailScopeError:
            return self.async_abort(reason="missing_scope")
        except GmailAuthError:
            return self.async_abort(reason="reauth_failed")
        except GmailConnectionError:
            return self.async_abort(reason="cannot_connect")
        except GmailError as err:
            _LOGGER.warning("Reauth failed: %s", type(err).__name__)
            return self.async_abort(reason="reauth_failed")
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Reauth failed: %s", type(err).__name__)
            return self.async_abort(reason="reauth_failed")
        if not isinstance(token, dict) or not token.get("access_token"):
            return self.async_abort(reason="reauth_failed")
        try:
            token["expires_in"] = int(token["expires_in"])
        except (KeyError, TypeError, ValueError):
            return self.async_abort(reason="reauth_failed")
        token["expires_at"] = time.time() + token["expires_in"]
        old_token = self._reauth_entry.data.get(CONF_TOKEN, {})
        merged_token = {**old_token, **token}
        account = str(profile.get("emailAddress") or self._reauth_entry.data.get(CONF_GMAIL_ACCOUNT))
        if (
            self._reauth_entry.unique_id
            and account
            and account.casefold() != self._reauth_entry.unique_id
        ):
            return self.async_abort(reason="wrong_account")
        return self.async_update_reload_and_abort(
            self._reauth_entry,
            data={
                **self._reauth_entry.data,
                CONF_TOKEN: merged_token,
                CONF_GMAIL_ACCOUNT: account,
            },
            reason="reauth_successful",
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        return PackageTrackerOptionsFlow()


class PackageTrackerOptionsFlow(config_entries.OptionsFlow):
    """All runtime options in one visual form."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        defaults = {**_default_options(), **self.config_entry.options}
        errors: dict[str, str] = {}
        if user_input is not None:
            provider = str(user_input.get(CONF_TRACKING_PROVIDER) or TRACKING_PROVIDER_NONE)
            if provider == TRACKING_PROVIDER_DHL and not str(
                user_input.get(CONF_TRACKING_API_KEY) or ""
            ).strip():
                errors["base"] = "tracking_api_key_required"
            if provider == TRACKING_PROVIDER_CUSTOM:
                url = str(user_input.get(CONF_TRACKING_URL) or "")
                if "{tracking}" not in url:
                    errors["base"] = "tracking_url_invalid"
            if not errors:
                options = {
                    CONF_SYNC_INTERVAL: int(
                        user_input.get(CONF_SYNC_INTERVAL, DEFAULT_SYNC_INTERVAL)
                    ),
                    CONF_INITIAL_SYNC_DAYS: int(
                        user_input.get(
                            CONF_INITIAL_SYNC_DAYS, DEFAULT_INITIAL_SYNC_DAYS
                        )
                    ),
                    CONF_GMAIL_QUERY: str(
                        user_input.get(CONF_GMAIL_QUERY, DEFAULT_GMAIL_QUERY)
                    ).strip(),
                    CONF_MAX_MESSAGES: int(
                        user_input.get(CONF_MAX_MESSAGES, DEFAULT_MAX_MESSAGES)
                    ),
                    CONF_STORE_EMAIL_SUBJECTS: bool(
                        user_input.get(CONF_STORE_EMAIL_SUBJECTS, True)
                    ),
                    CONF_RETENTION_DAYS: int(
                        user_input.get(CONF_RETENTION_DAYS, DEFAULT_RETENTION_DAYS)
                    ),
                    CONF_NOTIFY_SERVICE: str(
                        user_input.get(CONF_NOTIFY_SERVICE) or ""
                    ).strip(),
                    CONF_NOTIFY_EVENTS: list(
                        user_input.get(CONF_NOTIFY_EVENTS, DEFAULT_NOTIFY_EVENTS)
                    ),
                    CONF_TRACKING_PROVIDER: provider,
                    CONF_TRACKING_API_KEY: str(
                        user_input.get(CONF_TRACKING_API_KEY) or ""
                    ).strip(),
                    CONF_TRACKING_INTERVAL: int(
                        user_input.get(
                            CONF_TRACKING_INTERVAL, DEFAULT_TRACKING_INTERVAL
                        )
                    ),
                    CONF_TRACKING_URL: str(
                        user_input.get(CONF_TRACKING_URL) or ""
                    ).strip(),
                    CONF_TRACKING_HEADER: str(
                        user_input.get(CONF_TRACKING_HEADER) or ""
                    ).strip(),
                    CONF_TRACKING_HEADER_VALUE: str(
                        user_input.get(CONF_TRACKING_HEADER_VALUE) or ""
                    ).strip(),
                    CONF_TRACKING_STATUS_PATH: str(
                        user_input.get(CONF_TRACKING_STATUS_PATH) or "status"
                    ).strip(),
                    CONF_TRACKING_EXPECTED_PATH: str(
                        user_input.get(CONF_TRACKING_EXPECTED_PATH) or ""
                    ).strip(),
                    CONF_TRACKING_EVENTS_PATH: str(
                        user_input.get(CONF_TRACKING_EVENTS_PATH) or "events"
                    ).strip(),
                    CONF_TRACKING_EVENT_TIME_PATH: str(
                        user_input.get(CONF_TRACKING_EVENT_TIME_PATH) or "timestamp"
                    ).strip(),
                    CONF_TRACKING_EVENT_TEXT_PATH: str(
                        user_input.get(CONF_TRACKING_EVENT_TEXT_PATH) or "description"
                    ).strip(),
                }
                return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SYNC_INTERVAL,
                        default=defaults[CONF_SYNC_INTERVAL],
                    ): _number_selector(1, 1440, "min"),
                    vol.Required(
                        CONF_INITIAL_SYNC_DAYS,
                        default=defaults[CONF_INITIAL_SYNC_DAYS],
                    ): _number_selector(1, 365, "Tage"),
                    vol.Optional(
                        CONF_GMAIL_QUERY, default=defaults[CONF_GMAIL_QUERY]
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(multiline=True)
                    ),
                    vol.Required(
                        CONF_MAX_MESSAGES, default=defaults[CONF_MAX_MESSAGES]
                    ): _number_selector(100, 2000),
                    vol.Required(
                        CONF_STORE_EMAIL_SUBJECTS,
                        default=defaults[CONF_STORE_EMAIL_SUBJECTS],
                    ): cv.boolean,
                    vol.Required(
                        CONF_RETENTION_DAYS, default=defaults[CONF_RETENTION_DAYS]
                    ): _number_selector(0, 3650, "Tage"),
                    vol.Optional(
                        CONF_NOTIFY_SERVICE, default=defaults[CONF_NOTIFY_SERVICE]
                    ): cv.string,
                    vol.Optional(
                        CONF_NOTIFY_EVENTS, default=defaults[CONF_NOTIFY_EVENTS]
                    ): _select(
                        [
                            selector.SelectOptionDict(value=value, label=label)
                            for value, label in NOTIFY_EVENT_OPTIONS.items()
                        ],
                        multiple=True,
                    ),
                    vol.Required(
                        CONF_TRACKING_PROVIDER,
                        default=defaults[CONF_TRACKING_PROVIDER],
                    ): _select(
                        [
                            selector.SelectOptionDict(
                                value=TRACKING_PROVIDER_NONE, label="Deaktiviert"
                            ),
                            selector.SelectOptionDict(
                                value=TRACKING_PROVIDER_DHL,
                                label="DHL Unified API (offiziell)",
                            ),
                            selector.SelectOptionDict(
                                value=TRACKING_PROVIDER_CUSTOM,
                                label="Eigener JSON-Endpunkt",
                            ),
                        ]
                    ),
                    vol.Optional(
                        CONF_TRACKING_API_KEY, default=defaults[CONF_TRACKING_API_KEY]
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD
                        )
                    ),
                    vol.Required(
                        CONF_TRACKING_INTERVAL,
                        default=defaults[CONF_TRACKING_INTERVAL],
                    ): _number_selector(0, 1440, "min"),
                    vol.Optional(
                        CONF_TRACKING_URL, default=defaults[CONF_TRACKING_URL]
                    ): cv.string,
                    vol.Optional(
                        CONF_TRACKING_HEADER, default=defaults[CONF_TRACKING_HEADER]
                    ): cv.string,
                    vol.Optional(
                        CONF_TRACKING_HEADER_VALUE,
                        default=defaults[CONF_TRACKING_HEADER_VALUE],
                    ): cv.string,
                    vol.Optional(
                        CONF_TRACKING_STATUS_PATH,
                        default=defaults[CONF_TRACKING_STATUS_PATH],
                    ): cv.string,
                    vol.Optional(
                        CONF_TRACKING_EXPECTED_PATH,
                        default=defaults[CONF_TRACKING_EXPECTED_PATH],
                    ): cv.string,
                    vol.Optional(
                        CONF_TRACKING_EVENTS_PATH,
                        default=defaults[CONF_TRACKING_EVENTS_PATH],
                    ): cv.string,
                    vol.Optional(
                        CONF_TRACKING_EVENT_TIME_PATH,
                        default=defaults[CONF_TRACKING_EVENT_TIME_PATH],
                    ): cv.string,
                    vol.Optional(
                        CONF_TRACKING_EVENT_TEXT_PATH,
                        default=defaults[CONF_TRACKING_EVENT_TEXT_PATH],
                    ): cv.string,
                }
            ),
            errors=errors,
        )
