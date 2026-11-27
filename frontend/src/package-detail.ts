import { LitElement, css, html, nothing } from "lit";
import { sharedStyles } from "./styles/shared";
import { EmailRef, HomeAssistant, PackageData } from "./types";
import {
  Lang,
  emailKindLabel,
  formatDate,
  formatDateTime,
  formatDeliveryDate,
  mergeTimeline,
  pick,
  statusLabel,
  statusTone,
  translateNote,
} from "./logic";

export class PackageDetail extends LitElement {
  static properties = {
    pkg: { attribute: false },
    hass: { attribute: false },
    lang: { attribute: false },
    showImages: { type: Boolean, attribute: "show-images" },
    open: { type: Boolean },
    _imageFailed: { state: true },
    _copied: { state: true },
  };

  declare pkg: PackageData | null;
  declare hass: HomeAssistant;
  declare lang: Lang;
  declare showImages: boolean;
  declare open: boolean;
  declare _imageFailed: boolean;
  declare _copied: boolean;

  constructor() {
    super();
    this.pkg = null;
    this.open = false;
    this.showImages = true;
    this._imageFailed = false;
    this._copied = false;
  }

  private _onKeydown = (event: KeyboardEvent) => {
    if (event.key === "Escape" && this.open) this._close();
  };

  connectedCallback() {
    super.connectedCallback();
    window.addEventListener("keydown", this._onKeydown);
  }

  disconnectedCallback() {
    window.removeEventListener("keydown", this._onKeydown);
    super.disconnectedCallback();
  }

  protected willUpdate(changed: Map<PropertyKey, unknown>) {
    if (changed.has("pkg")) {
      this._imageFailed = false;
      this._copied = false;
    }
  }

  protected updated(changed: Map<PropertyKey, unknown>) {
    if (this.open && changed.has("open")) {
      const close = this.renderRoot.querySelector<HTMLButtonElement>(".close");
      close?.focus();
    }
  }

  private _close() {
    this.dispatchEvent(
      new CustomEvent("package-close", { bubbles: true, composed: true }),
    );
  }

