# Package Tracker – custom integration

This integration is part of the Package Tracker project. The complete documentation, including Google Cloud setup, dashboard configuration, events, services, notifications and troubleshooting, is in the [project README](../../README.md). A German version is available at [README.de.md](../../README.de.md).

## Quick start

1. Enable the Gmail API in the Google Cloud Console.
2. Create an OAuth client (Web application) with redirect URI `https://my.home-assistant.io/redirect/oauth`.
3. Add the integration and enter client ID/secret.
4. Grant read-only Gmail access.
5. Add the dashboard card `custom:package-tracker-card`.

## Entities

- `sensor.package_tracker_packages`
- `sensor.package_tracker_deliveries_today`
- `sensor.package_tracker_next_delivery`
- `sensor.package_tracker_delivered_today`
- `sensor.package_tracker_packages_in_transit`
- `sensor.package_tracker_delayed`
- one sensor per recognised parcel
- binary sensors for delivery today, out for delivery, delayed and Gmail connection
- buttons for Gmail sync and tracking refresh

## Privacy

- read-only `gmail.readonly` scope
- local e-mail analysis
- no e-mail bodies stored
- no external AI
- diagnostics redact tokens, secrets and tracking numbers

License: MIT.
