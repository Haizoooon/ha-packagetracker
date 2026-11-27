// @vitest-environment jsdom
import { describe, expect, it } from "vitest";
import {
  PackageTrackerCard,
} from "./package-tracker-card";
import { PackageTrackerCardEditor } from "./package-editor";
import { DEFAULT_CONFIG } from "./types";

describe("Lovelace card registration", () => {
  it("defines the custom elements and card picker metadata", () => {
    expect(customElements.get("package-tracker-card")).toBeDefined();
    expect(customElements.get("package-tracker-card-editor")).toBeDefined();
    expect(window.customCards?.some((card) => card.type === "package-tracker-card")).toBe(
      true,
    );
  });

  it("supplies a stub config and visual editor element", () => {
    const stub = PackageTrackerCard.getStubConfig();
    expect(stub.max_packages).toBe(DEFAULT_CONFIG.max_packages);
    expect(stub.type).toBe("package-tracker-card");
    const editor = PackageTrackerCard.getConfigElement();
    expect(editor.tagName.toLowerCase()).toBe("package-tracker-card-editor");
    expect(editor).toBeInstanceOf(PackageTrackerCardEditor);
  });

  it("normalizes invalid card configuration", () => {
    const card = document.createElement("package-tracker-card") as PackageTrackerCard;
    card.setConfig({
      type: "custom:package-tracker-card",
      max_packages: 0,
      default_filter: "nonsense" as never,
      sort_by: "nonsense" as never,
    });
    expect(card.getCardSize()).toBeGreaterThan(0);
    expect(() => card.setConfig(null as never)).toThrow();
  });

  it("applies editor values through config-changed events", async () => {
    const editor = document.createElement(
      "package-tracker-card-editor",
    ) as PackageTrackerCardEditor;
    document.body.appendChild(editor);
    editor.setConfig({ type: "custom:package-tracker-card" });
    await editor.updateComplete;
    let received: unknown = null;
    editor.addEventListener("config-changed", (event) => {
      received = (event as CustomEvent).detail.config;
    });
    const input = editor.shadowRoot?.querySelector<HTMLInputElement>(
      'input[type="text"]',
    );
    expect(input).toBeTruthy();
    if (input) {
      input.value = "Meine Pakete";
      input.dispatchEvent(new Event("change"));
    }
    expect(received).toMatchObject({ title: "Meine Pakete" });
    editor.remove();
  });
});

describe("responsive theming", () => {
  it("uses Home Assistant CSS variables and mobile breakpoints", () => {
    const cssText = (PackageTrackerCard.styles as Array<{ cssText: string }>)
      .map((style) => style.cssText)
      .join("\n");
    expect(cssText).toContain("var(--primary-text-color)");
    expect(cssText).toContain("var(--card-background-color)");
    expect(cssText).toContain("@media (max-width: 560px)");
    expect(cssText).toContain("prefers-reduced-motion");
  });
});

describe("card rendering with data", () => {
  it("renders overview cards from the websocket payload", async () => {
    const card = document.createElement("package-tracker-card") as PackageTrackerCard;
    document.body.appendChild(card);
    card.setConfig({ type: "custom:package-tracker-card" });
    const snapshot = {
      version: 1,
      generated_at: new Date().toISOString(),
      packages: [
        {
          id: "pkg_test",
          merchant: "Amazon",
          product_name: "Logitech MX Master 4",
          status: "in_transit",
          carrier: "dhl",
          carrier_name: "DHL",
          tracking_number: "00340434161094000000",
          expected_delivery: new Date().toISOString().slice(0, 10),
          delivery_window: "14:00–18:00 Uhr",
        },
      ],
      orders: [],
      stats: {
        total: 1,
        active: 1,
        in_transit: 1,
        delivery_today: 1,
        delivered_today: 0,
        delayed: 0,
        ready_for_pickup: 0,
        next_delivery: null,
      },
      gmail: {
        connected: true,
        account: "t***@example.com",
        last_sync: new Date().toISOString(),
        emails_processed: 3,
      },
    };
    card.hass = {
      states: {},
      language: "de",
      callWS: async () => snapshot,
      callService: async () => ({}),
      connection: { subscribeEvents: async () => () => undefined },
    } as never;
    await card.updateComplete;
    await new Promise((resolve) => setTimeout(resolve, 0));
    await card.updateComplete;
    const tiles = card.shadowRoot?.querySelectorAll("package-tracker-package-card");
    expect(tiles?.length).toBe(1);
    const packageCard = tiles?.[0] as HTMLElement & { updateComplete?: Promise<unknown> };
    await packageCard.updateComplete;
    expect(packageCard.shadowRoot?.textContent).toContain("Logitech MX Master 4");
    card.remove();
  });
});
