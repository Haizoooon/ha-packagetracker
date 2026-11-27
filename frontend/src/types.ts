export interface HassEntity {
  entity_id: string;
  state: string;
  attributes: Record<string, unknown>;
  last_changed?: string;
  last_updated?: string;
}

export interface HassConnection {
  subscribeEvents: (
    callback: (event: { event_type: string; data: Record<string, unknown> }) => void,
    eventType: string,
  ) => Promise<() => void>;
}

export interface HomeAssistant {
  states: Record<string, HassEntity>;
  callService: (
    domain: string,
    service: string,
    data?: Record<string, unknown>,
    target?: Record<string, unknown>,
  ) => Promise<unknown>;
  callWS: <T>(message: Record<string, unknown>) => Promise<T>;
  connection: HassConnection;
  language?: string;
  locale?: { language?: string };
  [key: string]: unknown;
}

export interface StatusEvent {
  status: string;
  timestamp: string;
  source: string;
  message?: string | null;
  email_id?: string | null;
}

export interface EmailRef {
  id: string;
  received_at: string;
  kind: string;
  subject?: string | null;
  sender?: string | null;
  status?: string | null;
}

export interface TrackingEvent {
  timestamp: string;
  status?: string | null;
  description?: string | null;
  location?: string | null;
  source?: string;
}

export interface TrackingInfo {
  provider: string;
  last_checked?: string | null;
  status?: string | null;
  expected_delivery?: string | null;
  events?: TrackingEvent[];
  error?: string | null;
}

export interface Order {
  id: string;
  merchant?: string | null;
  order_number?: string | null;
  order_date?: string | null;
  product_names?: string[];
  product_image?: string | null;
  shipment_ids?: string[];
  emails?: EmailRef[];
  status?: string;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PackageSibling {
  id: string;
  tracking_number?: string | null;
  carrier?: string | null;
  status?: string;
  product_name?: string;
  expected_delivery?: string | null;
}

export type PackageStatus =
  | "ordered"
  | "shipped"
  | "in_transit"
  | "out_for_delivery"
  | "delivered"
  | "delayed"
  | "ready_for_pickup"
  | "returned"
  | "cancelled"
  | "unknown";

export interface PackageData {
  id: string;
  order_id?: string | null;
  merchant?: string | null;
  carrier?: string | null;
  carrier_name?: string | null;
  product_name?: string | null;
  product_names?: string[];
  product_image?: string | null;
  order_number?: string | null;
  tracking_number?: string | null;
  tracking_url?: string | null;
  order_date?: string | null;
  shipped_date?: string | null;
  expected_delivery?: string | null;
  delivery_window?: string | null;
  actual_delivery?: string | null;
  status: PackageStatus;
  status_label?: string;
  status_changed_at?: string | null;
  status_history?: StatusEvent[];
  emails?: EmailRef[];
  last_email_at?: string | null;
  last_email_subject?: string | null;
  last_email_from?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
  completed?: boolean;
  notes?: string | null;
  tracking?: TrackingInfo | null;
  tracking_events?: TrackingEvent[];
  source?: string;
  manual_override?: boolean;
  display_name?: string;
  is_active?: boolean;
  is_terminal?: boolean;
  order?: Order | null;
  siblings?: PackageSibling[];
  config_entry_id?: string;
  package_id?: string;
  [key: string]: unknown;
}

export interface PackageStats {
  total: number;
  active: number;
  in_transit: number;
  delivery_today: number;
  delivered_today: number;
  delayed: number;
  ready_for_pickup: number;
  next_delivery: PackageData | null;
}

export interface GmailInfo {
  connected: boolean;
  account?: string | null;
  last_sync?: string | null;
  emails_processed?: number;
}

export interface Snapshot {
  version: number;
  generated_at: string;
  packages: PackageData[];
  orders: Order[];
  stats: PackageStats;
  gmail: GmailInfo;
}

export type FilterKey =
  | "all"
  | "transit"
  | "today"
  | "delivered"
  | "delayed"
  | "pickup";

export type SortKey = "expected" | "carrier" | "merchant" | "status";

export interface PackageTrackerCardConfig {
  type?: string;
  title?: string;
  max_packages?: number;
  show_delivered?: boolean;
  show_images?: boolean;
  show_delivery_dates?: boolean;
  compact?: boolean;
  default_filter?: FilterKey;
  sort_by?: SortKey;
  show_stats?: boolean;
  show_search?: boolean;
  show_last_sync?: boolean;
}

export const DEFAULT_CONFIG: Required<Omit<PackageTrackerCardConfig, "type">> = {
  title: "",
  max_packages: 24,
  show_delivered: false,
  show_images: true,
  show_delivery_dates: true,
  compact: false,
  default_filter: "all",
  sort_by: "expected",
  show_stats: true,
  show_search: true,
  show_last_sync: true,
};

export const FILTER_LABELS: Record<FilterKey, { de: string; en: string }> = {
  all: { de: "Alle", en: "All" },
  transit: { de: "Unterwegs", en: "In transit" },
  today: { de: "Heute", en: "Today" },
  delivered: { de: "Zugestellt", en: "Delivered" },
  delayed: { de: "Verspätet", en: "Delayed" },
  pickup: { de: "Abholbereit", en: "Pickup" },
};

export const SORT_LABELS: Record<SortKey, { de: string; en: string }> = {
  expected: { de: "Lieferdatum", en: "Delivery date" },
  carrier: { de: "Paketdienst", en: "Carrier" },
  merchant: { de: "Händler", en: "Merchant" },
  status: { de: "Status", en: "Status" },
};

export const STATUS_LABELS: Record<
  PackageStatus,
  { de: string; en: string }
> = {
  ordered: { de: "Bestellt", en: "Ordered" },
  shipped: { de: "Versendet", en: "Shipped" },
  in_transit: { de: "Unterwegs", en: "In transit" },
  out_for_delivery: { de: "In Zustellung", en: "Out for delivery" },
  delivered: { de: "Zugestellt", en: "Delivered" },
  delayed: { de: "Verspätet", en: "Delayed" },
  ready_for_pickup: { de: "Abholbereit", en: "Ready for pickup" },
  returned: { de: "Retourniert", en: "Returned" },
  cancelled: { de: "Storniert", en: "Cancelled" },
  unknown: { de: "Unbekannt", en: "Unknown" },
};
