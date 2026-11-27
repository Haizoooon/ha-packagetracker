# Package Tracker – Custom Integration

Diese Integration ist Teil des Package-Tracker-Projekts. Die vollständige deutsche Dokumentation inklusive Google-Cloud-Einrichtung, Dashboard, Events, Services, Benachrichtigungen und Fehlerbehebung steht in der [README im Projektstamm](../../README.md).

## Kurzstart

1. Gmail API in der Google Cloud Console aktivieren.
2. OAuth-Client (Webanwendung) mit Redirect-URI `https://my.home-assistant.io/redirect/oauth` erstellen.
3. Integration hinzufügen und Client-ID/Secret eintragen.
4. Lesenden Gmail-Zugriff erlauben.
5. Dashboard-Karte `custom:package-tracker-card` hinzufügen.

## Enthaltene Entities

- `sensor.package_tracker_packages`
- `sensor.package_tracker_deliveries_today`
- `sensor.package_tracker_next_delivery`
- `sensor.package_tracker_delivered_today`
- `sensor.package_tracker_packages_in_transit`
- `sensor.package_tracker_delayed`
- ein Sensor pro erkanntem Paket
- Binary Sensoren für Lieferung heute, Zustellung, Verspätung und Gmail-Verbindung
- Buttons für Gmail-Sync und Tracking-Refresh

## Datenschutz

- ausschließlich `gmail.readonly`
- E-Mail-Analyse lokal
- keine Speicherung von E-Mail-Bodys
- keine externe KI
- Diagnostics mit geschwärzten Tokens, Secrets und Sendungsnummern

Lizenz: MIT.
