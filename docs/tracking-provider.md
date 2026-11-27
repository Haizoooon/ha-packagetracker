# Optionaler Tracking-Provider – Vertrag

Package Tracker benötigt **keine** externe Tracking-API. Die E-Mail-Daten sind die primäre Quelle. Wer zusätzliche Tracking-Events möchte, kann einen der folgenden Anbieter konfigurieren.

## Grundsätze

- Standard: `none` (kein externer Abruf).
- Kein Scraping, kein Browser, kein JavaScript.
- Nur GET-Anfragen; Timeout 20–25 Sekunden.
- Fehler werden am Paket gespeichert (`tracking.error`) und beeinflussen den Gmail-Sync nicht.
- Trackingdaten werden getrennt von E-Mail-Daten gespeichert (`shipment.tracking`).
- E-Mail-Fakten (Händler, Produkt, Bestellnummer, E-Mail-Historie) werden nicht überschrieben.
- Ein aus der E-Mail bekannter Liefertermin bleibt primär; der Provider-Termin steht separat als `tracking.expected_delivery`.
- Terminale E-Mail-Status (`delivered`, `returned`, `cancelled`) werden nicht automatisch zurückgestuft.

## 1. DHL Unified API

- Offizieller Endpunkt: `https://api-eu.dhl.com/track/shipments?trackingNumber=...&language=de`
- Header: `DHL-API-Key: <key>`
- API-Key bei [DHL Developer](https://developer.dhl.com/) beantragen.
- Optionen:
  - `tracking_provider: dhl_unified`
  - `tracking_api_key`
  - `tracking_interval` (Minuten, 0 = aus)

Erwartete Antwort (vereinfacht):

```json
{
  "shipments": [
    {
      "status": {
        "statusCode": "transit",
        "description": "Die Sendung ist unterwegs",
        "timestamp": "2026-11-26T08:00:00+00:00"
      },
      "estimatedTimeOfDelivery": "2026-11-29",
      "events": [
        {
          "timestamp": "2026-11-25T18:00:00+00:00",
          "description": "Im Paketzentrum bearbeitet",
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

Unterstützte Statuscodes: `pre-transit`, `transit`, `delivered`, `failure`, `unknown`. Zusätzlich werden deutsche/englische Beschreibungen ausgewertet.

## 2. Eigener JSON-Endpunkt

Optionen:

| Option | Beispiel | Bedeutung |
|---|---|---|
| `tracking_provider` | `custom_json` | aktiviert den Provider |
| `tracking_url` | `https://api.example.com/track/{tracking}` | Pflicht, `{tracking}` wird ersetzt |
| `tracking_header` | `X-Api-Key` | optional |
| `tracking_header_value` | `...` | optional |
| `tracking_api_key` | `...` | alternativ `Authorization: Bearer ...` |
| `tracking_status_path` | `data.state` | JSON-Pfad zum Status |
| `tracking_expected_path` | `data.expected_delivery` | JSON-Pfad zum Liefertermin |
| `tracking_events_path` | `data.history` | JSON-Pfad zur Ereignisliste |
| `tracking_event_time_path` | `timestamp` | Pfad **innerhalb** eines Ereignisses |
| `tracking_event_text_path` | `description` | Pfad innerhalb eines Ereignisses |

Unterstützte JSON-Formen:

```json
{
  "data": {
    "state": "in_transit",
    "expected_delivery": "2026-12-01",
    "history": [
      {
        "timestamp": "2026-11-26T09:00:00+00:00",
        "description": "Im Paketzentrum angekommen"
      }
    ]
  }
}
```

Mindestanforderung:

- `tracking_url` enthält `{tracking}`.
- Antwort ist gültiges JSON.
- Status-/Ereignis-Pfade sind optional; ohne Treffer wird nichts erfunden.

Status-Erkennung (Auszug):

- `delivered`, `zugestellt` → `delivered`
- `out for delivery`, `in zustellung`, `zustellfahrzeug` → `out_for_delivery`
- `verzögert`, `delay`, `failure`, `problem` → `delayed`
- `abholbereit`, `packstation`, `pickup` → `ready_for_pickup`
- `transit`, `unterwegs`, `paketzentrum` → `in_transit`
- `shipped`, `versendet` → `shipped`

## Sicherheit

- Verwende ausschließlich offizielle oder selbst betriebene Endpunkte.
- Keine Zugangsdaten in die URL schreiben, wenn der Provider Logs erstellt; nutze Header.
- Der API-Key wird im Config-Entry gespeichert und in Diagnostics geschwärzt.
- Bei Fehlern werden keine Daten gelöscht; der letzte erfolgreiche Stand bleibt erhalten.

## Warum kein Standard-Scraping?

Paketdienst-Websites ändern sich, blockieren Bots und liefern oft nur mit Login vollständige Daten. Ein Scraping-Fallback wäre unzuverlässig und würde bei Ausfällen die Gmail-Erkennung gefährden. Deshalb ist Tracking explizit optional und getrennt implementiert.
