import { LitElement, css, html } from "lit";
import { sharedStyles } from "./styles/shared";
import { FilterKey, PackageStats } from "./types";
import { Lang, formatDeliveryDate, pick } from "./logic";

export class PackageOverview extends LitElement {
  static properties = {
    stats: { attribute: false },
    lang: { attribute: false },
    filter: { attribute: false },
  };

  declare stats: PackageStats;
  declare lang: Lang;
  declare filter: FilterKey;

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
      }

      .stats {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 10px;
        margin: 0 0 16px;
      }

      .tile {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 8px;
        min-width: 0;
        padding: 13px 14px;
        border: 1px solid var(--pt-border);
        border-radius: 14px;
        background: var(--pt-surface);
        color: var(--primary-text-color);
        text-align: left;
        transition:
          border-color 160ms var(--pt-ease),
          background 160ms var(--pt-ease),
          transform 160ms var(--pt-ease);
      }

      .tile:hover {
        border-color: color-mix(in srgb, var(--primary-color) 35%, var(--pt-border));
        transform: translateY(-1px);
      }

      .tile[data-active="true"] {
        border-color: color-mix(in srgb, var(--primary-color) 55%, transparent);
        background: color-mix(in srgb, var(--primary-color) 8%, var(--pt-surface));
      }

      .top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
      }

      .label {
        color: var(--secondary-text-color);
        font-size: 12px;
        font-weight: 560;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      ha-icon {
        --mdc-icon-size: 18px;
        color: var(--secondary-text-color);
        flex: none;
      }

      .value {
        font-size: clamp(20px, 4vw, 25px);
        font-weight: 700;
        line-height: 1;
        letter-spacing: -0.02em;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .value.date {
        font-size: clamp(16px, 3.2vw, 21px);
      }

      .sub {
        min-height: 14px;
        color: var(--secondary-text-color);
        font-size: 11px;
        line-height: 1.25;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .accent {
        color: var(--pt-transit);
      }

      @media (max-width: 720px) {
        .stats {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }
    `,
  ];

  private _emitOpen(id: string) {
    this.dispatchEvent(
      new CustomEvent("package-open", {
        detail: { id },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private _emit(filter: FilterKey) {
    this.dispatchEvent(
      new CustomEvent("filter-select", {
        detail: { filter },
        bubbles: true,
        composed: true,
      }),
    );
  }

  render() {
    if (!this.stats) return html``;
    const next = this.stats.next_delivery;
    return html`
      <div class="stats" aria-label=${pick(this.lang, "Übersicht", "Overview")}>
        <button
          class="tile"
          data-active=${this.filter === "transit"}
          @click=${() => this._emit("transit")}
        >
          <div class="top">
            <span class="label">${pick(this.lang, "Unterwegs", "In transit")}</span>
            <ha-icon icon="mdi:truck-fast"></ha-icon>
          </div>
          <div class="value">${this.stats.in_transit}</div>
          <div class="sub">
            ${pick(
              this.lang,
              `${this.stats.active} aktive Pakete`,
              `${this.stats.active} active parcels`,
            )}
          </div>
        </button>

        <button
          class="tile"
          data-active=${this.filter === "today"}
          @click=${() => this._emit("today")}
        >
          <div class="top">
            <span class="label">${pick(this.lang, "Heute", "Today")}</span>
            <ha-icon icon="mdi:calendar-today"></ha-icon>
          </div>
          <div class="value">${this.stats.delivery_today}</div>
          <div class="sub">
            ${pick(this.lang, "Lieferungen angekündigt", "deliveries expected")}
          </div>
        </button>

        <button
          class="tile"
          data-active=${this.filter === "delivered"}
          @click=${() => this._emit("delivered")}
        >
          <div class="top">
            <span class="label">${pick(this.lang, "Zugestellt", "Delivered")}</span>
            <ha-icon icon="mdi:package-variant-closed-check"></ha-icon>
          </div>
          <div class="value">${this.stats.delivered_today}</div>
          <div class="sub">${pick(this.lang, "heute zugestellt", "delivered today")}</div>
        </button>

        <button
          class="tile"
          data-active=${this.filter === "today"}
          @click=${() => (next ? this._emitOpen(next.id) : this._emit("today"))}
        >
          <div class="top">
            <span class="label">${pick(this.lang, "Nächste Lieferung", "Next delivery")}</span>
            <ha-icon icon="mdi:truck-delivery"></ha-icon>
          </div>
          <div class="value date accent">
            ${next
              ? formatDeliveryDate(next.expected_delivery, this.lang)
              : "–"}
          </div>
          <div class="sub">
            ${next
              ? `${next.product_name || next.merchant || pick(this.lang, "Paket", "Parcel")}${
                  next.delivery_window ? ` · ${next.delivery_window}` : ""
                }`
              : pick(this.lang, "Keine Lieferung geplant", "No delivery scheduled")}
          </div>
        </button>
      </div>
    `;
  }
}

if (!customElements.get("package-tracker-overview")) {
  customElements.define("package-tracker-overview", PackageOverview);
}
