import {
  FilterKey,
  PackageData,
  PackageStats,
  PackageStatus,
  SortKey,
  STATUS_LABELS,
  TrackingEvent,
} from "./types";

export type Lang = "de" | "en";

export function languageOf(language?: string): Lang {
  return (language || "de").toLowerCase().startsWith("de") ? "de" : "en";
}

export function pick(lang: Lang, de: string, en: string): string {
  return lang === "de" ? de : en;
}

export function statusLabel(status: PackageStatus | string, lang: Lang): string {
  const entry = STATUS_LABELS[status as PackageStatus];
  return entry ? entry[lang] : String(status);
}

export function isTerminal(pkg: PackageData): boolean {
  return (
    pkg.is_terminal ??
    ["delivered", "returned", "cancelled"].includes(String(pkg.status))
  );
}

export function isActive(pkg: PackageData): boolean {
  return !pkg.completed && !isTerminal(pkg);
}

export function todayISO(now = new Date()): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function parseISODate(value?: string | null): Date | null {
  if (!value) return null;
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value);
  if (!match) return null;
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

export function formatDeliveryDate(
  value: string | null | undefined,
  lang: Lang,
  now = new Date(),
): string {
  const date = parseISODate(value);
  if (!date) return pick(lang, "Kein Termin", "No date");
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const diff = Math.round((date.getTime() - today.getTime()) / 86_400_000);
  if (diff === 0) return pick(lang, "Heute", "Today");
  if (diff === 1) return pick(lang, "Morgen", "Tomorrow");
  if (diff === -1) return pick(lang, "Gestern", "Yesterday");
  const options: Intl.DateTimeFormatOptions = {
    weekday: "short",
    day: "2-digit",
    month: "2-digit",
  };
  if (date.getFullYear() !== today.getFullYear()) options.year = "numeric";
  return new Intl.DateTimeFormat(lang === "de" ? "de-DE" : "en-GB", options).format(
    date,
  );
}

