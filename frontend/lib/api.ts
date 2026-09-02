/**
 * The one place that talks to the API.
 *
 * `credentials: "include"` on every call, because auth is a session cookie —
 * there is no token to attach and no password to store.
 */

import type {
  FacetCounts,
  FeedFilters,
  ListingDetail,
  ListingPage,
  Me,
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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(init.headers ?? {}) },
    ...init,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new ApiError(res.status, body.detail ?? res.statusText);
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

  // ---- listings
  listings: (filters: FeedFilters) => request<ListingPage>(`/listings${qs(filters)}`),
  facets: (filters: FeedFilters) => request<FacetCounts>(`/listings/facets${qs(filters)}`),
  listing: (id: string) => request<ListingDetail>(`/listings/${id}`),
  createListing: (body: Record<string, unknown>) =>
    request<ListingDetail>("/listings", { method: "POST", body: JSON.stringify(body) }),
  markSold: (id: string) => request<void>(`/listings/${id}/sold`, { method: "POST" }),
  save: (id: string) => request<void>(`/listings/${id}/save`, { method: "POST" }),
  unsave: (id: string) => request<void>(`/listings/${id}/save`, { method: "DELETE" }),

  /**
   * The only call that returns a contact detail, and only because the buyer
   * just tapped the button. Nothing else in the API carries an address or a
   * number (UX_SPEC.md §5.1).
   */
  enquire: (id: string, channel: "email" | "sms") =>
    request<{ channel: string; address?: string; phone?: string }>(`/listings/${id}/enquiry`, {
      method: "POST",
      body: JSON.stringify({ channel }),
    }),

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
  enums: () => request<Record<string, unknown>>("/reference/enums"),
};
