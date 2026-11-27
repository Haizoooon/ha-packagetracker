import { LitElement, css, html, nothing } from "lit";
import "./package-overview";
import "./package-card";
import "./package-detail";
import "./package-editor";
import { sharedStyles } from "./styles/shared";
import {
  DEFAULT_CONFIG,
  FILTER_LABELS,
  FilterKey,
  GmailInfo,
  HomeAssistant,
  PackageData,
  PackageStats,
  PackageTrackerCardConfig,
  SORT_LABELS,
  Snapshot,
  SortKey,
} from "./types";
import {
  Lang,
  computeStats,
  filterPackages,
  languageOf,
  pick,
  relativeTime,
  sortPackages,
} from "./logic";

declare global {
  interface Window {
    customCards?: Array<Record<string, unknown>>;
  }
}

const CARD_TYPE = "package-tracker-card";
const SUBSCRIPTION_EVENT = "package_tracker_updated";

export class PackageTrackerCard extends LitElement {
  static properties = {
    hass: { attribute: false },
    _config: { state: true },
    _data: { state: true },
    _loading: { state: true },
    _error: { state: true },
    _syncError: { state: true },
    _syncing: { state: true },
    _filter: { state: true },
    _sort: { state: true },
    _search: { state: true },
    _openId: { state: true },
    _fallbackMode: { state: true },
  };

  declare hass: HomeAssistant;
  declare _config: Required<Omit<PackageTrackerCardConfig, "type">>;
  declare _data: Snapshot | null;
  declare _loading: boolean;
  declare _error: string | null;
  declare _syncError: string | null;
  declare _syncing: boolean;
  declare _filter: FilterKey;
  declare _sort: SortKey;
  declare _search: string;
  declare _openId: string | null;
  declare _fallbackMode: boolean;

  private _unsubscribe: (() => void) | null = null;
  private _subscribing = false;
  private _disposed = false;
  private _reloadTimer: number | null = null;
  private _pollTimer: number | null = null;
  private _pendingReload = false;
  private _lastSensorStamp: string | undefined;

  static getConfigElement(): HTMLElement {
    return document.createElement("package-tracker-card-editor");
  }

  static getStubConfig(): PackageTrackerCardConfig {
    return { type: CARD_TYPE, ...DEFAULT_CONFIG };
  }

  constructor() {
    super();
    this._config = { ...DEFAULT_CONFIG };
    this._data = null;
    this._loading = false;
    this._error = null;
    this._syncError = null;
    this._syncing = false;
    this._filter = DEFAULT_CONFIG.default_filter;
    this._sort = DEFAULT_CONFIG.sort_by;
    this._search = "";
    this._openId = null;
    this._fallbackMode = false;
  }

  setConfig(config: PackageTrackerCardConfig): void {
    if (!config || typeof config !== "object") {
      throw new Error("Invalid Package Tracker configuration");
    }
    const merged = { ...DEFAULT_CONFIG, ...config };
    merged.max_packages = Math.max(
      1,
      Math.min(200, Number(merged.max_packages) || DEFAULT_CONFIG.max_packages),
    );
    if (!(merged.default_filter in FILTER_LABELS)) {
      merged.default_filter = DEFAULT_CONFIG.default_filter;
    }
    if (!(merged.sort_by in SORT_LABELS)) {
      merged.sort_by = DEFAULT_CONFIG.sort_by;
    }
    this._config = merged;
    this._filter = merged.default_filter;
    this._sort = merged.sort_by;
  }

  getCardSize(): number {
    const count = this._data?.packages.length || 0;
    return (this._config.show_stats ? 4 : 0) + 3 + Math.min(6, Math.ceil(count / 2)) * 3;
  }

  getGridOptions() {
    return {
      columns: 12,
      min_columns: 6,
      rows: "auto",
    };
  }

  connectedCallback() {
    super.connectedCallback();
    this._disposed = false;
  }

