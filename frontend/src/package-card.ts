import { LitElement, css, html, nothing } from "lit";
import { sharedStyles } from "./styles/shared";
import { PackageData } from "./types";
import {
  Lang,
  formatDeliveryDate,
  isTerminal,
  merchantColor,
  merchantInitials,
  pick,
  progressIndex,
  shortTracking,
  statusLabel,
  statusTone,
  todayISO,
} from "./logic";

export class PackageCard extends LitElement {
  static properties = {
    pkg: { attribute: false },
    lang: { attribute: false },
    showImages: { type: Boolean, attribute: "show-images" },
    showDeliveryDates: { type: Boolean, attribute: "show-delivery-dates" },
    compact: { type: Boolean },
    _imageFailed: { state: true },
  };

  declare pkg: PackageData;
  declare lang: Lang;
  declare showImages: boolean;
  declare showDeliveryDates: boolean;
  declare compact: boolean;
  declare _imageFailed: boolean;

  constructor() {
    super();
    this.showImages = true;
    this.showDeliveryDates = true;
    this.compact = false;
    this._imageFailed = false;
  }

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
        min-width: 0;
      }

      .card {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 12px;
        height: 100%;
        padding: 15px;
        border: 1px solid var(--pt-border);
        border-radius: var(--pt-radius);
        background: var(--ha-card-background, var(--card-background-color));
        color: var(--primary-text-color);
        text-align: left;
        overflow: hidden;
        transition:
          transform 180ms var(--pt-ease),
          border-color 180ms var(--pt-ease),
          box-shadow 180ms var(--pt-ease);
        animation: pt-fade-up 240ms var(--pt-ease) both;
      }

      .card::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 3px;
        background: transparent;
      }

      .card[data-tone="warning"]::before {
        background: var(--pt-warning);
      }

      .card[data-tone="success"]::before {
        background: var(--pt-success);
      }

      .card[data-tone="transit"]::before {
        background: var(--pt-transit);
      }

      .card[data-tone="pickup"]::before {
        background: var(--pt-pickup);
      }

      .card[data-tone="danger"]::before {
        background: var(--pt-danger);
      }

      .card:hover {
        transform: translateY(-2px);
        border-color: color-mix(in srgb, var(--primary-color) 35%, var(--pt-border));
        box-shadow: 0 8px 22px color-mix(in srgb, #000 9%, transparent);
      }

      .head {
        display: flex;
        align-items: flex-start;
        gap: 11px;
        min-width: 0;
      }

      .media {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        flex: none;
        width: 52px;
        height: 52px;
        border-radius: 12px;
        overflow: hidden;
        background: var(--pt-surface);
      }

      .media img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        padding: 4px;
        background: #fff;
      }

      .monogram {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
        height: 100%;
        color: #fff;
        font-size: 17px;
        font-weight: 700;
        letter-spacing: 0.02em;
      }

      .head-text {
        display: flex;
        flex-direction: column;
        gap: 3px;
        min-width: 0;
        flex: 1;
      }

      .merchant {
        display: flex;
        align-items: center;
        gap: 6px;
        min-width: 0;
        color: var(--secondary-text-color);
        font-size: 12px;
        font-weight: 560;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .product {
        margin: 0;
        font-size: 15px;
        font-weight: 650;
        line-height: 1.3;
        letter-spacing: -0.01em;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        word-break: break-word;
      }

      .status {
        flex: none;
        margin-left: auto;
        align-self: flex-start;
      }

      .meta-row {
        display: flex;
        align-items: center;
        gap: 7px;
        min-width: 0;
        color: var(--secondary-text-color);
        font-size: 11.5px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .meta-row ha-icon {
        --mdc-icon-size: 15px;
        flex: none;
      }

      .dot {
        opacity: 0.45;
        padding: 0 1px;
      }

      .delivery {
        display: flex;
        align-items: center;
        gap: 7px;
        margin-top: auto;
        padding-top: 9px;
        border-top: 1px solid var(--pt-border);
        font-size: 12.5px;
        min-width: 0;
      }

      .delivery ha-icon {
        --mdc-icon-size: 16px;
        color: var(--secondary-text-color);
        flex: none;
      }

      .delivery .date {
        font-weight: 620;
        white-space: nowrap;
      }

      .delivery .window {
        color: var(--secondary-text-color);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .today {
        color: var(--pt-transit);
      }

      .progress {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 0;
        align-items: center;
        margin: 1px 0;
      }

      .step {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
      }

      .step::before {
        content: "";
        position: absolute;
        top: 50%;
        right: 50%;
        width: 100%;
        height: 2px;
        background: var(--pt-border);
        transform: translateY(-50%);
      }

      .step:first-child::before {
        display: none;
      }

      .step[data-done="true"]::before {
        background: color-mix(in srgb, var(--primary-color) 55%, var(--pt-border));
      }

      .point {
        position: relative;
        z-index: 1;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--pt-border);
        transition: background 160ms var(--pt-ease);
      }

      .step[data-done="true"] .point {
        background: var(--primary-color);
      }

      .step[data-current="true"] .point {
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--primary-color) 18%, transparent);
      }

      .card[data-tone="warning"] .step[data-current="true"] .point {
        background: var(--pt-warning);
        box-shadow: 0 0 0 3px color-mix(in srgb, var(--pt-warning) 20%, transparent);
      }

      .card[data-tone="success"] .step .point,
      .card[data-tone="success"] .step[data-done="true"]::before {
        background: var(--pt-success);
      }

      .empty-term {
        color: var(--secondary-text-color);
        font-weight: 500;
      }

      /* Compact layout */
      .card.compact {
        flex-direction: row;
        align-items: center;
        gap: 12px;
        padding: 11px 13px;
      }

      .card.compact .media {
        width: 44px;
        height: 44px;
        border-radius: 10px;
      }

      .card.compact .head {
        flex: 1;
        align-items: center;
      }

      .card.compact .head-text {
        gap: 2px;
      }

      .card.compact .product {
        -webkit-line-clamp: 1;
        font-size: 14px;
      }

      .card.compact .status {
        align-self: center;
      }

      .card.compact .delivery {
        margin: 0;
        padding: 0;
        border: 0;
        flex: none;
        font-size: 12px;
      }

      .card.compact .progress,
      .card.compact .meta-row {
        display: none;
      }

      @media (max-width: 520px) {
        .card {
          padding: 13px;
        }

        .media {
          width: 46px;
          height: 46px;
        }

        .product {
          font-size: 14px;
        }
      }
    `,
  ];

  private _open() {
    this.dispatchEvent(
      new CustomEvent("package-open", {
        detail: { id: this.pkg.id },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private _onKeydown(event: KeyboardEvent) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      this._open();
    }
  }

  private _renderProgress() {
    const index = progressIndex(this.pkg.status);
    if (index < 0) return nothing;
    return html`
      <div class="progress" aria-hidden="true">
        ${[0, 1, 2, 3, 4].map(
          (step) => html`
            <span
              class="step"
              data-done=${step <= index}
              data-current=${step === index}
            >
              <span class="point"></span>
            </span>
          `,
        )}
      </div>
    `;
  }

  render() {
    const pkg = this.pkg;
    if (!pkg) return nothing;
    const tone = statusTone(pkg.status);
    const today = todayISO();
    const expectedToday =
      pkg.expected_delivery === today && !isTerminal(pkg) && pkg.status !== "delivered";
    const showImage = this.showImages && pkg.product_image && !this._imageFailed;
    const merchant = pkg.merchant || pick(this.lang, "Unbekannter Händler", "Unknown merchant");
    const product =
      pkg.product_name ||
      pick(this.lang, `Paket von ${merchant}`, `Parcel from ${merchant}`);
    const carrier = pkg.carrier_name || pkg.carrier || pick(this.lang, "Paketdienst offen", "Carrier pending");
    const deliveryText = pkg.status === "delivered" && pkg.actual_delivery
      ? pick(this.lang, "Zugestellt", "Delivered")
      : pkg.expected_delivery
        ? formatDeliveryDate(pkg.expected_delivery, this.lang)
        : pick(this.lang, "Termin folgt", "Date pending");
    const aria = `${merchant}: ${product}. ${statusLabel(pkg.status, this.lang)}. ${carrier}. ${deliveryText}`;

    return html`
      <article
        class="card ${this.compact ? "compact" : ""}"
        data-tone=${tone}
        role="button"
        tabindex="0"
        aria-label=${aria}
        @click=${this._open}
        @keydown=${this._onKeydown}
      >
        <div class="head">
          <div class="media">
            ${showImage
              ? html`<img
                  src=${pkg.product_image}
                  alt=""
                  loading="lazy"
                  decoding="async"
                  referrerpolicy="no-referrer"
                  @error=${() => {
                    this._imageFailed = true;
                  }}
                />`
              : html`<span
                  class="monogram"
                  style="background:${merchantColor(pkg.merchant)}"
                  >${merchantInitials(pkg.merchant)}</span
                >`}
          </div>
          <div class="head-text">
            <div class="merchant">
              <span>${merchant}</span>
              ${pkg.siblings && pkg.siblings.length
                ? html`<span class="dot">·</span><span>${pkg.siblings.length + 1} Pakete</span>`
                : nothing}
            </div>
            <h3 class="product">${product}</h3>
          </div>
          <span class="pill status ${tone}"
            >${statusLabel(pkg.status, this.lang)}</span
          >
        </div>

        <div class="meta-row">
          <ha-icon icon="mdi:truck-outline"></ha-icon>
          <span>${carrier}</span>
          ${pkg.tracking_number
            ? html`<span class="dot">·</span
                ><span class="mono">${shortTracking(pkg.tracking_number)}</span>`
            : nothing}
        </div>

        ${this.compact ? nothing : this._renderProgress()}

        ${this.showDeliveryDates
          ? html`
              <div class="delivery">
                <ha-icon icon="mdi:calendar-clock-outline"></ha-icon>
                <span class="date ${expectedToday ? "today" : ""}">${deliveryText}</span>
                ${pkg.delivery_window
                  ? html`<span class="window">${pkg.delivery_window}</span>`
                  : pkg.expected_delivery && !expectedToday
                    ? html`<span class="window"
                        >${pick(this.lang, "voraussichtlich", "estimated")}</span
                      >`
                    : nothing}
              </div>
            `
          : nothing}
      </article>
    `;
  }
}

if (!customElements.get("package-tracker-package-card")) {
  customElements.define("package-tracker-package-card", PackageCard);
}
