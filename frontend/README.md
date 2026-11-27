# Package Tracker Card

Lovelace Custom Card für die Package-Tracker-Integration.

## Entwicklung

```bash
npm ci
npm run typecheck
npm test
npm run build
```

`npm run build` schreibt den gebündelten ES-Modul-Build nach:

```text
../custom_components/package_tracker/frontend/package-tracker-card.js
```

Der Bundle wird mitgeliefert, damit HACS keine Node-Toolchain benötigt. Nach Änderungen an `src/` immer neu bauen und den Bundle committen.

## Aufbau

- `src/package-tracker-card.ts` – Hauptkarte, Datenabruf via WebSocket, Filter, Suche, Sortierung
- `src/package-card.ts` – Paketkachel
- `src/package-detail.ts` – Detailansicht/Bottom-Sheet mit Timeline
- `src/package-overview.ts` – Statistik-Kacheln
- `src/package-editor.ts` – visueller Lovelace-Konfigurationseditor
- `src/logic.ts` – reine Filter-/Sortier-/Formatierungslogik (Vitest)
- `src/types.ts` – gemeinsame Typen und Card-Konfiguration
- `src/styles/shared.ts` – gemeinsame Home-Assistant-CSS-Variablen und Utilities

## Designregeln

- Nur Home-Assistant-CSS-Variablen, keine harten Theme-Farben für Flächen/Text.
- Responsive: eine Spalte auf Smartphones, Raster ab Tablet, Detail als Bottom-Sheet.
- Light/Dark automatisch über HA-Themes.
- Keine Beispieldaten in der produktiven Ansicht; Lade-, Leer- und Fehlerzustände sind explizit.
- Animationen dezent und `prefers-reduced-motion`-freundlich.
- Produktbilder mit Monogramm-Fallback; keine harten Fehler bei blockierten CDNs.
