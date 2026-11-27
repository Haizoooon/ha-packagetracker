import { LitElement, css, html } from "lit";
import { sharedStyles } from "./styles/shared";
import {
  DEFAULT_CONFIG,
  FILTER_LABELS,
  FilterKey,
  HomeAssistant,
  PackageTrackerCardConfig,
  SORT_LABELS,
  SortKey,
} from "./types";
import { Lang, languageOf, pick } from "./logic";

export class PackageTrackerCardEditor extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
  };

  declare hass: HomeAssistant;
  declare _config: Required<Omit<PackageTrackerCardConfig, "type">>;

  constructor() {
    super();
    this._config = { ...DEFAULT_CONFIG };
  }

  setConfig(config: PackageTrackerCardConfig): void {
    this._config = { ...DEFAULT_CONFIG, ...config };
  }

  private get _lang(): Lang {
    return languageOf(this.hass?.language);
  }

  private _update<K extends keyof typeof DEFAULT_CONFIG>(
    key: K,
    value: (typeof DEFAULT_CONFIG)[K],
  ) {
    const config = { ...this._config, [key]: value };
    this._config = config;
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private _text(
    label: string,
    key: "title",
    placeholder = "",
  ) {
    return html`
      <label class="field">
        <span class="label">${label}</span>
        <input
          type="text"
          .value=${this._config[key]}
          placeholder=${placeholder}
          @change=${(event: Event) =>
            this._update(key, (event.target as HTMLInputElement).value)}
        />
      </label>
    `;
  }

  private _number(label: string, key: "max_packages", min: number, max: number) {
    return html`
      <label class="field">
        <span class="label">${label}</span>
        <input
          type="number"
          min=${min}
          max=${max}
          .value=${String(this._config[key])}
          @change=${(event: Event) => {
            const value = Number((event.target as HTMLInputElement).value);
            this._update(
              key,
              Math.min(max, Math.max(min, Number.isFinite(value) ? value : min)),
            );
          }}
        />
      </label>
    `;
  }

  private _toggle(
    label: string,
    description: string,
    key:
      | "show_delivered"
      | "show_images"
      | "show_delivery_dates"
      | "compact"
      | "show_stats"
      | "show_search"
      | "show_last_sync",
  ) {
    return html`
      <label class="toggle-row">
        <span class="toggle-text">
          <span class="label">${label}</span>
          <span class="hint">${description}</span>
        </span>
        <input
          class="switch"
          type="checkbox"
          .checked=${this._config[key]}
          @change=${(event: Event) =>
            this._update(key, (event.target as HTMLInputElement).checked)}
        />
      </label>
    `;
  }

  render() {
    const lang = this._lang;
    return html`
      <div class="editor">
        <div class="intro">
          <h3>${pick(lang, "Package Tracker Karte", "Package Tracker card")}</h3>
          <p>
            ${pick(
              lang,
              "Darstellung und Startfilter der Karte. Alle Optionen lassen sich auch per YAML setzen.",
              "Appearance and initial filter. Every option can also be set in YAML.",
            )}
          </p>
        </div>

        <div class="grid">
          ${this._text(pick(lang, "Titel", "Title"), "title", "Pakete")}
          ${this._number(
            pick(lang, "Maximal angezeigte Pakete", "Maximum packages"),
            "max_packages",
            1,
            200,
          )}
        </div>

        <div class="grid">
          <label class="field">
            <span class="label">${pick(lang, "Startfilter", "Initial filter")}</span>
            <select
              .value=${this._config.default_filter}
              @change=${(event: Event) =>
                this._update(
                  "default_filter",
                  (event.target as HTMLSelectElement).value as FilterKey,
                )}
            >
              ${(Object.keys(FILTER_LABELS) as FilterKey[]).map(
                (key) => html`<option value=${key}>${FILTER_LABELS[key][lang]}</option>`,
              )}
            </select>
          </label>

          <label class="field">
            <span class="label">${pick(lang, "Sortierung", "Sorting")}</span>
            <select
              .value=${this._config.sort_by}
              @change=${(event: Event) =>
                this._update(
                  "sort_by",
                  (event.target as HTMLSelectElement).value as SortKey,
                )}
            >
              ${(Object.keys(SORT_LABELS) as SortKey[]).map(
                (key) => html`<option value=${key}>${SORT_LABELS[key][lang]}</option>`,
              )}
            </select>
          </label>
        </div>

        <div class="toggles">
          ${this._toggle(
            pick(lang, "Zugestellte Pakete", "Delivered parcels"),
            pick(
              lang,
              "Zugestellte Pakete standardmäßig in der Liste anzeigen.",
              "Show delivered parcels by default.",
            ),
            "show_delivered",
          )}
          ${this._toggle(
            pick(lang, "Produktbilder", "Product images"),
            pick(
              lang,
              "Bilder aus Versand-E-Mails anzeigen, sofern verfügbar.",
              "Show images extracted from shipping e-mails when available.",
            ),
            "show_images",
          )}
          ${this._toggle(
            pick(lang, "Liefertermine", "Delivery dates"),
            pick(
              lang,
              "Lieferdatum und Zeitfenster auf den Karten anzeigen.",
              "Show delivery date and time window on cards.",
            ),
            "show_delivery_dates",
          )}
          ${this._toggle(
            pick(lang, "Kompakte Darstellung", "Compact layout"),
            pick(
              lang,
              "Pakete als schmale Listenzeilen statt als Kacheln.",
              "Render parcels as compact rows instead of tiles.",
            ),
            "compact",
          )}
          ${this._toggle(
            pick(lang, "Statistikleiste", "Statistics"),
            pick(
              lang,
              "Unterwegs, Heute, Zugestellt und nächste Lieferung anzeigen.",
              "Show in transit, today, delivered and next delivery.",
            ),
            "show_stats",
          )}
          ${this._toggle(
            pick(lang, "Suche", "Search"),
            pick(
              lang,
              "Suchfeld für Händler, Produkt und Sendungsnummer anzeigen.",
              "Show search for merchant, product and tracking number.",
            ),
            "show_search",
          )}
          ${this._toggle(
            pick(lang, "Letzte Synchronisierung", "Last sync"),
            pick(
              lang,
              "Zeitpunkt der letzten Gmail-Synchronisierung im Kopfbereich anzeigen.",
              "Show the last Gmail sync in the header.",
            ),
            "show_last_sync",
          )}
        </div>

        <div class="yaml-hint">
          <ha-icon icon="mdi:code-braces"></ha-icon>
          <span>
            ${pick(
              lang,
              "YAML wird vollständig unterstützt. Beispiel:",
              "YAML is fully supported. Example:",
            )}
            <code
              >type: custom:package-tracker-card<br />max_packages:
              12<br />default_filter: today</code
            >
          </span>
        </div>
      </div>
    `;
  }

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
      }

      .editor {
        display: flex;
        flex-direction: column;
        gap: 16px;
        padding: 4px 0;
      }

      .intro h3 {
        margin: 0 0 4px;
        font-size: 16px;
      }

      .intro p {
        margin: 0;
        color: var(--secondary-text-color);
        font-size: 12px;
        line-height: 1.45;
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }

      .field {
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .label {
        font-size: 12px;
        font-weight: 600;
      }

      input[type="text"],
      input[type="number"],
      select {
        width: 100%;
        padding: 9px 10px;
        border: 1px solid var(--pt-border);
        border-radius: 9px;
        background: var(--pt-surface);
        color: var(--primary-text-color);
        outline: none;
      }

      input:focus,
      select:focus {
        border-color: var(--primary-color);
      }

      .toggles {
        display: flex;
        flex-direction: column;
        border: 1px solid var(--pt-border);
        border-radius: 12px;
        overflow: hidden;
      }

      .toggle-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 10px 12px;
        border-bottom: 1px solid var(--pt-border);
      }

      .toggle-row:last-child {
        border-bottom: 0;
      }

      .toggle-text {
        display: flex;
        flex-direction: column;
        gap: 2px;
        min-width: 0;
      }

      .hint {
        color: var(--secondary-text-color);
        font-size: 10.5px;
        line-height: 1.35;
      }

      .switch {
        appearance: none;
        flex: none;
        width: 38px;
        height: 22px;
        border-radius: 999px;
        background: var(--pt-border);
        position: relative;
        cursor: pointer;
        transition: background 160ms var(--pt-ease);
      }

      .switch::after {
        content: "";
        position: absolute;
        top: 3px;
        left: 3px;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: #fff;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.24);
        transition: transform 160ms var(--pt-ease);
      }

      .switch:checked {
        background: var(--primary-color);
      }

      .switch:checked::after {
        transform: translateX(16px);
      }

      .yaml-hint {
        display: flex;
        align-items: flex-start;
        gap: 8px;
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--pt-surface);
        color: var(--secondary-text-color);
        font-size: 11px;
        line-height: 1.45;
      }

      .yaml-hint ha-icon {
        --mdc-icon-size: 16px;
        flex: none;
        margin-top: 1px;
      }

      .yaml-hint code {
        display: block;
        margin-top: 4px;
        font-size: 10.5px;
        color: var(--primary-text-color);
      }

      @media (max-width: 520px) {
        .grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ];
}

if (!customElements.get("package-tracker-card-editor")) {
  customElements.define("package-tracker-card-editor", PackageTrackerCardEditor);
}