  disconnectedCallback() {
    this._disposed = true;
    if (this._reloadTimer !== null) window.clearTimeout(this._reloadTimer);
    if (this._pollTimer !== null) window.clearInterval(this._pollTimer);
    this._pollTimer = null;
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = null;
    }
    super.disconnectedCallback();
  }

  protected updated(changed: Map<PropertyKey, unknown>) {
    if (changed.has("hass") && this.hass) {
      this._ensureSubscription();
      if (!this._data && !this._loading) void this._load();
      const aggregate = this.hass.states["sensor.package_tracker_packages"];
      if (aggregate?.last_updated && aggregate.last_updated !== this._lastSensorStamp) {
        this._lastSensorStamp = aggregate.last_updated;
        if (this._data && !this._loading) this._scheduleLoad();
      }
    }
  }

  private _ensureSubscription() {
    if (
      this._unsubscribe ||
      this._subscribing ||
      !this.hass?.connection?.subscribeEvents
    ) {
      return;
    }
    this._subscribing = true;
    this.hass.connection
      .subscribeEvents(() => this._scheduleLoad(), SUBSCRIPTION_EVENT)
      .then((unsubscribe) => {
        this._unsubscribe = unsubscribe;
        if (this._disposed) {
          unsubscribe();
          this._unsubscribe = null;
        }
      })
      .catch(() => {
        this._startPolling();
      })
      .finally(() => {
        this._subscribing = false;
      });
  }

  private _startPolling() {
    if (this._pollTimer !== null) return;
    this._pollTimer = window.setInterval(() => {
      if (!this._loading) void this._load();
    }, 60_000);
  }

  private _scheduleLoad() {
    if (this._reloadTimer !== null) window.clearTimeout(this._reloadTimer);
    this._reloadTimer = window.setTimeout(() => {
      this._reloadTimer = null;
      void this._load();
    }, 450);
  }

  private async _load() {
    if (!this.hass) return;
    if (this._loading) {
      this._pendingReload = true;
      return;
    }
    this._loading = true;
    this._error = null;
    try {
      const snapshot = await this.hass.callWS<Snapshot>({
        type: "package_tracker/packages",
      });
      if (!snapshot || !Array.isArray(snapshot.packages)) {
        throw new Error(
          pick(this._lang, "Invalid response from the integration", "Ungültige Antwort der Integration"),
        );
      }
      this._data = snapshot;
      this._fallbackMode = false;
    } catch (err) {
      const fallback = this._fallbackSnapshot();
      if (fallback) {
        this._data = fallback;
        this._fallbackMode = true;
        this._error = null;
      } else {
        this._error =
          err instanceof Error
            ? err.message
            : pick(this._lang, "Unbekannter Fehler", "Unknown error");
      }
    } finally {
      this._loading = false;
      if (this._pendingReload) {
        this._pendingReload = false;
        void this._load();
      }
    }
  }

  private _fallbackSnapshot(): Snapshot | null {
    const entity = this.hass.states["sensor.package_tracker_packages"];
    if (!entity) return null;
    const attrs = entity.attributes;
    const compact = Array.isArray(attrs.packages)
      ? (attrs.packages as PackageData[])
      : [];
    const byId = new Map<string, PackageData>();
    for (const pkg of compact) {
      if (pkg?.id) byId.set(pkg.id, pkg);
    }
    for (const state of Object.values(this.hass.states)) {
      if (!state.entity_id.startsWith("sensor.package_tracker_package_")) continue;
      const full = state.attributes as unknown as PackageData;
      const id = (full.package_id || full.id) as string | undefined;
      if (id) byId.set(id, { ...(byId.get(id) || {}), ...full, id } as PackageData);
    }
    const packages = [...byId.values()];
    const counts = (attrs.counts || {}) as Partial<PackageStats>;
    const stats: PackageStats = {
      ...computeStats(packages),
      ...counts,
      next_delivery: (counts.next_delivery as PackageData | null) ?? null,
    } as PackageStats;
    const gmail = (attrs.gmail || {}) as GmailInfo;
    return {
      version: 1,
      generated_at: String(attrs.updated_at || new Date().toISOString()),
      packages,
      orders: [],
      stats,
      gmail: {
        connected: Boolean(gmail.connected),
        account: gmail.account || null,
        last_sync: gmail.last_sync || null,
        emails_processed: gmail.emails_processed || 0,
      },
    };
  }

  private async _sync() {
    if (this._syncing || !this.hass) return;
    this._syncing = true;
    this._syncError = null;
    try {
      await this.hass.callService("package_tracker", "sync", {});
      await this._load();
    } catch (err) {
      this._syncError =
        err instanceof Error
          ? err.message
          : pick(this._lang, "Synchronisierung fehlgeschlagen", "Sync failed");
    } finally {
      this._syncing = false;
    }
  }

  private get _lang(): Lang {
    return languageOf(this.hass?.language);
  }

  private get _visiblePackages(): PackageData[] {
    if (!this._data) return [];
    const filtered = filterPackages(
      this._data.packages,
      this._filter,
      this._search,
      this._config.show_delivered,
    );
    return sortPackages(filtered, this._sort).slice(
      0,
      this._config.max_packages,
    );
  }

  private get _openPackage(): PackageData | null {
    if (!this._data || !this._openId) return null;
    return this._data.packages.find((pkg) => pkg.id === this._openId) || null;
  }

  private _filterCount(filter: FilterKey): number {
    if (!this._data) return 0;
    if (filter === "all") {
      return this._data.packages.filter((pkg) => !pkg.completed).length;
    }
    return filterPackages(
      this._data.packages,
      filter,
      "",
      true,
    ).length;
  }

  private _renderHeader() {
    const lang = this._lang;
    const data = this._data;
    const gmail = data?.gmail;
    const account = gmail?.account || "";
    const syncText = gmail?.last_sync
      ? `${pick(lang, "Synchronisiert", "Synced")} ${relativeTime(gmail.last_sync, lang)}`
      : pick(lang, "Noch nicht synchronisiert", "Not synced yet");
    return html`
      <header class="header">
        <div class="brand">
          <div class="brand-icon">
            <ha-icon icon="mdi:package-variant-closed"></ha-icon>
          </div>
          <div class="brand-text">
            <h2>${this._config.title || pick(lang, "Pakete", "Parcels")}</h2>
            <div class="sub">
              ${gmail?.connected
                ? html`<span class="gmail-ok"
                      ><ha-icon icon="mdi:gmail"></ha-icon>${account}</span
                    >`
                : html`<span class="gmail-off"
                    ><ha-icon icon="mdi:gmail-off"></ha-icon
                    >${pick(lang, "Gmail nicht verbunden", "Gmail not connected")}</span
                  >`}
              ${this._config.show_last_sync
                ? html`<span class="dot">·</span><span>${syncText}</span>`
                : nothing}
              ${this._fallbackMode
                ? html`<span class="pill warning"
                    >${pick(lang, "Eingeschränkter Modus", "Limited mode")}</span
                  >`
                : nothing}
            </div>
          </div>
        </div>
        <button
          class="icon-btn sync ${this._syncing ? "spinning" : ""}"
          @click=${this._sync}
          ?disabled=${this._syncing}
          title=${pick(lang, "Gmail jetzt synchronisieren", "Sync Gmail now")}
          aria-label=${pick(lang, "Gmail jetzt synchronisieren", "Sync Gmail now")}
        >
          <ha-icon icon="mdi:email-sync"></ha-icon>
        </button>
      </header>
      ${this._syncError
        ? html`<div class="inline-error">
            <ha-icon icon="mdi:alert-circle-outline"></ha-icon>
            <span>${this._syncError}</span>
          </div>`
        : nothing}
    `;
  }

  private _renderToolbar() {
    const lang = this._lang;
    const filters: FilterKey[] = [
      "all",
      "transit",
      "today",
      "delivered",
      "delayed",
      "pickup",
    ];
    return html`
      <div class="toolbar">
        <div class="chips" role="tablist" aria-label=${pick(lang, "Filter", "Filters")}>
          ${filters.map((key) => {
            const count = this._filterCount(key);
            return html`
              <button
                class="chip"
                role="tab"
                aria-selected=${this._filter === key}
                data-active=${this._filter === key}
                @click=${() => {
                  this._filter = key;
                }}
              >
                ${FILTER_LABELS[key][lang]}
                ${key !== "all" && count > 0
                  ? html`<span class="chip-count">${count}</span>`
                  : nothing}
              </button>
            `;
          })}
        </div>
        <div class="tools">
          ${this._config.show_search
            ? html`<label class="search">
                <ha-icon icon="mdi:magnify"></ha-icon>
                <input
                  type="search"
                  .value=${this._search}
                  placeholder=${pick(
                    lang,
                    "Händler, Produkt, Sendungsnummer",
                    "Merchant, product, tracking",
                  )}
                  aria-label=${pick(lang, "Pakete durchsuchen", "Search parcels")}
                  @input=${(event: Event) => {
                    this._search = (event.target as HTMLInputElement).value;
                  }}
                />
              </label>`
            : nothing}
          <label class="sort">
            <span class="visually-hidden"
              >${pick(lang, "Sortierung", "Sorting")}</span
            >
            <ha-icon icon="mdi:sort-variant"></ha-icon>
            <select
              .value=${this._sort}
              aria-label=${pick(lang, "Sortierung", "Sorting")}
              @change=${(event: Event) => {
                this._sort = (event.target as HTMLSelectElement).value as SortKey;
              }}
            >
              ${(Object.keys(SORT_LABELS) as SortKey[]).map(
                (key) => html`<option value=${key}>${SORT_LABELS[key][lang]}</option>`,
              )}
            </select>
          </label>
        </div>
      </div>
    `;
  }

  private _renderSkeleton() {
    return html`
      <div class="stats-skeleton">
        ${[0, 1, 2, 3].map(
          () => html`
            <div class="tile-skeleton">
              <div class="skeleton line short"></div>
              <div class="skeleton line value"></div>
              <div class="skeleton line tiny"></div>
            </div>
          `,
        )}
      </div>
      <div class="grid">
        ${[0, 1, 2].map(
          () => html`
            <div class="card-skeleton">
              <div class="skeleton avatar"></div>
              <div class="skeleton line"></div>
              <div class="skeleton line short"></div>
              <div class="skeleton line tiny"></div>
            </div>
          `,
        )}
      </div>
    `;
  }

  private _renderEmpty() {
    const lang = this._lang;
    const hasPackages = Boolean(this._data?.packages.length);
    return html`
      <div class="state">
        <div class="state-icon">
          <ha-icon icon=${hasPackages ? "mdi:filter-variant-remove" : "mdi:package-variant"}></ha-icon>
        </div>
        <h3>
          ${hasPackages
            ? pick(lang, "Keine Pakete für diesen Filter", "No parcels for this filter")
            : pick(lang, "Noch keine Pakete erkannt", "No parcels detected yet")}
        </h3>
        <p>
          ${hasPackages
            ? pick(
                lang,
                "Passe Filter oder Suche an, um weitere Pakete zu sehen.",
                "Adjust the filter or search to see more parcels.",
              )
            : pick(
                lang,
                "Sobald Bestell- oder Versand-E-Mails eintreffen, erscheinen die Pakete automatisch hier.",
                "Parcels appear here automatically once order or shipping e-mails arrive.",
              )}
        </p>
        ${hasPackages
          ? html`<button
              class="primary-btn"
              @click=${() => {
                this._filter = "all";
                this._search = "";
              }}
            >
              ${pick(lang, "Filter zurücksetzen", "Reset filters")}
            </button>`
          : html`<button class="primary-btn" @click=${this._sync} ?disabled=${this._syncing}>
              <ha-icon icon="mdi:email-sync"></ha-icon>
              ${pick(lang, "Gmail synchronisieren", "Sync Gmail")}
            </button>`}
      </div>
    `;
  }

  private _renderError() {
    const lang = this._lang;
    return html`
      <div class="state error">
        <div class="state-icon">
          <ha-icon icon="mdi:cloud-alert-outline"></ha-icon>
        </div>
        <h3>${pick(lang, "Paketdaten nicht verfügbar", "Package data unavailable")}</h3>
        <p>${this._error}</p>
        <div class="state-actions">
          <button class="primary-btn" @click=${() => void this._load()}>
            ${pick(lang, "Erneut versuchen", "Try again")}
          </button>
          <button class="secondary-btn" @click=${this._sync} ?disabled=${this._syncing}>
            ${pick(lang, "Gmail synchronisieren", "Sync Gmail")}
          </button>
        </div>
      </div>
    `;
  }

  render() {
    const lang = this._lang;
    const data = this._data;
    const visible = this._visiblePackages;
    const totalMatching = data
      ? filterPackages(
          data.packages,
          this._filter,
          this._search,
          this._config.show_delivered,
        ).length
      : 0;

    return html`
      <ha-card class="root">
        ${this._renderHeader()}
        ${this._config.show_stats && data
          ? html`
              <package-tracker-overview
                .stats=${data.stats}
                .lang=${lang}
                .filter=${this._filter}
                @filter-select=${(event: CustomEvent<{ filter: FilterKey }>) => {
                  this._filter = event.detail.filter;
                }}
                @package-open=${(event: CustomEvent<{ id: string }>) => {
                  this._openId = event.detail.id;
                }}
              ></package-tracker-overview>
            `
          : nothing}

        ${data ? this._renderToolbar() : nothing}

        ${this._loading && !data
          ? this._renderSkeleton()
          : this._error && !data
            ? this._renderError()
            : visible.length
              ? html`
                  <div class="grid ${this._config.compact ? "compact" : ""}">
                    ${visible.map(
                      (pkg) => html`
                        <package-tracker-package-card
                          .pkg=${pkg}
                          .lang=${lang}
                          .showImages=${this._config.show_images}
                          .showDeliveryDates=${this._config.show_delivery_dates}
                          ?compact=${this._config.compact}
                          @package-open=${(event: CustomEvent<{ id: string }>) => {
                            this._openId = event.detail.id;
                          }}
                        ></package-tracker-package-card>
                      `,
                    )}
                  </div>
                  <div class="footer">
                    <span>
                      ${totalMatching > visible.length
                        ? pick(
                            lang,
                            `${visible.length} von ${totalMatching} Paketen angezeigt`,
                            `${visible.length} of ${totalMatching} parcels shown`,
                          )
                        : pick(
                            lang,
                            `${visible.length} Paket${visible.length === 1 ? "" : "e"}`,
                            `${visible.length} parcel${visible.length === 1 ? "" : "s"}`,
                          )}
                    </span>
                    <span class="muted"
                      >${pick(lang, "Stand", "Updated")}
                      ${relativeTime(this._data?.generated_at, lang)}</span
                    >
                  </div>
                `
              : this._renderEmpty()}

        <package-tracker-detail
          .pkg=${this._openPackage}
          .hass=${this.hass}
          .lang=${lang}
          .showImages=${this._config.show_images}
          ?open=${Boolean(this._openPackage)}
          @package-close=${() => {
            this._openId = null;
          }}
          @package-open=${(event: CustomEvent<{ id: string }>) => {
            this._openId = event.detail.id;
          }}
        ></package-tracker-detail>
      </ha-card>
    `;
  }

  static styles = [
    sharedStyles,
    css`
      :host {
        display: block;
      }

      ha-card {
        display: block;
        overflow: visible;
        background: var(--ha-card-background, var(--card-background-color));
        border-radius: var(--pt-radius);
      }

      .root {
        padding: 16px;
      }

      .header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 15px;
      }

      .brand {
        display: flex;
        align-items: center;
        gap: 11px;
        min-width: 0;
      }

      .brand-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        flex: none;
        width: 40px;
        height: 40px;
        border-radius: 12px;
        background: color-mix(in srgb, var(--primary-color) 12%, transparent);
        color: var(--primary-color);
      }

      .brand-icon ha-icon {
        --mdc-icon-size: 23px;
      }

      .brand-text {
        min-width: 0;
      }

      h2 {
        margin: 0;
        font-size: 19px;
        font-weight: 680;
        letter-spacing: -0.02em;
        line-height: 1.2;
      }

      .sub {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: 5px;
        margin-top: 3px;
        color: var(--secondary-text-color);
        font-size: 11px;
        line-height: 1.3;
      }

      .sub span {
        display: inline-flex;
        align-items: center;
        gap: 3px;
      }

      .sub ha-icon {
        --mdc-icon-size: 13px;
      }

      .gmail-ok ha-icon {
        color: var(--pt-danger);
      }

      .dot {
        opacity: 0.5;
      }

      .sync ha-icon {
        --mdc-icon-size: 20px;
      }

      .sync.spinning ha-icon {
        animation: pt-spin 900ms linear infinite;
      }

      .inline-error {
        display: flex;
        align-items: center;
        gap: 6px;
        margin: -6px 0 12px;
        padding: 7px 9px;
        border-radius: 8px;
        background: color-mix(in srgb, var(--pt-danger) 10%, transparent);
        color: var(--pt-danger);
        font-size: 11.5px;
      }

      .inline-error ha-icon {
        --mdc-icon-size: 15px;
      }

      .toolbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 13px;
      }

      .chips {
        display: flex;
        gap: 6px;
        min-width: 0;
        overflow-x: auto;
        scrollbar-width: none;
        padding: 1px;
      }

      .chips::-webkit-scrollbar {
        display: none;
      }

      .chip {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        flex: none;
        padding: 6px 10px;
        border: 1px solid var(--pt-border);
        border-radius: 999px;
        background: transparent;
        color: var(--secondary-text-color);
        font-size: 11.5px;
        font-weight: 560;
        white-space: nowrap;
        transition:
          background 140ms var(--pt-ease),
          color 140ms var(--pt-ease),
          border-color 140ms var(--pt-ease);
      }

      .chip:hover {
        color: var(--primary-text-color);
        background: var(--pt-surface);
      }

      .chip[data-active="true"] {
        border-color: color-mix(in srgb, var(--primary-color) 45%, transparent);
        background: color-mix(in srgb, var(--primary-color) 11%, transparent);
        color: var(--primary-color);
        font-weight: 650;
      }

      .chip-count {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 16px;
        height: 16px;
        padding: 0 4px;
        border-radius: 999px;
        background: var(--pt-surface);
        font-size: 9.5px;
        font-weight: 650;
      }

      .chip[data-active="true"] .chip-count {
        background: color-mix(in srgb, var(--primary-color) 16%, transparent);
      }

      .tools {
        display: flex;
        align-items: center;
        gap: 7px;
        flex: none;
      }

      .search,
      .sort {
        display: flex;
        align-items: center;
        gap: 6px;
        height: 34px;
        padding: 0 9px;
        border: 1px solid var(--pt-border);
        border-radius: 10px;
        background: var(--pt-surface);
        color: var(--secondary-text-color);
      }

      .search ha-icon,
      .sort ha-icon {
        --mdc-icon-size: 16px;
        flex: none;
      }

      .search input {
        width: clamp(120px, 18vw, 210px);
        border: 0;
        outline: none;
        background: transparent;
        color: var(--primary-text-color);
        font-size: 12px;
      }

      .search input::placeholder {
        color: var(--secondary-text-color);
      }

      .sort select {
        max-width: 145px;
        border: 0;
        outline: none;
        background: transparent;
        color: var(--primary-text-color);
        font-size: 11.5px;
        cursor: pointer;
      }

      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(268px, 1fr));
        gap: 11px;
      }

      .grid.compact {
        grid-template-columns: 1fr;
        gap: 7px;
      }

      .footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        margin-top: 12px;
        padding-top: 10px;
        border-top: 1px solid var(--pt-border);
        color: var(--secondary-text-color);
        font-size: 10.5px;
      }

      .footer .muted {
        color: var(--secondary-text-color);
      }

      .state {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 38px 18px 42px;
      }

      .state-icon {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 58px;
        height: 58px;
        margin-bottom: 13px;
        border-radius: 18px;
        background: var(--pt-surface);
        color: var(--secondary-text-color);
      }

      .state-icon ha-icon {
        --mdc-icon-size: 28px;
      }

      .state.error .state-icon {
        color: var(--pt-danger);
        background: color-mix(in srgb, var(--pt-danger) 10%, transparent);
      }

      .state h3 {
        margin: 0 0 5px;
        font-size: 15px;
      }

      .state p {
        max-width: 420px;
        margin: 0 0 16px;
        color: var(--secondary-text-color);
        font-size: 12px;
        line-height: 1.5;
      }

      .state-actions {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: center;
      }

      .primary-btn,
      .secondary-btn {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 8px 13px;
        border-radius: 10px;
        border: 1px solid transparent;
        font-size: 12px;
        font-weight: 600;
      }

      .primary-btn {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
      }

      .primary-btn:disabled {
        opacity: 0.55;
        cursor: default;
      }

      .secondary-btn {
        border-color: var(--pt-border);
        background: transparent;
        color: var(--primary-text-color);
      }

      .primary-btn ha-icon {
        --mdc-icon-size: 16px;
      }

      .stats-skeleton {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
        margin-bottom: 16px;
      }

      .tile-skeleton {
        display: flex;
        flex-direction: column;
        gap: 8px;
        padding: 13px;
        border: 1px solid var(--pt-border);
        border-radius: 14px;
      }

      .line {
        height: 12px;
        border-radius: 6px;
      }

      .line.short {
        width: 55%;
      }

      .line.tiny {
        width: 72%;
        height: 9px;
      }

      .line.value {
        width: 40%;
        height: 22px;
      }

      .card-skeleton {
        display: flex;
        flex-direction: column;
        gap: 9px;
        padding: 15px;
        border: 1px solid var(--pt-border);
        border-radius: var(--pt-radius);
      }

      .card-skeleton .avatar {
        width: 48px;
        height: 48px;
        border-radius: 12px;
      }

      .visually-hidden {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
      }

      @keyframes pt-spin {
        to {
          transform: rotate(360deg);
        }
      }

      @media (max-width: 820px) {
        .toolbar {
          flex-direction: column;
          align-items: stretch;
        }

        .tools {
          justify-content: space-between;
        }

        .search {
          flex: 1;
        }

        .search input {
          width: 100%;
        }

        .grid {
          grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
        }
      }

      @media (max-width: 560px) {
        .root {
          padding: 13px;
        }

        h2 {
          font-size: 17px;
        }

        .grid {
          grid-template-columns: 1fr;
        }

        .stats-skeleton {
          grid-template-columns: repeat(2, 1fr);
        }

        .sort {
          display: none;
        }

        .footer {
          flex-direction: column;
          align-items: flex-start;
          gap: 3px;
        }
      }
    `,
  ];
}

if (!customElements.get(CARD_TYPE)) {
  customElements.define(CARD_TYPE, PackageTrackerCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((card) => card.type === CARD_TYPE)) {
  window.customCards.push({
    type: CARD_TYPE,
    name: "Package Tracker",
    description:
      "Intelligent parcel overview with filters, detail view and optional tracking.",
    preview: false,
    documentationURL: "https://github.com/Haizoooon/ha-packagetracker",
  });
}
