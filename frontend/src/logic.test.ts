import { describe, expect, it } from "vitest";
import {
  computeStats,
  filterPackages,
  formatDeliveryDate,
  mergeTimeline,
  progressIndex,
  shortTracking,
  sortPackages,
  statusTone,
} from "./logic";
import { PackageData } from "./types";

const now = new Date(2026, 10, 26, 12, 0, 0);

function pkg(partial: Partial<PackageData>): PackageData {
  return {
    id: partial.id || "pkg_1",
    status: "in_transit",
    merchant: "Amazon",
    product_name: "Logitech MX Master 4",
    ...partial,
  };
}

describe("filterPackages", () => {
  const packages = [
    pkg({ id: "a", status: "in_transit", expected_delivery: "2026-11-26" }),
    pkg({ id: "b", status: "delivered", actual_delivery: "2026-11-26" }),
    pkg({ id: "c", status: "delayed", expected_delivery: "2026-11-27" }),
    pkg({ id: "d", status: "ready_for_pickup" }),
    pkg({ id: "e", status: "ordered", merchant: "OTTO", product_name: "Kopfhörer" }),
  ];

  it("hides delivered parcels by default", () => {
    const result = filterPackages(packages, "all", "", false, now);
    expect(result.map((item) => item.id)).toEqual(["a", "c", "d", "e"]);
  });

  it("shows delivered parcels when requested", () => {
    const result = filterPackages(packages, "delivered", "", false, now);
    expect(result.map((item) => item.id)).toEqual(["b"]);
  });

  it("filters today including delivered today", () => {
    const result = filterPackages(packages, "today", "", true, now);
    expect(result.map((item) => item.id)).toEqual(["a", "b"]);
  });

  it("searches merchant, product and tracking", () => {
    expect(filterPackages(packages, "all", "otto", true, now)).toHaveLength(1);
    expect(
      filterPackages(packages, "all", "mx master", true, now),
    ).toHaveLength(4);
    expect(
      filterPackages(
        [pkg({ tracking_number: "00340434161094000000" })],
        "all",
        "003404",
        true,
        now,
      ),
    ).toHaveLength(1);
  });

  it("filters pickup and delayed", () => {
    expect(filterPackages(packages, "pickup", "", true, now)[0].id).toBe("d");
    expect(filterPackages(packages, "delayed", "", true, now)[0].id).toBe("c");
  });
});

describe("sortPackages", () => {
  it("sorts active parcels by expected date before delivered", () => {
    const result = sortPackages(
      [
        pkg({ id: "late", expected_delivery: "2026-12-02" }),
        pkg({ id: "delivered", status: "delivered" }),
        pkg({ id: "soon", expected_delivery: "2026-11-27" }),
      ],
      "expected",
    );
    expect(result.map((item) => item.id)).toEqual(["soon", "late", "delivered"]);
  });

  it("sorts by carrier", () => {
    const result = sortPackages(
      [
        pkg({ id: "ups", carrier_name: "UPS" }),
        pkg({ id: "dhl", carrier_name: "DHL" }),
      ],
      "carrier",
    );
    expect(result.map((item) => item.id)).toEqual(["dhl", "ups"]);
  });
});

describe("dashboard helpers", () => {
  it("computes stats from packages", () => {
    const stats = computeStats(
      [
        pkg({ id: "a", expected_delivery: "2026-11-26" }),
        pkg({ id: "b", status: "delivered", actual_delivery: "2026-11-26" }),
        pkg({ id: "c", status: "delayed" }),
        pkg({ id: "d", status: "ready_for_pickup" }),
      ],
      now,
    );
    expect(stats.in_transit).toBe(2);
    expect(stats.delivery_today).toBe(1);
    expect(stats.delivered_today).toBe(1);
    expect(stats.delayed).toBe(1);
    expect(stats.next_delivery?.id).toBe("a");
  });

  it("formats relative delivery dates", () => {
    expect(formatDeliveryDate("2026-11-26", "de", now)).toBe("Heute");
    expect(formatDeliveryDate("2026-11-27", "de", now)).toBe("Morgen");
    expect(formatDeliveryDate("2026-12-02", "de", now)).toMatch(/02\.12\./);
  });

  it("maps statuses to tones and progress", () => {
    expect(statusTone("delivered")).toBe("success");
    expect(statusTone("delayed")).toBe("warning");
    expect(progressIndex("out_for_delivery")).toBe(3);
    expect(progressIndex("delivered")).toBe(4);
  });

  it("shortens long tracking numbers", () => {
    expect(shortTracking("00340434161094000000")).toBe("0034…00000");
    expect(shortTracking("TBA123")).toBe("TBA123");
  });

  it("merges and de-duplicates e-mail and tracking history", () => {
    const events = mergeTimeline(
      pkg({
        status_history: [
          { status: "ordered", timestamp: "2026-11-20T10:00:00+00:00", source: "email" },
          { status: "shipped", timestamp: "2026-11-21T10:00:00+00:00", source: "email" },
        ],
        tracking_events: [
          { status: "in_transit", timestamp: "2026-11-22T10:00:00+00:00" },
          { status: "in_transit", timestamp: "2026-11-22T10:00:00+00:00" },
        ],
      }),
    );
    expect(events).toHaveLength(3);
    expect(events[0].status).toBe("in_transit");
  });
});
