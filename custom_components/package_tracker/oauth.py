"""Google OAuth2 implementation tailored for Gmail readonly access."""

from __future__ import annotations

import logging

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import (
    AUTH_CALLBACK_PATH,
    MY_AUTH_CALLBACK_PATH,
    LocalOAuth2Implementation,
)

from .const import (
    DOMAIN,
    GMAIL_SCOPE,
    GOOGLE_AUTHORIZE_URL,
    GOOGLE_TOKEN_URL,
)

_LOGGER = logging.getLogger(__name__)

GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"


class NoRedirectUriError(Exception):
    """No public HTTPS redirect URI is configured."""


def resolve_redirect_uri(hass: HomeAssistant) -> str:
    """Return the OAuth redirect URI.

    Google requires an HTTPS redirect URI.  My Home Assistant provides a
    stable one; otherwise the configured external URL is used.  An internal
    URL (http://homeassistant.local:8123) cannot be registered with Google.
    """
    if "my" in hass.config.components:
        return MY_AUTH_CALLBACK_PATH
    external = hass.config.external_url
    if external and external.startswith("https://"):
        return f"{external.rstrip('/')}{AUTH_CALLBACK_PATH}"
    raise NoRedirectUriError


class GoogleOAuth2Implementation(LocalOAuth2Implementation):
    """Local OAuth2 implementation with Google specific parameters."""

    def __init__(
        self,
        hass: HomeAssistant,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
    ) -> None:
        super().__init__(
            hass,
            DOMAIN,
            client_id,
            client_secret,
            GOOGLE_AUTHORIZE_URL,
            GOOGLE_TOKEN_URL,
        )
        self._redirect_uri = redirect_uri

    @property
    def name(self) -> str:
        return "Google"

    @property
    def redirect_uri(self) -> str:
        return self._redirect_uri

    @property
    def extra_authorize_data(self) -> dict[str, str]:
        # access_type=offline + prompt=consent ensures Google returns a refresh
        # token, which OAuth2Session stores and rotates automatically.
        return {
            "scope": GMAIL_SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }


async def async_revoke_token(hass: HomeAssistant, token: dict[str, str] | None) -> None:
    """Best effort revocation when the account is disconnected."""
    if not token:
        return
    value = token.get("refresh_token") or token.get("access_token")
    if not value:
        return
    session = async_get_clientsession(hass)
    try:
        async with session.post(
            GOOGLE_REVOKE_URL,
            data={"token": value},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20,
        ) as response:
            if response.status >= 400:
                _LOGGER.debug("Google token revocation returned HTTP %s", response.status)
    except (ClientError, TimeoutError):
        _LOGGER.debug("Google token revocation failed (network)")
