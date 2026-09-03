/**
 * The one place that talks to the API.
 *
 * `credentials: "include"` on every call, because auth is a session cookie —
 * there is no token to attach and no password to store.
 */

import type {
  Country,
  EmailCheck,
  EnquiryRow,
  EnumsRef,
  FacetCounts,
  FeedFilters,
  ListingDetail,
  ListingInput,
  ListingPage,
  ListingStatus,
  Me,
  Photo,
  ZipResult,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

/**
 * Turn a FastAPI error body into something a person can read.
 *
 * A raised HTTPException gives `detail` as a string, but a Pydantic validation
 * failure gives an array of objects, which stringified to "[object Object]".
 */
function detailMessage(body: unknown, fallback: string): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((d) => (typeof d === "string" ? d : (d as { msg?: string })?.msg))
      .filter(Boolean)
      // Pydantic prefixes its own "Value error, "; the rest is our copy.
      .map((m) => String(m).replace(/^Value error,\s*/, ""));
    if (messages.length) return messages.join(" ");
  }
  return fallback;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isForm = init.body instanceof FormData;
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    ...init,
    headers: {
      ...(isForm ? {} : { "Content-Type": "application/json" }),
      ...(init.headers ?? {}),
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, detailMessage(body, res.statusText));
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

function qs(filters: FeedFilters): string {
  const p = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null || value === "" || value === false) continue;
    if (Array.isArray(value)) value.forEach((v) => p.append(key, String(v)));
    else p.set(key, String(value));
  }
  const s = p.toString();
  return s ? `?${s}` : "";
}

export const api = {
  // ---- auth
  emailCheck: (email: string) =>
    request<EmailCheck>(`/auth/email-check?email=${encodeURIComponent(email)}`),

  signup: (body: Record<string, unknown>) =>
    request<{ sent: boolean; dev_link: string | null }>("/auth/signup", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  requestLink: (email: string) =>
    request<{ sent: boolean; resend_available_in_seconds: number; dev_link: string | null }>(
      "/auth/request-link",
      { method: "POST", body: JSON.stringify({ email }) },
    ),

  verify: (token: string) =>
    request<Me>(`/auth/verify?token=${encodeURIComponent(token)}`, { method: "POST" }),

  signout: () => request<void>("/auth/signout", { method: "POST" }),

  usernameAvailable: (username: string) =>
    request<{ username: string; available: boolean; suggestions: string[] }>(
      `/auth/username-available?username=${encodeURIComponent(username)}`,
    ),

  // ---- profile
  me: () => request<Me>("/me"),
  updateMe: (body: Partial<Me>) =>
    request<Me>("/me", { method: "PATCH", body: JSON.stringify(body) }),
  deactivate: () => request<void>("/me/deactivate", { method: "POST" }),

  // ---- the avatar menu's three collections
  myListings: (offset = 0) => request<ListingPage>(`/me/listings?offset=${offset}`),
  mySaves: (offset = 0) => request<ListingPage>(`/me/saves?offset=${offset}`),
  myEnquiries: () => request<EnquiryRow[]>("/me/enquiries"),

  // ---- listings
  listings: (filters: FeedFilters) => request<ListingPage>(`/listings${qs(filters)}`),
  facets: (filters: FeedFilters) => request<FacetCounts>(`/listings/facets${qs(filters)}`),
  listing: (id: string) => request<ListingDetail>(`/listings/${id}`),
  createListing: (body: ListingInput) =>
    request<ListingDetail>("/listings", { method: "POST", body: JSON.stringify(body) }),
  updateListing: (id: string, body: Partial<ListingInput> & { status?: ListingStatus }) =>
    request<ListingDetail>(`/listings/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  markSold: (id: string) => request<void>(`/listings/${id}/sold`, { method: "POST" }),
  save: (id: string) => request<void>(`/listings/${id}/save`, { method: "POST" }),
  unsave: (id: string) => request<void>(`/listings/${id}/save`, { method: "DELETE" }),

  /**
   * The browser never writes to storage directly: the API resizes, re-encodes
   * and strips metadata before anything is kept (UX_SPEC.md §4.3).
   */
  uploadPhoto: (file: File) => {
    const form = new FormData();
    form.append("file", file, file.name);
    return request<Photo>("/photos", { method: "POST", body: form });
  },

  /**
   * The only call that returns a contact detail, and only because the buyer
   * just tapped the button. Nothing else in the API carries an address or a
   * number (UX_SPEC.md §5.1).
   */
  enquire: (id: string, channel: "email" | "sms") =>
    request<{ channel: string; address?: string | null; phone?: string | null }>(
      `/listings/${id}/enquiry`,
      { method: "POST", body: JSON.stringify({ channel }) },
    ),

  /**
   * Fire on every toggle and every slider release. This is the table that
   * answers "which of the filters is doing the work" and it cannot be
   * reconstructed later, so do not batch it away.
   */
  logFilter: (filterKey: string, resultCount: number, value?: string) =>
    request<void>(
      `/listings/events/filter?filter_key=${filterKey}&result_count=${resultCount}` +
        (value ? `&value=${encodeURIComponent(value)}` : ""),
      { method: "POST" },
    ).catch(() => {}), // analytics must never break the UI

  // ---- reference
  zips: (q: string) => request<ZipResult[]>(`/zips?q=${encodeURIComponent(q)}`),
  enums: () => request<EnumsRef>("/reference/enums"),
  countries: () => request<Country[]>("/reference/countries"),
};
