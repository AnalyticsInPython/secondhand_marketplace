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
export type ListingStatus = "draft" | "active" | "reserved" | "sold";
export type Source = "internal" | "ebay" | "facebook" | "karrot";
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

export interface ListingCard {
  id: string;
  title: string;
  price_cents: number;
  is_free: boolean;
  condition: Condition;
  category: Category;
  subcategory: string | null;
  zip_code: string;
  /** Already measured from the viewer's ZIP. Null when signed out. */
  distance_mi: number | null;
  posted_at: string;
  status: ListingStatus;
  cover_photo_url: string | null;
  badges: Badge[];
  is_external: boolean;
  source: Source;
  source_label: string;
}

export interface ListingDetail extends ListingCard {
  description: string | null;
  is_negotiable: boolean;
  photo_urls: string[];
  view_count: number;
  save_count: number;
  enquiry_count: number;
  external_url: string | null;
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

/** The query string of GET /listings. */
export interface FeedFilters {
  q?: string;
  category?: Category[];
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
