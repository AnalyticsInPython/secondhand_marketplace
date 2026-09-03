"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { DistanceSlider } from "@/components/DistanceSlider";
import { ItemCard, ItemRow } from "@/components/ItemCard";
import { MobileTabBar, TopNav } from "@/components/TopNav";
import { Card, Checkbox, Chip, SectionLabel, Toggle } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import { CATEGORY_LABELS } from "@/lib/format";
import type {
  Category,
  Condition,
  FacetCounts,
  FeedFilters,
  ListingCard,
  Me,
  SortOrder,
} from "@/lib/types";

const SORTS: { value: SortOrder; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "closest", label: "Closest first" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "most_saved", label: "Most saved" },
];

const PRICE_PRESETS: { label: string; min?: number; max?: number }[] = [
  { label: "Free", max: 0 },
  { label: "Under $50", max: 4999 },
  { label: "$50–200", min: 5000, max: 20000 },
  { label: "$200+", min: 20001 },
];

/**
 * The feed — UX_SPEC.md §6.3. There is no browsing without an account, so a
 * signed-out visitor is sent to /signin before anything is requested.
 */
export default function FeedPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [items, setItems] = useState<ListingCard[]>([]);
  const [facets, setFacets] = useState<FacetCounts | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState<FeedFilters | null>(null);
  const [query, setQuery] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);
  const sentinel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api
      .me()
      .then((user) => {
        setMe(user);
        // The saved defaults are where the sliders start, not a lock.
        setFilters({
          limit: 24,
          radius_mi: user.default_radius_mi,
          same_zip: user.default_filter_same_zip,
          same_nationality: user.default_filter_same_nationality,
          same_school: user.default_filter_same_school,
        });
      })
      .catch(() => router.replace("/signin"));
  }, [router]);

  const load = useCallback(async () => {
    if (!filters) return;
    setLoading(true);
    try {
      const [page, counts] = await Promise.all([api.listings(filters), api.facets(filters)]);
      setItems(page.items);
      setTotal(page.total);
      setFacets(counts);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) router.replace("/signin");
    } finally {
      setLoading(false);
    }
  }, [filters, router]);

  useEffect(() => {
    void load();
  }, [load]);

  /**
   * Load the next page and append it. Filters reset to the first page, but
   * scrolling adds — with a real button as the trigger so it works without an
   * IntersectionObserver and stays keyboard-reachable.
   */
  const loadMore = useCallback(async () => {
    if (!filters || loadingMore || items.length >= total) return;
    setLoadingMore(true);
    try {
      const page = await api.listings({ ...filters, offset: items.length });
      // Guard against a filter change landing mid-flight and duplicating rows.
      setItems((current) => {
        const seen = new Set(current.map((i) => i.id));
        return [...current, ...page.items.filter((i) => !seen.has(i.id))];
      });
    } finally {
      setLoadingMore(false);
    }
  }, [filters, items.length, total, loadingMore]);

  useEffect(() => {
    const node = sentinel.current;
    if (!node) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) void loadMore();
      },
      { rootMargin: "600px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [loadMore]);

  function patch(next: Partial<FeedFilters>) {
    setFilters((f) => ({ ...(f ?? {}), ...next, offset: 0 }));
  }

  // One request per pause in typing, not one per keystroke.
  useEffect(() => {
    const t = setTimeout(() => {
      const current = filters?.q ?? "";
      if (filters && current !== query) patch({ q: query || undefined });
    }, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query]);

  function toggleCategory(c: Category) {
    const active = filters?.category ?? [];
    const next = active.includes(c) ? active.filter((x) => x !== c) : [...active, c];
    // A subcategory only makes sense under its parent.
    const subcategory = next.includes("furniture") ? filters?.subcategory : undefined;
    patch({ category: next, subcategory });
    api.logFilter("category", total, c);
  }

  function toggleSubcategory(s: string) {
    const active = filters?.subcategory ?? [];
    patch({ subcategory: active.includes(s) ? active.filter((x) => x !== s) : [...active, s] });
    api.logFilter("subcategory", total, s);
  }

  function toggleCondition(c: Condition) {
    const active = filters?.condition ?? [];
    patch({ condition: active.includes(c) ? active.filter((x) => x !== c) : [...active, c] });
    api.logFilter("condition", total, c);
  }

  function toggleTrust(key: "same_zip" | "same_nationality" | "same_school", on: boolean) {
    patch({ [key]: on });
    api.logFilter(key, total, String(on));
  }

  function setPrice(preset: { min?: number; max?: number } | null) {
    patch({ price_min_cents: preset?.min, price_max_cents: preset?.max });
    api.logFilter("price", total, preset ? `${preset.min ?? 0}-${preset.max ?? ""}` : "off");
  }

  const zip = me?.zip_code ?? "";
  const radius = filters?.radius_mi ?? 2.5;
  const sort: SortOrder = filters?.sort ?? (filters?.q ? "closest" : "newest");
  const furnitureOn = (filters?.category ?? []).includes("furniture");
  const priceKey = `${filters?.price_min_cents ?? ""}-${filters?.price_max_cents ?? ""}`;

  return (
    <>
      <TopNav me={me} query={query} onQuery={setQuery} />

      {/* Mobile header */}
      <header className="border-b border-line bg-surface px-4 pb-3 pt-4 md:hidden">
        <h1 className="text-[18px] font-bold tracking-[-0.01em]">{zip}</h1>
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search desks, textbooks, coats…"
          className="mt-3 w-full rounded-[12px] bg-muted px-3.5 py-3 text-[14.5px] outline-none placeholder:text-ink3"
        />
      </header>

      <main className="mx-auto flex max-w-[1360px] gap-7 px-0 py-0 md:px-10 md:py-7">
        {/* ---------------- filter sidebar (desktop) ---------------- */}
        <aside className="hidden w-[288px] shrink-0 md:block">
          <Card className="flex flex-col gap-6 p-5">
            <div className="flex items-center">
              <h2 className="flex-1 text-[18px] font-bold">Filters</h2>
              <button
                onClick={() => {
                  setQuery("");
                  setFilters({ limit: 24, radius_mi: me?.default_radius_mi });
                }}
                className="text-[13px] font-semibold text-deep"
              >
                Reset
              </button>
            </div>

            <div className="flex flex-col gap-3.5 rounded-[12px] border border-light bg-tint p-4">
              <div>
                <p className="text-[14px] font-bold text-deep">Trust filters</p>
                <p className="text-[12px] leading-[17px] text-ink2">
                  Only show sellers you overlap with.
                </p>
              </div>
              {(
                [
                  ["same_zip", "Same ZIP code", facets?.same_zip],
                  ["same_nationality", "Same nationality", facets?.same_nationality],
                  ["same_school", "Same college", facets?.same_school],
                ] as const
              ).map(([key, label, count]) => (
                <div key={key} className="flex items-center gap-2.5">
                  <div className="flex-1">
                    <p className="text-[13.5px] font-semibold text-ink">{label}</p>
                    <p className="text-[11px] text-ink2">{count ?? 0} items</p>
                  </div>
                  <Toggle on={Boolean(filters?.[key])} onChange={(v) => toggleTrust(key, v)} />
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-3.5">
              <SectionLabel>CATEGORY</SectionLabel>
              {facets?.categories.map((f) => (
                <div key={f.key} className="flex flex-col gap-2.5">
                  <label className="flex cursor-pointer items-center gap-2.5">
                    <Checkbox
                      on={(filters?.category ?? []).includes(f.key as Category)}
                      onChange={() => toggleCategory(f.key as Category)}
                    />
                    <span className="flex-1 text-[14px] text-ink2">{f.label}</span>
                    <span className="text-[12px] text-ink3">{f.count}</span>
                  </label>
                  {f.key === "furniture" && furnitureOn && (
                    <div className="ml-7 flex flex-col gap-2.5 border-l border-line pl-3">
                      {facets.subcategories.map((s) => (
                        <label key={s.key} className="flex cursor-pointer items-center gap-2.5">
                          <Checkbox
                            on={(filters?.subcategory ?? []).includes(s.key)}
                            onChange={() => toggleSubcategory(s.key)}
                          />
                          <span className="flex-1 text-[13px] text-ink2">{s.label}</span>
                          <span className="text-[11.5px] text-ink3">{s.count}</span>
                        </label>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-3">
              <SectionLabel>PRICE</SectionLabel>
              <div className="flex flex-wrap gap-1.5">
                {PRICE_PRESETS.map((p) => {
                  const key = `${p.min ?? ""}-${p.max ?? ""}`;
                  const active = key === priceKey;
                  return (
                    <button
                      key={p.label}
                      type="button"
                      onClick={() => setPrice(active ? null : p)}
                      className={`rounded-full px-2.5 py-1.5 text-[11.5px] font-semibold transition-colors ${
                        active ? "bg-deep text-white" : "bg-muted text-ink2 hover:bg-line"
                      }`}
                    >
                      {p.label}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex flex-col gap-3.5">
              <SectionLabel>CONDITION</SectionLabel>
              {facets?.conditions.map((f) => (
                <label key={f.key} className="flex cursor-pointer items-center gap-2.5">
                  <Checkbox
                    on={(filters?.condition ?? []).includes(f.key as Condition)}
                    onChange={() => toggleCondition(f.key as Condition)}
                  />
                  <span className="flex-1 text-[14px] text-ink2">{f.label}</span>
                  <span className="text-[12px] text-ink3">{f.count}</span>
                </label>
              ))}
            </div>

            <div className="flex flex-col gap-3.5">
              <SectionLabel>DISTANCE FROM {zip}</SectionLabel>
              <DistanceSlider
                zip={zip}
                value={radius}
                count={total}
                steps={facets?.radius_steps}
                onChange={(mi) => patch({ radius_mi: mi })}
              />
            </div>
          </Card>
        </aside>

        {/* ---------------- results ---------------- */}
        <section className="flex min-w-0 flex-1 flex-col gap-4">
          <div className="flex items-center gap-3 px-4 pt-4 md:px-0 md:pt-0">
            <div className="flex-1">
              <h2 className="text-[16px] font-semibold text-ink2 md:text-[22px] md:font-bold md:tracking-[-0.02em] md:text-ink">
                {loading && !facets
                  ? "Loading your feed…"
                  : `${total.toLocaleString()} ${total === 1 ? "item" : "items"} within ${radius} ${radius === 1 ? "mile" : "miles"} of ${zip}`}
              </h2>
              {filters?.q && (
                <p className="text-[12.5px] text-ink2">Matching “{filters.q}” · closest first unless you change the sort</p>
              )}
            </div>
            <select
              value={sort}
              onChange={(e) => patch({ sort: e.target.value as SortOrder })}
              className="rounded-[9px] border border-line-strong bg-surface px-3 py-2 text-[13.5px] font-medium outline-none"
            >
              {SORTS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
          </div>

          {/* Category chips — the mobile equivalent of the sidebar list */}
          <div className="flex gap-2 overflow-x-auto px-4 md:hidden">
            {(Object.keys(CATEGORY_LABELS) as Category[]).map((c) => (
              <Chip
                key={c}
                active={(filters?.category ?? []).includes(c)}
                onClick={() => toggleCategory(c)}
              >
                {CATEGORY_LABELS[c]}
              </Chip>
            ))}
          </div>

          {loading && items.length === 0 ? (
            <div className="grid grid-cols-1 gap-5 px-4 md:grid-cols-4 md:px-0">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-72 animate-pulse rounded-[14px] bg-muted" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              radius={radius}
              query={filters?.q}
              onWiden={() => patch({ radius_mi: Math.min(10, radius * 2) })}
              onClearQuery={() => setQuery("")}
            />
          ) : (
            <div className={loading ? "opacity-60 transition-opacity" : "transition-opacity"}>
              <div className="hidden grid-cols-2 gap-5 lg:grid-cols-4 md:grid">
                {items.map((item) => (
                  <ItemCard key={item.id} item={item} />
                ))}
              </div>
              <div className="bg-surface md:hidden">
                {items.map((item) => (
                  <ItemRow key={item.id} item={item} />
                ))}
              </div>
            </div>
          )}

          {items.length > 0 && (
            <div ref={sentinel} className="flex flex-col items-center gap-3 px-4 py-10 md:px-0">
              {items.length < total ? (
                <>
                  <button
                    type="button"
                    onClick={() => void loadMore()}
                    disabled={loadingMore}
                    className="rounded-[10px] border border-line bg-surface px-5 py-3 text-[14px] font-semibold text-deep disabled:opacity-60"
                  >
                    {loadingMore ? "Loading…" : "Load more"}
                  </button>
                  <p className="text-[12.5px] text-ink3">
                    Showing {items.length} of {total}
                  </p>
                </>
              ) : (
                <p className="text-[12.5px] text-ink3">
                  That is all {total} {total === 1 ? "item" : "items"}.
                </p>
              )}
            </div>
          )}
        </section>
      </main>

      <MobileTabBar />
    </>
  );
}

/**
 * Never just "nothing found". Name the filter that is responsible and offer the
 * one-tap loosening that would fix it (UX_SPEC.md state C4).
 */
function EmptyState({
  radius,
  query,
  onWiden,
  onClearQuery,
}: {
  radius: number;
  query?: string;
  onWiden: () => void;
  onClearQuery: () => void;
}) {
  return (
    <Card className="mx-4 flex flex-col items-center gap-3 p-10 text-center md:mx-0">
      <p className="text-[17px] font-bold tracking-[-0.01em]">
        {query ? `Nothing matches “${query}” within ${radius} mi` : `Nothing within ${radius} ${radius === 1 ? "mile" : "miles"}`}
      </p>
      <p className="max-w-sm text-[12.5px] leading-[19px] text-ink2">
        {radius < 10
          ? "Your radius is the binding filter. Widening it is usually all it takes."
          : "Try fewer filters, or check back after the weekend — most items are posted then."}
      </p>
      <div className="mt-1 flex gap-2">
        {radius < 10 && (
          <button
            onClick={onWiden}
            className="rounded-[11px] bg-deep px-5 py-3 text-[14px] font-semibold text-white"
          >
            Widen to {Math.min(10, radius * 2)} mi
          </button>
        )}
        {query && (
          <button
            onClick={onClearQuery}
            className="rounded-[11px] border border-line-strong bg-surface px-5 py-3 text-[14px] font-semibold text-ink"
          >
            Clear search
          </button>
        )}
      </div>
    </Card>
  );
}
