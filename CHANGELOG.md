# Changelog

## 1.0.0 – 2026-11-26

Erste produktive Version.

- Gmail API (readonly) mit OAuth2-Config-Flow, Reauth und automatischer Token-Erneuerung
- Lokaler Parser für Bestell-, Versand-, Tracking-, Zustell-, Verspätungs-, Abhol- und Retouren-E-Mails
- Unterstützung für DHL, Deutsche Post, Hermes, DPD, GLS, UPS, FedEx und Amazon Logistics
- Zentrale Paketverwaltung mit Bestellungen, mehreren Sendungen pro Bestellung und stabilen IDs
- Persistente Speicherung über Home Assistant `Store`
- Sensoren, Binary Sensoren, Buttons und ein Sensor pro Paket
- Events, Device-Trigger, Device-Conditions und Device-Actions
- Anbieterunabhängige Benachrichtigungen mit Duplikatvermeidung
- Lovelace-Karte mit Übersicht, Filtern, Suche, Sortierung, Detailansicht und visuellem Editor
- Optionales DHL-Unified- und Custom-JSON-Tracking mit Fehlerisolierung
- Diagnostics mit Schwärzung sensibler Daten, Repairs für Auth-/Speicherprobleme
- Umfangreiche pytest- und Vitest-Tests sowie anonymisierte Fixtures
