/**
 * Mirrors backend/app/schemas.py. Keep the two in step — the enum *values* are
 * contractual (UX_SPEC.md §4.5).
 */

export type Category =
  | "furniture"
  | "textbooks"
  | "electronics"
  | "kitchen_home"
  | "clothing"
  | "bikes_transport"
  | "sports"
  | "free_stuff";

export type Condition = "new" | "like_new" | "used_good" | "used_fair";
export type Grade = "undergraduate" | "graduate" | "faculty_staff";
export type ListingStatus = "draft" | "active" | "reserved" | "sold" | "delisted";
export type SortOrder = "newest" | "closest" | "price_asc" | "price_desc" | "most_saved";

/** Computed per (viewer, listing). An attribute you do not share is absent. */
export type Badge = "SAME ZIP" | "SAME COUNTRY" | "SAME SCHOOL";

export interface SellerPublic {
  username: string;
  display_name: string | null;
  is_verified: boolean;
  member_since: string;
  badges: Badge[];
  /** Drives the two contact shapes. The number itself never reaches the page. */
  can_receive_sms: boolean;
}

export interface Photo {
  url: string;
  width: number | null;
  height: number | null;
}

export interface ListingCard {
  id: string;
  title: string;
  price_cents: number;
  is_free: boolean;
  condition: Condition;
  category: Category;
  subcategory: string | null;
  zip_code: string;
  neighbourhood: string | null;
  /** Already measured from the viewer's ZIP. */
  distance_mi: number | null;
  posted_at: string;
  status: ListingStatus;
  cover_photo_url: string | null;
  photo_count: number;
  badges: Badge[];
}

export interface ListingDetail extends ListingCard {
  description: string | null;
  is_negotiable: boolean;
  photos: Photo[];
  photo_urls: string[];
  view_count: number;
  save_count: number;
  enquiry_count: number;
  sold_at: string | null;
  seller: SellerPublic | null;
  is_saved: boolean;
  is_owner: boolean;
}

export interface ListingPage {
  items: ListingCard[];
  total: number;
  next_cursor: string | null;
}

export interface FacetCount {
  key: string;
  label: string;
  count: number;
}

export interface FacetCounts {
  total: number;
  categories: FacetCount[];
  subcategories: FacetCount[];
  conditions: FacetCount[];
  same_zip: number;
  same_nationality: number;
  same_school: number;
  radius_steps: FacetCount[];
}

export interface Me {
  id: string;
  email: string;
  username: string;
  display_name: string | null;
  phone: string | null;
  phone_contact_enabled: boolean;
  nationality: string;
  school: string;
  grade: Grade;
  zip_code: string;
  default_radius_mi: number;
  default_filter_same_zip: boolean;
  default_filter_same_nationality: boolean;
  default_filter_same_school: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface ZipResult {
  zip_code: string;
  neighbourhood: string;
  borough: string;
  miles_away: number;
  miles_from_campus: number | null;
}

export interface Country {
  code: string;
  name: string;
  pinned: boolean;
}

export interface EmailCheck {
  email: string;
  allowed: boolean;
  reason: string | null;
  suggested_school: string | null;
}

export interface Option {
  value: string;
  label: string;
}

/** GET /reference/enums — one call at boot fills every picker. */
export interface EnumsRef {
  allowed_email_domains: string[];
  categories: (Option & { subcategories: Option[] })[];
  conditions: Option[];
  grades: Option[];
  schools: { undergraduate: Option[]; graduate: Option[] };
  listing_statuses: Option[];
  radius_steps_mi: number[];
  photos: { max_per_listing: number; max_bytes: number };
}

/** The query string of GET /listings. */
export interface FeedFilters {
  q?: string;
  category?: Category[];
  subcategory?: string[];
  condition?: Condition[];
  price_min_cents?: number;
  price_max_cents?: number;
  radius_mi?: number;
  same_zip?: boolean;
  same_nationality?: boolean;
  same_school?: boolean;
  sort?: SortOrder;
  limit?: number;
  offset?: number;
}

/**
 * One row of the inbox. There is no in-app chat (UX_SPEC §1), so this records a
 * contact made rather than a conversation: which listing, which channel, when.
 */
export interface EnquiryRow {
  id: string;
  channel: "email" | "sms";
  created_at: string;
  listing: ListingCard;
  seller_username: string | null;
}

export interface ListingInput {
  title: string;
  description: string | null;
  category: Category;
  subcategory: string | null;
  condition: Condition;
  price_cents: number;
  is_free: boolean;
  is_negotiable: boolean;
  zip_code: string;
  photo_urls: string[];
}

/** Someone who contacted the seller — the candidates when marking an item sold. */
export interface Enquirer {
  id: string;
  username: string;
  display_name: string | null;
  channel: "email" | "sms";
  enquired_at: string;
}

/** Everything the dashboard draws. Aggregated in Python — see routers/insights.py. */
export interface Insights {
  overview: {
    members: number; listings: number; sold: number; active: number;
    views: number; saves: number; enquiries: number; sessions: number; searches: number;
  };
  activity: { week: string; posted: number; sold: number; per_seller: number }[];
  funnel: { stage: string; count: number; share_of_views: number; conversion: number | null }[];
  sales_by_distance: { band: string; sales: number }[];
  searches: {
    total: number; empty: number; empty_share: number;
    top: { query: string; searches: number; empty: number; clicks: number }[];
    empty_top: { query: string; searches: number }[];
  };
  price_by_condition: {
    condition: string; listings: number; p25: number; median: number; p75: number;
  }[];
  inventory_age: {
    buckets: { band: string; listings: number }[];
    total: number;
    stale_share: number;
  };
  days_to_sell: {
    category: string; listings: number; sold: number;
    sell_through: number; median_days: number | null;
  }[];
  categories: {
    category: string; listings: number; sold: number;
    sell_through: number; median_price: number;
  }[];
  badges: {
    arms: { arm: string; impressions: number; contacts: number; rate: number }[];
    planted: boolean;
  };
  trust_curve: {
    steps: {
      label: string; depth: number; median: number; p25: number; p75: number;
      share_of_all: number; below_threshold: number;
    }[];
    sample: number;
    total: number;
    threshold: number;
  };
  overlap: {
    levels: { shared: number; impressions: number; contacts: number; rate: number }[];
  };
  buyer_vs_viewer: {
    listings: number;
    buyer_mean: number;
    viewer_mean: number;
    lift: number | null;
    by_attribute: { attribute: string; buyers: number; viewers: number }[];
  };
}

export type TopLinePeriod = "day" | "week" | "month";

/** One time bucket. Every count is at its own event time — a listing counts in
 *  the bucket it was posted, a sale in the bucket it was sold. */
export interface TopLineBucket {
  start: string;
  listed: number;
  sellers: number;
  sold: number;
  gmv_cents: number;
  buyers: number;
  new_members: number;
  views: number;
  active_members: number;
  saves: number;
  contacts: number;
  searches: number;
  sell_through: number;
  contact_rate: number;
}

export interface TopLine {
  period: TopLinePeriod;
  buckets: TopLineBucket[];
  current: TopLineBucket;
  previous: TopLineBucket;
  /** Percent change against the previous complete bucket; null when it was zero. */
  change: Partial<Record<keyof TopLineBucket, number | null>>;
}