export function formatDate(value: string | null | undefined, lang: Lang): string {
  const date = parseISODate(value);
  if (!date) return "–";
  return new Intl.DateTimeFormat(lang === "de" ? "de-DE" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(date);
}

export function formatDateTime(
  value: string | null | undefined,
  lang: Lang,
): string {
  if (!value) return "–";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "–";
  return new Intl.DateTimeFormat(lang === "de" ? "de-DE" : "en-GB", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

export function relativeTime(
  value: string | null | undefined,
  lang: Lang,
  now = new Date(),
): string {
  if (!value) return pick(lang, "Noch nie", "Never");
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return pick(lang, "Unbekannt", "Unknown");
  const seconds = Math.max(0, Math.round((now.getTime() - date.getTime()) / 1000));
  if (seconds < 60) return pick(lang, "gerade eben", "just now");
  const minutes = Math.round(seconds / 60);
  if (minutes < 60)
    return pick(lang, `vor ${minutes} Min.`, `${minutes} min ago`);
  const hours = Math.round(minutes / 60);
  if (hours < 24) return pick(lang, `vor ${hours} Std.`, `${hours} h ago`);
  const days = Math.round(hours / 24);
  if (days < 7) return pick(lang, `vor ${days} Tag${days === 1 ? "" : "en"}`, `${days} d ago`);
  return formatDateTime(value, lang);
}

export function statusTone(status: PackageStatus | string): string {
  switch (status) {
    case "out_for_delivery":
    case "in_transit":
    case "shipped":
      return "transit";
    case "delivered":
      return "success";
    case "delayed":
      return "warning";
    case "ready_for_pickup":
      return "pickup";
    case "returned":
    case "cancelled":
      return "danger";
    case "ordered":
      return "ordered";
    default:
      return "muted";
  }
}

export function progressIndex(status: PackageStatus | string): number {
  switch (status) {
    case "ordered":
      return 0;
    case "shipped":
      return 1;
    case "in_transit":
    case "delayed":
      return 2;
    case "out_for_delivery":
    case "ready_for_pickup":
      return 3;
    case "delivered":
      return 4;
    default:
      return -1;
  }
}

const SORT_STATUS_RANK: Record<string, number> = {
  out_for_delivery: 0,
  delayed: 1,
  in_transit: 2,
  ready_for_pickup: 3,
  shipped: 4,
  ordered: 5,
  unknown: 6,
  delivered: 7,
  returned: 8,
  cancelled: 9,
};

export function filterPackages(
  packages: PackageData[],
  filter: FilterKey,
  query: string,
  showDelivered: boolean,
  now = new Date(),
): PackageData[] {
  const today = todayISO(now);
  const needle = query.trim().toLowerCase();
  return packages.filter((pkg) => {
    if (pkg.completed) return false;
    if (!showDelivered && pkg.status === "delivered" && filter !== "delivered") {
      return false;
    }
    if (filter === "transit") {
      if (
        !["shipped", "in_transit", "out_for_delivery", "delayed"].includes(
          String(pkg.status),
        )
      ) {
        return false;
      }
    } else if (filter === "today") {
      const deliveredToday =
        pkg.status === "delivered" && pkg.actual_delivery === today;
      if (pkg.expected_delivery !== today && !deliveredToday) return false;
    } else if (filter === "delivered") {
      if (pkg.status !== "delivered") return false;
    } else if (filter === "delayed") {
      if (pkg.status !== "delayed") return false;
    } else if (filter === "pickup") {
      if (pkg.status !== "ready_for_pickup") return false;
    }
    if (!needle) return true;
    const haystack = [
      pkg.merchant,
      pkg.product_name,
      ...(pkg.product_names || []),
      pkg.tracking_number,
      pkg.order_number,
      pkg.carrier_name,
      pkg.carrier,
      pkg.status_label,
      ...(pkg.siblings || []).map((sibling) => sibling.product_name),
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    return haystack.includes(needle);
  });
}

export function sortPackages(
  packages: PackageData[],
  sortBy: SortKey,
): PackageData[] {
  const copy = [...packages];
  const dateKey = (pkg: PackageData) => {
    if (pkg.expected_delivery) return pkg.expected_delivery;
    return "9999-12-31";
  };
  if (sortBy === "carrier") {
    copy.sort(
      (a, b) =>
        (a.carrier_name || a.carrier || "").localeCompare(
          b.carrier_name || b.carrier || "",
          "de",
        ) || dateKey(a).localeCompare(dateKey(b)),
    );
  } else if (sortBy === "merchant") {
    copy.sort(
      (a, b) =>
        (a.merchant || "").localeCompare(b.merchant || "", "de") ||
        dateKey(a).localeCompare(dateKey(b)),
    );
  } else if (sortBy === "status") {
    copy.sort(
      (a, b) =>
        (SORT_STATUS_RANK[String(a.status)] ?? 99) -
          (SORT_STATUS_RANK[String(b.status)] ?? 99) ||
        dateKey(a).localeCompare(dateKey(b)),
    );
  } else {
    copy.sort((a, b) => {
      const terminalA = isTerminal(a) ? 1 : 0;
      const terminalB = isTerminal(b) ? 1 : 0;
      if (terminalA !== terminalB) return terminalA - terminalB;
      return (
        dateKey(a).localeCompare(dateKey(b)) ||
        (b.created_at || "").localeCompare(a.created_at || "")
      );
    });
  }
  return copy;
}

export function computeStats(
  packages: PackageData[],
  now = new Date(),
): PackageStats {
  const today = todayISO(now);
  const active = packages.filter((pkg) => isActive(pkg));
  const upcoming = active
    .filter(
      (pkg) =>
        pkg.expected_delivery &&
        pkg.expected_delivery >= today &&
        pkg.status !== "ready_for_pickup",
    )
    .sort((a, b) =>
      (a.expected_delivery || "9999").localeCompare(
        b.expected_delivery || "9999",
      ),
    );
  return {
    total: packages.length,
    active: active.length,
    in_transit: active.filter((pkg) =>
      ["shipped", "in_transit", "out_for_delivery", "delayed"].includes(
        String(pkg.status),
      ),
    ).length,
    delivery_today: active.filter(
      (pkg) => pkg.expected_delivery === today,
    ).length,
    delivered_today: packages.filter(
      (pkg) =>
        pkg.status === "delivered" && pkg.actual_delivery === today,
    ).length,
    delayed: active.filter((pkg) => pkg.status === "delayed").length,
    ready_for_pickup: active.filter(
      (pkg) => pkg.status === "ready_for_pickup",
    ).length,
    next_delivery: upcoming[0] || null,
  };
}

export function mergeTimeline(pkg: PackageData): TrackingEvent[] {
  const events: TrackingEvent[] = [];
  for (const event of pkg.status_history || []) {
    events.push({
      timestamp: event.timestamp,
      status: event.status,
      description: event.message || undefined,
      source: event.source || "email",
    });
  }
  for (const event of pkg.tracking_events || pkg.tracking?.events || []) {
    events.push({ ...event, source: "tracking" });
  }
  const seen = new Set<string>();
  return events
    .filter((event) => Boolean(event.timestamp))
    .sort(
      (a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
    )
    .filter((event) => {
      const key = `${event.timestamp}|${event.status}|${event.source}|${event.description}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
}

export function shortTracking(value?: string | null): string {
  if (!value) return "";
  if (value.length <= 10) return value;
  return `${value.slice(0, 4)}…${value.slice(-5)}`;
}

export function merchantInitials(merchant?: string | null): string {
  if (!merchant) return "?";
  const parts = merchant
    .replace(/[^\p{L}\p{N} &.-]/gu, "")
    .split(/[\s.&-]+/)
    .filter(Boolean);
  if (!parts.length) return merchant.slice(0, 1).toUpperCase();
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
}

export function merchantColor(merchant?: string | null): string {
  const hue = [...(merchant || "?")].reduce(
    (value, char) => (value * 31 + char.charCodeAt(0)) % 360,
    17,
  );
  return `hsl(${hue} 48% 42%)`;
}

export function emailKindLabel(kind?: string | null, lang: Lang = "de"): string {
  const labels: Record<string, { de: string; en: string }> = {
    order_confirmation: { de: "Bestellbestätigung", en: "Order confirmation" },
    shipping_confirmation: { de: "Versandbestätigung", en: "Shipping confirmation" },
    delivery_announcement: { de: "Lieferankündigung", en: "Delivery announcement" },
    tracking_update: { de: "Tracking-Update", en: "Tracking update" },
    delivered: { de: "Zustellbestätigung", en: "Delivery confirmation" },
    delay: { de: "Verspätung", en: "Delay" },
    pickup: { de: "Abholbenachrichtigung", en: "Pickup notice" },
    return: { de: "Retoure", en: "Return" },
    return_label: { de: "Retourenlabel", en: "Return label" },
    cancellation: { de: "Stornierung", en: "Cancellation" },
  };
  const entry = labels[kind || ""];
  return entry ? entry[lang] : pick(lang, "E-Mail", "E-mail");
}