  private _openSibling(id: string) {
    this.dispatchEvent(
      new CustomEvent("package-open", {
        detail: { id },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private _moreInfo() {
    if (!this.hass || !this.pkg) return;
    let entityId = this.pkg.entity_id as string | undefined;
    if (!entityId) {
      const state = Object.values(this.hass.states).find(
        (candidate) => candidate.attributes.package_id === this.pkg?.id,
      );
      entityId = state?.entity_id;
    }
    if (!entityId) return;
    this.dispatchEvent(
      new CustomEvent("hass-more-info", {
        detail: { entityId },
        bubbles: true,
        composed: true,
      }),
    );
  }

  private async _copyTracking() {
    const value = this.pkg?.tracking_number;
    if (!value || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(value);
      this._copied = true;
      window.setTimeout(() => {
        this._copied = false;
      }, 1600);
    } catch {
      this._copied = false;
    }
  }

  private _row(label: string, value: unknown) {
    if (value === null || value === undefined || value === "") return nothing;
    return html`
      <div class="info-row">
        <span class="info-label">${label}</span>
        <span class="info-value">${value}</span>
      </div>
    `;
  }

  private _emailLabel(email: EmailRef) {
    return email.subject || emailKindLabel(email.kind, this.lang);
  }

  private _renderStepper() {
    const steps = [
      pick(this.lang, "Bestellt", "Ordered"),
      pick(this.lang, "Versendet", "Shipped"),
      pick(this.lang, "Unterwegs", "Transit"),
      pick(this.lang, "Zustellung", "Delivery"),
      pick(this.lang, "Zugestellt", "Delivered"),
    ];
    const index = [
      "ordered",
      "shipped",
      "in_transit",
      "delayed",
      "out_for_delivery",
      "ready_for_pickup",
      "delivered",
    ].indexOf(String(this.pkg?.status));
    const current =
      this.pkg?.status === "ordered"
        ? 0
        : this.pkg?.status === "shipped"
          ? 1
          : ["in_transit", "delayed"].includes(String(this.pkg?.status))
            ? 2
            : ["out_for_delivery", "ready_for_pickup"].includes(String(this.pkg?.status))
              ? 3
              : this.pkg?.status === "delivered"
                ? 4
                : -1;
    if (index < 0 && current < 0) return nothing;
    return html`
      <div class="stepper" aria-hidden="true">
        ${steps.map(
          (label, step) => html`
            <div
              class="stepper-step"
              data-done=${step <= current}
              data-current=${step === current}
            >
              <span class="stepper-dot"></span>
              <span class="stepper-label">${label}</span>
            </div>
          `,
        )}
      </div>
    `;
  }

  render() {
    const pkg = this.pkg;
    if (!this.open || !pkg) return nothing;
    const tone = statusTone(pkg.status);
    const timeline = mergeTimeline(pkg);
    const merchant = pkg.merchant || pick(this.lang, "Unbekannter Händler", "Unknown merchant");
    const product =
      pkg.product_name || pick(this.lang, "Paket", "Parcel");
    const showImage =
      this.showImages && Boolean(pkg.product_image) && !this._imageFailed;
    const latestEmail = (pkg.emails || []).slice(-1)[0];
    const order = pkg.order || null;

    return html`
      <div class="backdrop" @click=${this._close}>
        <section
          class="sheet"
          role="dialog"
          aria-modal="true"
          aria-label=${product}
          @click=${(event: Event) => event.stopPropagation()}
        >
          <header class="header">
            <div class="media">
              ${showImage
                ? html`<img
                    src=${pkg.product_image}
                    alt=""
                    referrerpolicy="no-referrer"
                    @error=${() => {
                      this._imageFailed = true;
                    }}
                  />`
                : html`<ha-icon icon="mdi:package-variant-closed"></ha-icon>`}
            </div>
            <div class="heading">
              <div class="merchant">${merchant}</div>
              <h2>${product}</h2>
              <div class="status-line">
                <span class="pill ${tone}">${statusLabel(pkg.status, this.lang)}</span>
                ${pkg.completed
                  ? html`<span class="pill">${pick(this.lang, "Erledigt", "Completed")}</span>`
                  : nothing}
              </div>
            </div>
            <button class="icon-btn close" @click=${this._close} aria-label=${pick(this.lang, "Schließen", "Close")}>
              <ha-icon icon="mdi:close"></ha-icon>
            </button>
          </header>

          <div class="content">
            ${this._renderStepper()}

            ${pkg.notes
              ? html`<div class="note">${translateNote(pkg.notes, this.lang)}</div>`
              : nothing}

            <section class="section">
              <h3>${pick(this.lang, "Paketdetails", "Parcel details")}</h3>
              <div class="info-grid">
                ${this._row(pick(this.lang, "Händler", "Merchant"), pkg.merchant)}
                ${this._row(pick(this.lang, "Paketdienst", "Carrier"), pkg.carrier_name || pkg.carrier)}
                ${this._row(pick(this.lang, "Bestellnummer", "Order number"), pkg.order_number)}
                ${this._row(
                  pick(this.lang, "Bestelldatum", "Order date"),
                  pkg.order_date ? formatDate(pkg.order_date, this.lang) : null,
                )}
                ${this._row(
                  pick(this.lang, "Versanddatum", "Shipped"),
                  pkg.shipped_date ? formatDate(pkg.shipped_date, this.lang) : null,
                )}
                ${this._row(
                  pick(this.lang, "Voraussichtliche Lieferung", "Expected delivery"),
                  pkg.expected_delivery
                    ? `${formatDeliveryDate(pkg.expected_delivery, this.lang)}${
                        pkg.delivery_window ? ` · ${pkg.delivery_window}` : ""
                      }`
                    : null,
                )}
                ${this._row(
                  pick(this.lang, "Tatsächliche Lieferung", "Actual delivery"),
                  pkg.actual_delivery ? formatDate(pkg.actual_delivery, this.lang) : null,
                )}
                ${this._row(
                  pick(this.lang, "Produkte", "Products"),
                  pkg.product_names && pkg.product_names.length > 1
                    ? pkg.product_names.join(" · ")
                    : null,
                )}
              </div>
            </section>

            ${pkg.tracking_number || pkg.tracking_url
              ? html`
                  <section class="section">
                    <h3>${pick(this.lang, "Sendungsverfolgung", "Tracking")}</h3>
                    <div class="tracking-box">
                      <div class="tracking-main">
                        <ha-icon icon="mdi:barcode-scan"></ha-icon>
                        <span class="mono tracking-number">${pkg.tracking_number || "–"}</span>
                        ${pkg.tracking_number
                          ? html`<button
                              class="copy"
                              @click=${this._copyTracking}
                              aria-label=${pick(this.lang, "Sendungsnummer kopieren", "Copy tracking number")}
                            >
                              <ha-icon
                                icon=${this._copied ? "mdi:check" : "mdi:content-copy"}
                              ></ha-icon>
                              <span>${this._copied ? pick(this.lang, "Kopiert", "Copied") : ""}</span>
                            </button>`
                          : nothing}
                      </div>
                      ${pkg.tracking_url
                        ? html`<a
                            class="tracking-link"
                            href=${pkg.tracking_url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            <span>${pick(this.lang, "Sendung verfolgen", "Track parcel")}</span>
                            <ha-icon icon="mdi:open-in-new"></ha-icon>
                          </a>`
                        : nothing}
                      ${pkg.tracking?.error
                        ? html`<div class="warning-box">
                            <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
                            <span>${pkg.tracking.error}</span>
                          </div>`
                        : nothing}
                    </div>
                  </section>
                `
              : nothing}

            <section class="section">
              <div class="section-head">
                <h3>${pick(this.lang, "Statushistorie", "Status history")}</h3>
                ${pkg.last_email_at
                  ? html`<span class="muted small"
                      >${pick(this.lang, "Letzte E-Mail", "Last e-mail")}:
                      ${formatDateTime(pkg.last_email_at, this.lang)}</span
                    >`
                  : nothing}
              </div>
              ${timeline.length
                ? html`<ol class="timeline">
                    ${timeline.map(
                      (event) => html`
                        <li class="timeline-item" data-tone=${statusTone(String(event.status))}>
                          <span class="timeline-dot"></span>
                          <div class="timeline-body">
                            <div class="timeline-top">
                              <span class="timeline-status"
                                >${statusLabel(String(event.status || "unknown"), this.lang)}</span
                              >
                              <span class="timeline-time"
                                >${formatDateTime(event.timestamp, this.lang)}</span
                              >
                            </div>
                            ${event.description
                              ? html`<div class="timeline-desc">${translateNote(event.description, this.lang)}</div>`
                              : nothing}
                            <div class="timeline-source">
                              ${event.source === "tracking"
                                ? pick(this.lang, "Tracking-Anbieter", "Tracking provider")
                                : event.source === "manual"
                                  ? pick(this.lang, "Manuell", "Manual")
                                  : pick(this.lang, "E-Mail", "E-mail")}
                              ${event.location ? ` · ${event.location}` : ""}
                            </div>
                          </div>
                        </li>
                      `,
                    )}
                  </ol>`
                : html`<p class="muted">
                    ${pick(this.lang, "Noch keine Statusänderungen erfasst.", "No status changes recorded yet.")}
                  </p>`}
            </section>

            ${latestEmail || pkg.last_email_at
              ? html`
                  <section class="section">
                    <h3>${pick(this.lang, "Letzte E-Mail-Aktualisierung", "Last e-mail update")}</h3>
                    <div class="email-card">
                      <ha-icon icon="mdi:email-outline"></ha-icon>
                      <div class="email-body">
                        <div class="email-subject">
                          ${latestEmail ? this._emailLabel(latestEmail) : pick(this.lang, "E-Mail empfangen", "E-mail received")}
                        </div>
                        <div class="muted small">
                          ${latestEmail?.sender || pkg.last_email_from || ""}
                          ${latestEmail || pkg.last_email_at
                            ? ` · ${formatDateTime(latestEmail?.received_at || pkg.last_email_at, this.lang)}`
                            : ""}
                        </div>
                      </div>
                      <span class="pill">${latestEmail ? emailKindLabel(latestEmail.kind, this.lang) : "E-Mail"}</span>
                    </div>
                    ${(pkg.emails || []).length > 1
                      ? html`<div class="muted small email-count">
                          ${pick(
                            this.lang,
                            `${pkg.emails?.length} zugehörige E-Mails`,
                            `${pkg.emails?.length} related e-mails`,
                          )}
                        </div>`
                      : nothing}
                  </section>
                `
              : nothing}

            ${pkg.siblings && pkg.siblings.length
              ? html`
                  <section class="section">
                    <h3>${pick(this.lang, "Weitere Sendungen dieser Bestellung", "Other shipments in this order")}</h3>
                    <div class="siblings">
                      ${pkg.siblings.map(
                        (sibling) => html`
                          <button class="sibling" @click=${() => this._openSibling(sibling.id)}>
                            <ha-icon icon="mdi:package-variant"></ha-icon>
                            <span class="sibling-name">${sibling.product_name || sibling.id}</span>
                            <span class="sibling-carrier">${sibling.carrier || ""}</span>
                            <span class="pill ${statusTone(String(sibling.status))}"
                              >${statusLabel(String(sibling.status || "unknown"), this.lang)}</span
                            >
                          </button>
                        `,
                      )}
                    </div>
                  </section>
                `
              : nothing}

            ${order
              ? html`
                  <section class="section">
                    <h3>${pick(this.lang, "Bestellinformationen", "Order information")}</h3>
                    <div class="info-grid">
                      ${this._row(pick(this.lang, "Bestellnummer", "Order number"), order.order_number)}
                      ${this._row(
                        pick(this.lang, "Bestelldatum", "Order date"),
                        order.order_date ? formatDate(order.order_date, this.lang) : null,
                      )}
                      ${this._row(
                        pick(this.lang, "Sendungen", "Shipments"),
                        order.shipment_ids?.length || null,
                      )}
                      ${this._row(
                        pick(this.lang, "Status der Bestellung", "Order status"),
                        order.status ? statusLabel(order.status, this.lang) : null,
                      )}
                    </div>
                  </section>
                `
              : nothing}

            <div class="actions">
              ${pkg.entity_id
                ? html`<button class="secondary-btn" @click=${this._moreInfo}>
                    <ha-icon icon="mdi:information-outline"></ha-icon>
                    ${pick(this.lang, "Entität öffnen", "Open entity")}
                  </button>`
                : nothing}
              <span class="muted small">
                ${pick(this.lang, "Paket-ID", "Package ID")}: ${pkg.id}
              </span>
            </div>
          </div>
        </section>
      </div>
    `;
  }

  static styles = [
    sharedStyles,
    css`
      :host {
        display: contents;
      }

      .backdrop {
        position: fixed;
        inset: 0;
        z-index: 999;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
        background: rgba(0, 0, 0, 0.44);
        backdrop-filter: blur(3px);
        animation: pt-fade 160ms ease both;
      }

      .sheet {
        display: flex;
        flex-direction: column;
        width: min(640px, 100%);
        max-height: min(86vh, 900px);
        overflow: hidden;
        border: 1px solid var(--pt-border);
        border-radius: 20px;
        background: var(--ha-card-background, var(--card-background-color));
        box-shadow: 0 24px 60px rgba(0, 0, 0, 0.3);
        animation: pt-pop 220ms var(--pt-ease) both;
      }

      .header {
        display: flex;
        align-items: flex-start;
        gap: 13px;
        padding: 18px 18px 15px;
        border-bottom: 1px solid var(--pt-border);
      }

      .media {
        display: flex;
        align-items: center;
        justify-content: center;
        flex: none;
        width: 62px;
        height: 62px;
        border-radius: 14px;
        background: var(--pt-surface);
        overflow: hidden;
      }

      .media img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        padding: 4px;
        background: #fff;
      }

      .media ha-icon {
        --mdc-icon-size: 30px;
        color: var(--secondary-text-color);
      }

      .heading {
        flex: 1;
        min-width: 0;
      }

      .merchant {
        color: var(--secondary-text-color);
        font-size: 12px;
        font-weight: 600;
      }

      h2 {
        margin: 3px 0 7px;
        font-size: 20px;
        line-height: 1.25;
        letter-spacing: -0.02em;
        word-break: break-word;
      }

      .status-line {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
      }

      .content {
        overflow-y: auto;
        padding: 18px;
        scrollbar-width: thin;
      }

      .stepper {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        margin: 2px 0 22px;
      }

      .stepper-step {
        position: relative;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 7px;
        color: var(--secondary-text-color);
        font-size: 10px;
        text-align: center;
      }

      .stepper-step::before {
        content: "";
        position: absolute;
        top: 5px;
        right: 50%;
        width: 100%;
        height: 2px;
        background: var(--pt-border);
      }

      .stepper-step:first-child::before {
        display: none;
      }

      .stepper-step[data-done="true"]::before {
        background: color-mix(in srgb, var(--primary-color) 50%, var(--pt-border));
      }

      .stepper-dot {
        position: relative;
        z-index: 1;
        width: 11px;
        height: 11px;
        border-radius: 50%;
        background: var(--pt-border);
      }

      .stepper-step[data-done="true"] .stepper-dot {
        background: var(--primary-color);
      }

      .stepper-step[data-current="true"] {
        color: var(--primary-text-color);
        font-weight: 650;
      }

      .stepper-step[data-current="true"] .stepper-dot {
        box-shadow: 0 0 0 4px color-mix(in srgb, var(--primary-color) 16%, transparent);
      }

      .note {
        margin-bottom: 16px;
        padding: 10px 12px;
        border-radius: 10px;
        background: var(--pt-surface);
        color: var(--secondary-text-color);
        font-size: 12.5px;
        line-height: 1.45;
      }

      .section {
        margin-bottom: 21px;
      }

      .section h3 {
        margin: 0 0 10px;
        font-size: 13px;
        font-weight: 650;
        letter-spacing: 0.01em;
      }

      .section-head {
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        gap: 10px;
        flex-wrap: wrap;
      }

      .info-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1px;
        overflow: hidden;
        border: 1px solid var(--pt-border);
        border-radius: 12px;
        background: var(--pt-border);
      }

      .info-row {
        display: flex;
        flex-direction: column;
        gap: 3px;
        padding: 10px 12px;
        background: var(--ha-card-background, var(--card-background-color));
        min-width: 0;
      }

      .info-label {
        color: var(--secondary-text-color);
        font-size: 10.5px;
        font-weight: 560;
      }

      .info-value {
        font-size: 13px;
        line-height: 1.35;
        word-break: break-word;
      }

      .tracking-box {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 13px;
        border: 1px solid var(--pt-border);
        border-radius: 12px;
      }

      .tracking-main {
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .tracking-main ha-icon {
        --mdc-icon-size: 18px;
        color: var(--secondary-text-color);
      }

      .tracking-number {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        font-size: 13px;
        font-weight: 600;
      }

      .copy {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        border: 0;
        background: transparent;
        color: var(--secondary-text-color);
        font-size: 11px;
      }

      .copy ha-icon {
        --mdc-icon-size: 16px;
      }

      .tracking-link {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        align-self: flex-start;
        color: var(--primary-color);
        font-size: 12.5px;
        font-weight: 620;
        text-decoration: none;
      }

      .tracking-link ha-icon {
        --mdc-icon-size: 15px;
      }

      .warning-box {
        display: flex;
        align-items: flex-start;
        gap: 7px;
        padding: 8px 9px;
        border-radius: 8px;
        color: var(--pt-warning);
        background: color-mix(in srgb, var(--pt-warning) 12%, transparent);
        font-size: 11.5px;
        line-height: 1.4;
      }

      .warning-box ha-icon {
        --mdc-icon-size: 16px;
        flex: none;
      }

      .timeline {
        position: relative;
        display: flex;
        flex-direction: column;
        gap: 0;
        margin: 0;
        padding: 0 0 0 4px;
        list-style: none;
      }

      .timeline-item {
        position: relative;
        display: flex;
        gap: 12px;
        padding: 0 0 15px;
      }

      .timeline-item::before {
        content: "";
        position: absolute;
        left: 4px;
        top: 12px;
        bottom: 0;
        width: 1px;
        background: var(--pt-border);
      }

      .timeline-item:last-child::before {
        display: none;
      }

      .timeline-dot {
        position: relative;
        z-index: 1;
        flex: none;
        width: 9px;
        height: 9px;
        margin-top: 3px;
        border-radius: 50%;
        background: var(--pt-muted);
        box-shadow: 0 0 0 3px var(--ha-card-background, var(--card-background-color));
      }

      .timeline-item[data-tone="success"] .timeline-dot {
        background: var(--pt-success);
      }

      .timeline-item[data-tone="transit"] .timeline-dot {
        background: var(--pt-transit);
      }

      .timeline-item[data-tone="warning"] .timeline-dot {
        background: var(--pt-warning);
      }

      .timeline-item[data-tone="pickup"] .timeline-dot {
        background: var(--pt-pickup);
      }

      .timeline-item[data-tone="danger"] .timeline-dot {
        background: var(--pt-danger);
      }

      .timeline-body {
        min-width: 0;
        flex: 1;
      }

      .timeline-top {
        display: flex;
        justify-content: space-between;
        gap: 10px;
        flex-wrap: wrap;
      }

      .timeline-status {
        font-size: 12.5px;
        font-weight: 650;
      }

      .timeline-time {
        color: var(--secondary-text-color);
        font-size: 10.5px;
        white-space: nowrap;
      }

      .timeline-desc {
        margin-top: 2px;
        font-size: 12px;
        line-height: 1.4;
      }

      .timeline-source {
        margin-top: 3px;
        color: var(--secondary-text-color);
        font-size: 10.5px;
      }

      .email-card {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 11px 12px;
        border: 1px solid var(--pt-border);
        border-radius: 11px;
      }

      .email-card > ha-icon {
        --mdc-icon-size: 20px;
        color: var(--secondary-text-color);
        flex: none;
      }

      .email-body {
        flex: 1;
        min-width: 0;
      }

      .email-subject {
        font-size: 12.5px;
        font-weight: 600;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .email-count {
        margin-top: 6px;
      }

      .siblings {
        display: flex;
        flex-direction: column;
        gap: 7px;
      }

      .sibling {
        display: flex;
        align-items: center;
        gap: 9px;
        width: 100%;
        padding: 9px 11px;
        border: 1px solid var(--pt-border);
        border-radius: 10px;
        background: transparent;
        color: var(--primary-text-color);
        text-align: left;
      }

      .sibling:hover {
        background: var(--pt-surface);
      }

      .sibling > ha-icon {
        --mdc-icon-size: 17px;
        color: var(--secondary-text-color);
        flex: none;
      }

      .sibling-name {
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 12.5px;
      }

      .sibling-carrier {
        color: var(--secondary-text-color);
        font-size: 10.5px;
      }

      .actions {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        flex-wrap: wrap;
        padding-top: 4px;
      }

      .secondary-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 12px;
        border: 1px solid var(--pt-border);
        border-radius: 10px;
        background: transparent;
        color: var(--primary-text-color);
        font-size: 12px;
      }

      .secondary-btn:hover {
        background: var(--pt-surface);
      }

      .secondary-btn ha-icon {
        --mdc-icon-size: 16px;
      }

      .small {
        font-size: 10.5px;
      }

      @keyframes pt-fade {
        from {
          opacity: 0;
        }
      }

      @keyframes pt-pop {
        from {
          opacity: 0;
          transform: translateY(14px) scale(0.985);
        }
      }

      @media (max-width: 640px) {
        .backdrop {
          align-items: flex-end;
          padding: 0;
        }

        .sheet {
          width: 100%;
          max-height: 94vh;
          border-radius: 20px 20px 0 0;
          border-bottom: 0;
        }

        .header {
          padding: 15px 15px 13px;
        }

        .content {
          padding: 15px;
        }

        .info-grid {
          grid-template-columns: 1fr;
        }
      }
    `,
  ];
}

if (!customElements.get("package-tracker-detail")) {
  customElements.define("package-tracker-detail", PackageDetail);
}
