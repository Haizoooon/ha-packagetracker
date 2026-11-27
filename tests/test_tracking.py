"""Tests for optional external tracking providers."""

from __future__ import annotations

import pytest
from homeassistant.core import HomeAssistant

from custom_components.package_tracker.const import (
    CONF_TRACKING_API_KEY,
    CONF_TRACKING_EVENT_TEXT_PATH,
    CONF_TRACKING_EVENT_TIME_PATH,
    CONF_TRACKING_EVENTS_PATH,
    CONF_TRACKING_EXPECTED_PATH,
    CONF_TRACKING_INTERVAL,
    CONF_TRACKING_PROVIDER,
    CONF_TRACKING_STATUS_PATH,
    CONF_TRACKING_URL,
    STATUS_IN_TRANSIT,
    STATUS_SHIPPED,
    TRACKING_PROVIDER_CUSTOM,
    TRACKING_PROVIDER_DHL,
)
from custom_components.package_tracker.tracking import async_refresh_tracking

from .test_package_manager import manager, parsed


@pytest.mark.asyncio
async def test_dhl_unified_tracking_is_stored_separately(
    hass: HomeAssistant, aioclient_mock
) -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("dpd_shipping"))
    shipment = next(iter(mgr.shipments.values()))
    aioclient_mock.get(
        "https://api-eu.dhl.com/track/shipments",
        json={
            "shipments": [
                {
                    "status": {
                        "statusCode": "transit",
                        "description": "Die Sendung ist unterwegs",
                        "timestamp": "2026-11-26T08:00:00+00:00",
                    },
                    "estimatedTimeOfDelivery": "2026-11-29",
                    "events": [
                        {
                            "timestamp": "2026-11-25T18:00:00+00:00",
                            "description": "Die Sendung wurde im Paketzentrum bearbeitet",
                            "location": {"address": {"addressLocality": "Hamburg"}},
                        }
                    ],
                }
            ]
        },
    )
    options = {
        CONF_TRACKING_PROVIDER: TRACKING_PROVIDER_DHL,
        CONF_TRACKING_API_KEY: "key",
        CONF_TRACKING_INTERVAL: 60,
    }
    changes = await async_refresh_tracking(
        hass, mgr, options, force=True, only_package_id=shipment.id
    )
    assert len(changes) == 1
    assert shipment.status == STATUS_IN_TRANSIT
    assert shipment.tracking is not None
    assert shipment.tracking.provider == TRACKING_PROVIDER_DHL
    assert shipment.tracking.events
    assert shipment.tracking.events[0].location == "Hamburg"
    assert shipment.tracking.expected_delivery == "2026-11-29"
    # E-mail-derived fields stay primary and are untouched.
    assert shipment.merchant == "MediaMarkt"
    assert shipment.tracking_number == "09876543210987"
    assert shipment.expected_delivery == "2026-11-25"


@pytest.mark.asyncio
async def test_tracking_failure_does_not_change_package(
    hass: HomeAssistant, aioclient_mock
) -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("dpd_shipping"))
    shipment = next(iter(mgr.shipments.values()))
    aioclient_mock.get(
        "https://api-eu.dhl.com/track/shipments",
        status=500,
        json={"error": "server"},
    )
    options = {
        CONF_TRACKING_PROVIDER: TRACKING_PROVIDER_DHL,
        CONF_TRACKING_API_KEY: "key",
        CONF_TRACKING_INTERVAL: 60,
    }
    changes = await async_refresh_tracking(
        hass, mgr, options, force=True, only_package_id=shipment.id
    )
    assert changes == []
    assert shipment.status == STATUS_SHIPPED
    assert shipment.tracking is not None
    assert shipment.tracking.error
    assert shipment.tracking.last_checked


@pytest.mark.asyncio
async def test_custom_json_provider(
    hass: HomeAssistant, aioclient_mock
) -> None:
    mgr = manager()
    mgr.apply_parsed(parsed("dpd_shipping"))
    shipment = next(iter(mgr.shipments.values()))
    aioclient_mock.get(
        "https://tracking.example.com/09876543210987",
        json={
            "data": {
                "state": "in_transit",
                "eta": "2026-11-30",
                "history": [
                    {
                        "time": "2026-11-26T09:00:00+00:00",
                        "text": "Im Paketzentrum angekommen",
                    }
                ],
            }
        },
    )
    options = {
        CONF_TRACKING_PROVIDER: TRACKING_PROVIDER_CUSTOM,
        CONF_TRACKING_INTERVAL: 60,
        CONF_TRACKING_URL: "https://tracking.example.com/{tracking}",
        CONF_TRACKING_STATUS_PATH: "data.state",
        CONF_TRACKING_EXPECTED_PATH: "data.eta",
        CONF_TRACKING_EVENTS_PATH: "data.history",
        CONF_TRACKING_EVENT_TIME_PATH: "time",
        CONF_TRACKING_EVENT_TEXT_PATH: "text",
    }
    changes = await async_refresh_tracking(
        hass, mgr, options, force=True, only_package_id=shipment.id
    )
    assert len(changes) == 1
    assert shipment.tracking is not None
    assert shipment.tracking.provider == TRACKING_PROVIDER_CUSTOM
    assert shipment.tracking.status == STATUS_IN_TRANSIT
    assert shipment.tracking.expected_delivery == "2026-11-30"
    assert shipment.tracking.events[0].description == "Im Paketzentrum angekommen"
