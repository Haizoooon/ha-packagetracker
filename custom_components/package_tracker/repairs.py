"""Repair flows for authentication and storage problems."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components.repairs import RepairsFlow
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN


class PackageTrackerRepairFlow(RepairsFlow):
    """Handle a Package Tracker repair."""

    def __init__(self, issue: str, entry_id: str) -> None:
        self._issue = issue
        self._entry_id = entry_id

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> Any:
        if user_input is not None:
            entry = self.hass.config_entries.async_get_entry(self._entry_id)
            if entry is not None and self._issue in {"auth", "scope"}:
                entry.async_start_reauth(self.hass)
            return self.async_create_entry(data={})

        issue = ir.async_get(self.hass).async_get_issue(
            DOMAIN, f"{self._issue}_{self._entry_id}"
        )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
            description_placeholders={
                "entry": issue.translation_placeholders.get("entry", "")
                if issue and issue.translation_placeholders
                else "",
                "message": issue.translation_placeholders.get("message", "")
                if issue and issue.translation_placeholders
                else "",
            },
        )


async def async_create_fix_flow(
    hass: HomeAssistant,
    issue_id: str,
    data: dict[str, Any] | None,
) -> RepairsFlow:
    data = data or {}
    issue = str(data.get("issue") or "")
    entry_id = str(data.get("entry_id") or "")
    if issue not in {"auth", "scope"} or not entry_id:
        raise ValueError("Unknown Package Tracker repair issue")
    return PackageTrackerRepairFlow(issue, entry_id)
