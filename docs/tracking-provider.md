# Optional tracking provider contract

Package Tracker does **not** require an external tracking API. E-mail data is the primary source. If you want additional tracking events, configure one of the following providers.

## Principles

- Default: `none` (no external request).
- No scraping, no browser, no JavaScript.
- GET requests only; timeout 20–25 seconds.
- Errors are stored on the parcel (`tracking.error`) and never affect Gmail sync.
- Tracking data is stored separately from e-mail data (`shipment.tracking`).
- E-mail facts (merchant, product, order number, e-mail history) are not overwritten.
- An e-mail delivery date remains primary; the provider estimate is stored separately as `tracking.expected_delivery`.
- Terminal e-mail statuses (`delivered`, `returned`, `cancelled`) are never downgraded automatically.

## 1. DHL Unified API

- Official endpoint: `https://api-eu.dhl.com/track/shipments?trackingNumber=...&language=en`
- Header: `DHL-API-Key: <key>`
- Request an API key at [DHL Developer](https://developer.dhl.com/).
- Options:
  - `tracking_provider: dhl_unified`
  - `tracking_api_key`
  - `tracking_interval` (minutes, 0 = off)

Expected response (simplified):

```json
{
  "shipments": [
    {
      "status": {
        "statusCode": "transit",
        "description": "The shipment is in transit",
        "timestamp": "2026-11-26T08:00:00+00:00"
      },
      "estimatedTimeOfDelivery": "2026-11-29",
      "events": [
        {
          "timestamp": "2026-11-25T18:00:00+00:00",
          "description": "Processed at the parcel centre",
          "location": {
            "address": {
              "addressLocality": "Hamburg"
            }
          }
        }
      ]
    }
  ]
}
```

Supported status codes: `pre-transit`, `transit`, `delivered`, `failure`, `unknown`. German and English descriptions are also evaluated.

## 2. Custom JSON endpoint

Options:

| Option | Example | Meaning |
|---|---|---|
| `tracking_provider` | `custom_json` | enables the provider |
| `tracking_url` | `https://api.example.com/track/{tracking}` | required, `{tracking}` is substituted |
| `tracking_header` | `X-Api-Key` | optional |
| `tracking_header_value` | `...` | optional |
| `tracking_api_key` | `...` | alternative to `Authorization: Bearer ...` |
| `tracking_status_path` | `data.state` | JSON path to the status |
| `tracking_expected_path` | `data.expected_delivery` | JSON path to the delivery estimate |
| `tracking_events_path` | `data.history` | JSON path to the event list |
| `tracking_event_time_path` | `timestamp` | path **inside** an event |
| `tracking_event_text_path` | `description` | path inside an event |

Supported JSON shape:

```json
{
  "data": {
    "state": "in_transit",
    "expected_delivery": "2026-12-01",
    "history": [
      {
        "timestamp": "2026-11-26T09:00:00+00:00",
        "description": "Arrived at the parcel centre"
      }
    ]
  }
}
```

Minimum requirements:

- `tracking_url` contains `{tracking}`.
- Response is valid JSON.
- Status/event paths are optional; no data is invented if they do not match.

Status mapping (excerpt):

- `delivered`, `zugestellt` → `delivered`
- `out for delivery`, `in zustellung`, `zustellfahrzeug` → `out_for_delivery`
- `verzögert`, `delay`, `failure`, `problem` → `delayed`
- `abholbereit`, `packstation`, `pickup` → `ready_for_pickup`
- `transit`, `unterwegs`, `paketzentrum` → `in_transit`
- `shipped`, `versendet` → `shipped`

## Security

- Use official or self-hosted endpoints only.
- Do not put credentials in the URL if the provider logs URLs; use headers.
- The API key is stored in the config entry and redacted in diagnostics.
- On errors no data is deleted; the last successful state remains.

## Why no default scraping?

Carrier websites change, block bots and often require a login for complete data. A scraping fallback would be unreliable and could break Gmail recognition during outages. Tracking is therefore explicitly optional and implemented separately.
