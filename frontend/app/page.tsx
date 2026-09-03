"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { DistanceSlider } from "@/components/DistanceSlider";
import { ItemCard, ItemRow } from "@/components/ItemCard";
import { MobileTabBar, TopNav } from "@/components/TopNav";
import { Card, Checkbox, Chip, RemovableChip, SectionLabel, Toggle } from "@/components/ui";
import { api } from "@/lib/api";
import { CATEGORY_LABELS, CONDITION_LABELS } from "@/lib/format";
import type { Category, FacetCounts, FeedFilters, ListingCard, Me, SortOrder } from "@/lib/types";

const SORTS: { value: SortOrder; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "closest", label: "Closest first" },
  { value: "price_asc", label: "Price: low to high" },
  { value: "price_desc", label: "Price: high to low" },
  { value: "most_saved", label: "Most saved" },
];

const PAGE_SIZE = 24;

export default function FeedPage() {
  const sentinel = useRef<HTMLDivElement>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [items, setItems] = useState<ListingCard[]>([]);
  const [facets, setFacets] = useState<FacetCounts | null>(null);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [filters, setFilters] = useState<FeedFilters>({ sort: "newest", limit: PAGE_SIZE });

  useEffect(() => {
    api
      .me()
      .then((user) => {
        setMe(user);
        // The saved defaults are where the sliders start, not a lock.
        setFilters((f) => ({
          ...f,
          radius_mi: user.default_radius_mi,
          same_zip: user.default_filter_same_zip,
          same_nationality: user.default_filter_same_nationality,
          same_school: user.default_filter_same_school,
        }));
      })
      .catch(() => setMe(null)); // signed out: no badges, no distance
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [page, counts] = await Promise.all([api.listings(filters), api.facets(filters)]);
      setItems(page.items);
      setTotal(page.total);
      setFacets(counts);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    void load();
  }, [load]);

  /**
   * Load the next page and append it.
   *
   * The API has always returned `next_cursor`; nothing was reading it, so the
   * feed rendered the first 24 of however many the header claimed. Appending
   * rather than replacing is the whole point: filters reset to offset 0, but
   * scrolling adds.
   */
  const loadMore = useCallback(async () => {
    if (loadingMore || items.length >= total) return;
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

  // Auto-load when the sentinel scrolls into view. The button below it stays
  // real and clickable, so this works without an observer too.
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
    setFilters((f) => ({ ...f, ...next, offset: 0 }));
  }

  function toggleCategory(c: Category) {
    const active = filters.category ?? [];
    const next = active.includes(c) ? active.filter((x) => x !== c) : [...active, c];
    patch({ category: next });
    api.logFilter("category", total, c);
  }

  function toggleTrust(key: "same_zip" | "same_nationality" | "same_school", on: boolean) {
    patch({ [key]: on });
    api.logFilter(key, total, String(on));
  }

  const zip = me?.zip_code ?? "10027";

  /**
   * Every filter currently narrowing the feed, as removable chips.
   *
   * The trust toggles load ON from the member's saved profile defaults, so a
   * third of people open a feed that is already narrowed by a control sitting
   * off-screen in the sidebar. The headline count moves, but nothing says why
   * it is small — which reads as an empty marketplace rather than a tight
   * circle. Naming the active filters here is the same honesty the live counts
   * are for (UX_SPEC.md §5.4).
   *
   * Radius is deliberately absent: the headline already states it.
   */
  const activeFilters: { key: string; label: string; clear: () => void }[] = [];
  if (filters.q) {
    activeFilters.push({
      key: "q",
      label: `“${filters.q}”`,
      clear: () => patch({ q: undefined }),
    });
  }
  for (const [key, label] of [
    ["same_zip", "Same ZIP code"],
    ["same_nationality", "Same nationality"],
    ["same_school", "Same college"],
  ] as const) {
    if (filters[key]) {
      activeFilters.push({ key, label, clear: () => toggleTrust(key, false) });
    }
  }
  for (const c of filters.category ?? []) {
    activeFilters.push({
      key: `category:${c}`,
      label: CATEGORY_LABELS[c],
      clear: () => toggleCategory(c),
    });
  }
  for (const cond of filters.condition ?? []) {
    activeFilters.push({
      key: `condition:${cond}`,
      label: CONDITION_LABELS[cond] ?? cond,
      clear: () =>
        patch({ condition: (filters.condition ?? []).filter((x) => x !== cond) }),
    });
  }

  return (
    <>
      <TopNav me={me} query={filters.q ?? ""} onQuery={(q) => patch({ q })} />

      {/* Mobile header */}
      <header className="border-b border-line bg-surface px-4 pb-3 pt-4 md:hidden">
        <h1 className="text-[18px] font-bold tracking-[-0.01em]">{zip}</h1>
        <input
          value={filters.q ?? ""}
          onChange={(e) => patch({ q: e.target.value })}
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
                onClick={() => setFilters({ sort: "newest", limit: 24, radius_mi: me?.default_radius_mi })}
                className="text-[13px] font-semibold text-deep"
              >
                Reset
              </button>
            </div>

            {/* Trust filters. Each one implicitly excludes external listings —
                an aggregated eBay item has no seller to share anything with. */}
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
                  <Toggle on={Boolean(filters[key])} onChange={(v) => toggleTrust(key, v)} />
                </div>
              ))}
            </div>

            <div className="flex flex-col gap-3.5">
              <SectionLabel>CATEGORY</SectionLabel>
              {facets?.categories.map((f) => (
                <label key={f.key} className="flex cursor-pointer items-center gap-2.5">
                  <Checkbox
                    on={(filters.category ?? []).includes(f.key as Category)}
                    onChange={() => toggleCategory(f.key as Category)}
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
                value={filters.radius_mi ?? 2.5}
                count={total}
                steps={facets?.radius_steps}
                onChange={(mi) => patch({ radius_mi: mi })}
              />
            </div>

            <div className="flex flex-col gap-3.5">
              <SectionLabel>CONDITION</SectionLabel>
              {facets?.conditions.map((f) => (
                <label key={f.key} className="flex cursor-pointer items-center gap-2.5">
                  <Checkbox
                    on={(filters.condition ?? []).some((c) => c === f.key)}
                    onChange={() => {
                      const active = filters.condition ?? [];
                      patch({
                        condition: active.some((c) => c === f.key)
                          ? active.filter((c) => c !== f.key)
                          : ([...active, f.key] as FeedFilters["condition"]),
                      });
                    }}
                  />
                  <span className="flex-1 text-[14px] text-ink2">{f.label}</span>
                  <span className="text-[12px] text-ink3">{f.count}</span>
                </label>
              ))}
            </div>
          </Card>
        </aside>

        {/* ---------------- results ---------------- */}
        <section className="flex min-w-0 flex-1 flex-col gap-4">
          <div className="flex items-center gap-3 px-4 pt-4 md:px-0 md:pt-0">
            <div className="flex-1">
              <h2 className="text-[16px] font-semibold text-ink2 md:text-[22px] md:font-bold md:tracking-[-0.02em] md:text-ink">
                {total.toLocaleString()} items within {filters.radius_mi ?? 2.5} miles of {zip}
              </h2>
            </div>
            <select
              value={filters.sort}
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

          {/* What is narrowing the feed right now, and how much of it you are
              actually looking at. Both are easy to lose: the trust toggles can
              arrive already on from the profile, and the grid always starts at
              one page however wide the radius is. */}
          {activeFilters.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 px-4 md:px-0">
              <span className="text-[12.5px] text-ink3">Filtering by</span>
              {activeFilters.map((f) => (
                <RemovableChip key={f.key} label={f.label} onRemove={f.clear} />
              ))}
              <button
                type="button"
                onClick={() =>
                  setFilters({
                    sort: filters.sort,
                    limit: PAGE_SIZE,
                    radius_mi: filters.radius_mi,
                  })
                }
                className="text-[12.5px] font-semibold text-deep underline underline-offset-2"
              >
                Clear all
              </button>
            </div>
          )}

          {!loading && total > 0 && (
            <p className="px-4 text-[12.5px] text-ink3 md:px-0">
              Showing {items.length.toLocaleString()} of {total.toLocaleString()}
              {items.length < total ? " — scroll for more" : ""}
            </p>
          )}

          {/* Category chips — the mobile equivalent of the sidebar list */}
          <div className="flex gap-2 overflow-x-auto px-4 md:hidden">
            {(Object.keys(CATEGORY_LABELS) as Category[]).map((c) => (
              <Chip
                key={c}
                active={(filters.category ?? []).includes(c)}
                onClick={() => toggleCategory(c)}
              >
                {CATEGORY_LABELS[c]}
              </Chip>
            ))}
          </div>

          {loading ? (
            <div className="grid grid-cols-1 gap-5 px-4 md:grid-cols-4 md:px-0">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="h-72 animate-pulse rounded-[14px] bg-muted" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <EmptyState
              radius={filters.radius_mi ?? 2.5}
              onWiden={() => patch({ radius_mi: Math.min(10, (filters.radius_mi ?? 2.5) * 2) })}
            />
          ) : (
            <>
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

              <div ref={sentinel} className="flex flex-col items-center gap-3 py-10">
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
            </>
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
function EmptyState({ radius, onWiden }: { radius: number; onWiden: () => void }) {
  return (
    <Card className="mx-4 flex flex-col items-center gap-3 p-10 text-center md:mx-0">
      <p className="text-[17px] font-bold tracking-[-0.01em]">
        Nothing within {radius} {radius === 1 ? "mile" : "miles"}
      </p>
      <p className="max-w-sm text-[12.5px] leading-[19px] text-ink2">
        Your radius is the binding filter. Widening it is usually all it takes.
      </p>
      <button
        onClick={onWiden}
        className="mt-1 rounded-[11px] bg-deep px-5 py-3 text-[14px] font-semibold text-white"
      >
        Widen to {Math.min(10, radius * 2)} mi
      </button>
    </Card>
  );
}
