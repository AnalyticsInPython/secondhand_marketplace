"use client";

import { useEffect, useState } from "react";

import { MobileTabBar, TopNav } from "@/components/TopNav";
import { Card, SectionLabel } from "@/components/ui";
import { api } from "@/lib/api";
import type { Insights, Me, TopLine, TopLinePeriod } from "@/lib/types";

/**
 * Dashboard — UX_SPEC has no screen for this; it exists for the coursework's
 * data-analysis component.
 *
 * Every number here is computed in Python (`backend/app/routers/insights.py`)
 * with pandas and arrives as plain values. This file draws; it does not
 * analyse. Charts are hand-drawn SVG rather than a charting library, so the
 * project gains no dependency for six charts.
 *
 * On reading these figures: several of the effects visible here were planted in
 * the seed data, and which ones is listed in docs/data_visualization_spec.md §6.
 */
export default function InsightsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [data, setData] = useState<Insights | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [period, setPeriod] = useState<TopLinePeriod>("week");
  const [top, setTop] = useState<TopLine | null>(null);

  useEffect(() => {
    api.me().then(setMe).catch(() => setMe(null));
    api
      .insights()
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load"));
  }, []);

  // Its own fetch, so changing the granularity redraws one section rather than
  // reloading six panels that did not change.
  useEffect(() => {
    api.topline(period).then(setTop).catch(() => setTop(null));
  }, [period]);

  return (
    <>
      <TopNav me={me} />
      <main className="mx-auto max-w-[1360px] px-4 py-7 pb-24 md:px-10 md:pb-10">
        <header className="mb-7 flex flex-col gap-1.5">
          <h1 className="text-[26px] font-bold tracking-[-0.02em] md:text-[32px]">Dashboard</h1>
          <p className="max-w-[70ch] text-[14.5px] leading-[23px] text-ink2">
            What is on the marketplace and what people do with it. Every figure is
            aggregated in Python from the event tables — impressions, saves, contacts,
            searches and completed sales.
          </p>
        </header>

        {error && <p className="text-[14px] text-danger">{error}</p>}
        {!data && !error && <p className="py-20 text-center text-ink2">Loading…</p>}

        {data && <Provenance data={data} />}

        <TopLineSection top={top} period={period} onPeriod={setPeriod} />

        {data && (
          <div className="mt-6 flex flex-col gap-6">
            <Divider title="What's listed" blurb="The inventory itself — what is for sale, at what price, and how fresh it is." />
            <Categories data={data} />
            <div className="grid gap-6 lg:grid-cols-2">
              <PriceByCondition data={data} />
              <InventoryAge data={data} />
            </div>

            <Divider
              title="What people look for"
              blurb="Search is the one place people say what they want in their own words. How often we fail to answer is the useful number here."
            />
            <div className="grid gap-6 lg:grid-cols-2">
              <Searches data={data} />
              <EmptySearches data={data} />
            </div>

            <Divider title="What happens" blurb="Where the two meet: how far a listing gets, and how long it takes." />
            <div className="grid gap-6 lg:grid-cols-2">
              <Funnel data={data} />
              <DaysToSell data={data} />
            </div>
            <TrustCurve data={data} />

            {/* --- the dividing line: operator numbers above, the product's own
                    assumptions below. Each panel below states a claim and shows
                    what actually happened. --- */}
            <div className="mt-6 flex flex-col gap-2 border-t-2 border-ink pt-7">
              <h2 className="text-[24px] font-bold tracking-[-0.02em]">
                Does the idea hold up?
              </h2>
              <p className="max-w-[70ch] text-[14px] leading-[22px] text-ink2">
                Columbia Market is built on a bet: that shared affiliation — the same
                ZIP, the same country, the same school — does the job that ratings and
                escrow do elsewhere. Each panel below is one thing we assumed, and what
                the data actually shows.
              </p>
            </div>

            <Claim
              heading="People trade with people near them"
              assumption="The whole product is built on ZIP-code distance, so proximity had better matter."
            >
              <Distance data={data} />
            </Claim>

            <Claim
              heading="Having something in common makes people reach out"
              assumption="This is the whole bet: that shared affiliation does the job ratings and escrow do elsewhere. If it holds, people should contact sellers they overlap with more often — and the ones who overlap most should be the ones who end up buying."
            >
              <div className="grid gap-6 lg:grid-cols-2">
                <Overlap data={data} />
                <BuyerVsViewer data={data} />
              </div>
            </Claim>
          </div>
        )}
      </main>
      <MobileTabBar />
    </>
  );
}

/* ---------------------------------------------------------------- top line */

const PERIODS: { value: TopLinePeriod; label: string }[] = [
  { value: "day", label: "Day" },
  { value: "week", label: "Week" },
  { value: "month", label: "Month" },
];

/** Which metrics get a headline tile, and how each is formatted. */
const HEADLINES: {
  key: keyof TopLine["current"];
  label: string;
  format?: (v: number) => string;
}[] = [
  { key: "listed", label: "Items listed" },
  { key: "sold", label: "Items sold" },
  { key: "gmv_cents", label: "Value sold", format: (v) => `$${Math.round(v / 100).toLocaleString()}` },
  { key: "sell_through", label: "Sell-through", format: (v) => `${v}%` },
  { key: "new_members", label: "New members" },
  { key: "active_members", label: "Active members" },
  { key: "contacts", label: "Contacts" },
  { key: "searches", label: "Searches" },
];

function TopLineSection({
  top,
  period,
  onPeriod,
}: {
  top: TopLine | null;
  period: TopLinePeriod;
  onPeriod: (p: TopLinePeriod) => void;
}) {
  const noun = period === "day" ? "day" : period === "week" ? "week" : "month";

  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <SectionLabel>TOP LINE</SectionLabel>
          <p className="mt-1 text-[12.5px] text-ink2">
            {top?.current?.start
              ? `Last complete ${noun}, beginning ${top.current.start}. The change is against the ${noun} before it; the ${noun} in progress is left out, because a half-finished one always looks like a collapse.`
              : `Counts per ${noun}.`}
          </p>
        </div>

        <div className="flex gap-1 rounded-[10px] border border-line bg-muted p-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              type="button"
              onClick={() => onPeriod(p.value)}
              aria-pressed={period === p.value}
              className={`rounded-[7px] px-3.5 py-1.5 text-[13px] font-semibold ${
                period === p.value ? "bg-surface text-deep shadow-sm" : "text-ink2"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {!top ? (
        <div className="rounded-[14px] border border-line bg-surface px-6 py-12 text-center text-ink2">
          Loading…
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-px overflow-hidden rounded-[14px] border border-line bg-line md:grid-cols-4">
            {HEADLINES.map(({ key, label, format }) => {
              const value = (top.current?.[key] as number) ?? 0;
              const delta = top.change?.[key];
              return (
                <div key={key} className="bg-surface px-4 py-4">
                  <p className="text-[11px] font-semibold uppercase tracking-[0.07em] text-ink2">
                    {label}
                  </p>
                  <p className="mt-1 text-[24px] font-bold tracking-[-0.02em] tabular-nums text-ink">
                    {format ? format(value) : value.toLocaleString()}
                  </p>
                  <Delta value={delta} />
                </div>
              );
            })}
          </div>

          <Card className="flex flex-col gap-4 p-6">
            <div>
              <h2 className="text-[17px] font-bold">Listed and sold, by {noun}</h2>
              <p className="text-[12.5px] text-ink2">
                A listing counts in the {noun} it was posted; a sale in the {noun} it sold.
              </p>
            </div>
            <TopLineChart buckets={top.buckets} />
            <div className="flex gap-4 text-[12px] text-ink2">
              <Key colour="var(--color-deep)" label="Listed" />
              <Key colour="var(--color-ok)" label="Sold" />
            </div>
          </Card>
        </>
      )}
    </section>
  );
}

function Delta({ value }: { value: number | null | undefined }) {
  if (value === null || value === undefined) {
    return <p className="mt-0.5 text-[12px] text-ink3">no prior {"\u2014"}</p>;
  }
  const up = value >= 0;
  return (
    <p className={`mt-0.5 text-[12px] font-semibold tabular-nums ${up ? "text-ok" : "text-danger"}`}>
      {up ? "▲" : "▼"} {Math.abs(value)}%
    </p>
  );
}

/** Grouped bars: listed and sold side by side per bucket. */
function TopLineChart({ buckets }: { buckets: TopLine["buckets"] }) {
  const w = 900;
  const h = 220;
  const pad = { l: 38, r: 8, t: 10, b: 26 };
  const max = Math.max(1, ...buckets.map((b) => Math.max(b.listed, b.sold)));
  const inner = w - pad.l - pad.r;
  const slot = inner / Math.max(buckets.length, 1);
  const bar = Math.max(Math.min(slot / 2 - 1, 14), 1);
  const y = (v: number) => pad.t + (1 - v / max) * (h - pad.t - pad.b);

  return (
    <div className="overflow-x-auto">
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full min-w-[520px]" role="img"
           aria-label="Items listed and sold per period">
        {[0, 0.5, 1].map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={w - pad.r} y1={y(max * t)} y2={y(max * t)}
                  stroke="var(--color-line)" strokeWidth="1" />
            <text x={pad.l - 6} y={y(max * t) + 4} textAnchor="end" fontSize="10"
                  fill="var(--color-ink3)">
              {Math.round(max * t)}
            </text>
          </g>
        ))}
        {buckets.map((b, i) => {
          const x = pad.l + i * slot;
          return (
            <g key={b.start}>
              <rect x={x} y={y(b.listed)} width={bar} height={Math.max(y(0) - y(b.listed), 0)}
                    fill="var(--color-deep)" rx="1" />
              <rect x={x + bar + 1} y={y(b.sold)} width={bar}
                    height={Math.max(y(0) - y(b.sold), 0)} fill="var(--color-ok)" rx="1" />
              <title>{`${b.start} — ${b.listed} listed, ${b.sold} sold`}</title>
            </g>
          );
        })}
        {buckets.length > 0 && (
          <>
            <text x={pad.l} y={h - 8} fontSize="10" fill="var(--color-ink3)">
              {buckets[0].start}
            </text>
            <text x={w - pad.r} y={h - 8} textAnchor="end" fontSize="10" fill="var(--color-ink3)">
              {buckets[buckets.length - 1].start}
            </text>
          </>
        )}
      </svg>
    </div>
  );
}

/** Where the numbers come from. Counts are what is loaded, not what was generated. */
function Provenance({ data }: { data: Insights }) {
  const o = data.overview;
  const actions = o.views + o.saves + o.enquiries + o.searches;

  const layers: { label: string; value: string; note: string }[] = [
    {
      label: "People",
      value: o.members.toLocaleString(),
      note: "ZIP, country, school and year — the four attributes the product filters on.",
    },
    {
      label: "Listings",
      value: o.listings.toLocaleString(),
      note: "1,500 generated; 150 are external-marketplace rows the schema no longer holds, so 1,350 are live.",
    },
    {
      label: "Actions",
      value: actions.toLocaleString(),
      note: `${o.views.toLocaleString()} views · ${o.saves.toLocaleString()} saves · ${o.enquiries.toLocaleString()} contacts · ${o.searches.toLocaleString()} searches, in ${o.sessions.toLocaleString()} visits.`,
    },
  ];

  return (
    <section className="mb-7 overflow-hidden rounded-[16px] border border-light bg-tint">
      <div className="px-6 pt-5">
        <SectionLabel>SEEDED DATA</SectionLabel>
      </div>
      <div className="mt-3 grid gap-px bg-light md:grid-cols-3">
        {layers.map((layer) => (
          <div key={layer.label} className="bg-tint px-6 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.07em] text-ink2">
              {layer.label}
            </p>
            <p className="mt-0.5 text-[26px] font-bold tracking-[-0.02em] tabular-nums text-deep">
              {layer.value}
            </p>
            <p className="mt-1 text-[12px] leading-[18px] text-ink2">{layer.note}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

/** A section break in the operator half — lighter than the rule before §5. */
function Divider({ title, blurb }: { title: string; blurb: string }) {
  return (
    <div className="mt-2 flex flex-col gap-1 border-t border-line pt-6">
      <h2 className="text-[20px] font-bold tracking-[-0.02em]">{title}</h2>
      <p className="max-w-[70ch] text-[13.5px] leading-[21px] text-ink2">{blurb}</p>
    </div>
  );
}

function PriceByCondition({ data }: { data: Insights }) {
  const rows = data.price_by_condition;
  const max = Math.max(1, ...rows.map((r) => r.p75));
  const label: Record<string, string> = {
    new: "New", like_new: "Like new", used_good: "Used — good", used_fair: "Used — fair",
  };
  const premium =
    rows.length >= 2 && rows[rows.length - 1].median
      ? Math.round((rows[0].median / rows[rows.length - 1].median - 1) * 100)
      : null;

  return (
    <Panel
      title="What things go for, by condition"
      hint="The bar spans the middle half of prices (25th to 75th percentile); the mark is the median."
    >
      <div className="flex flex-col gap-3.5">
        {rows.map((r) => (
          <div key={r.condition} className="flex items-center gap-3">
            <span className="w-[92px] shrink-0 text-[12.5px] text-ink2">
              {label[r.condition] ?? r.condition}
            </span>
            <div className="relative h-5 flex-1 rounded-[5px] bg-muted">
              <div
                className="absolute inset-y-0 rounded-[5px] bg-tint2"
                style={{ left: `${(r.p25 / max) * 100}%`, width: `${((r.p75 - r.p25) / max) * 100}%` }}
              />
              <div
                className="absolute inset-y-0 w-[3px] rounded bg-deep"
                style={{ left: `${(r.median / max) * 100}%` }}
                title={`median $${r.median}`}
              />
            </div>
            <span className="w-14 shrink-0 text-right text-[12.5px] font-semibold tabular-nums">
              ${r.median}
            </span>
          </div>
        ))}
      </div>
      {premium !== null && (
        <p className="text-[12.5px] leading-[19px] text-ink2">
          A new item asks about{" "}
          <span className="font-semibold text-ink">{premium}% more</span> than a
          used—fair one. That gap is the pricing guidance worth putting in the posting
          form.
        </p>
      )}
    </Panel>
  );
}

function InventoryAge({ data }: { data: Insights }) {
  const a = data.inventory_age;
  const max = Math.max(1, ...a.buckets.map((b) => b.listings));
  return (
    <Panel
      title="How old the live inventory is"
      hint={`${a.total} listings are on the feed right now.`}
    >
      <div className="flex flex-col gap-2.5">
        {a.buckets.map((b, i) => (
          <div key={b.band} className="flex items-center gap-3">
            <span className="w-[104px] shrink-0 text-[12.5px] text-ink2">{b.band}</span>
            <div className="h-5 flex-1 overflow-hidden rounded-[5px] bg-muted">
              <div
                className={`h-full rounded-[5px] ${i === a.buckets.length - 1 ? "bg-warn" : "bg-deep"}`}
                style={{ width: `${(b.listings / max) * 100}%` }}
              />
            </div>
            <span className="w-10 shrink-0 text-right text-[12.5px] font-semibold tabular-nums">
              {b.listings}
            </span>
          </div>
        ))}
      </div>
      <p className="rounded-[10px] bg-muted px-4 py-3 text-[12.5px] leading-[19px] text-ink2">
        <span className="font-semibold text-ink">{a.stale_share}% has been up for over
        three months.</span>{" "}
        A feed padded with stale listings looks fuller than it is — those items are
        scrolled past, not considered.
      </p>
    </Panel>
  );
}

function EmptySearches({ data }: { data: Insights }) {
  const rows = data.searches.empty_top;
  const max = Math.max(1, ...rows.map((r) => r.searches));
  return (
    <Panel
      title="Searches that find nothing"
      hint={`${data.searches.empty_share}% of all searches return no results.`}
    >
      <div className="flex flex-col gap-2.5">
        {rows.map((r) => (
          <div key={r.query} className="flex items-center gap-3">
            <span className="w-[110px] shrink-0 truncate text-[12.5px] font-medium">
              {r.query}
            </span>
            <div className="h-4 flex-1 overflow-hidden rounded-[5px] bg-muted">
              <div className="h-full rounded-[5px] bg-warn"
                   style={{ width: `${(r.searches / max) * 100}%` }} />
            </div>
            <span className="w-8 shrink-0 text-right text-[12.5px] font-semibold tabular-nums">
              {r.searches}
            </span>
          </div>
        ))}
      </div>
      <p className="rounded-[10px] bg-muted px-4 py-3 text-[12.5px] leading-[19px] text-ink2">
        <span className="font-semibold text-ink">These are not missing stock.</span> We
        have plenty of textbooks and desk chairs — but their titles say
        &ldquo;Corporate Finance (Berk) 5th ed.&rdquo; and &ldquo;HON Ignition, size
        C&rdquo;, never the words someone would type. Search matches on the title only,
        so the catalogue is there and unreachable.
      </p>
    </Panel>
  );
}

function DaysToSell({ data }: { data: Insights }) {
  const rows = data.days_to_sell.filter((r) => r.median_days !== null);
  const max = Math.max(1, ...rows.map((r) => r.median_days ?? 0));
  return (
    <Panel
      title="How long things take to sell"
      hint="Median days from posting to sale, counting only the items that sold — so read it alongside sell-through, not instead of it."
    >
      <div className="flex flex-col gap-2.5">
        {rows.map((r) => (
          <div key={r.category} className="flex items-center gap-3">
            <span className="w-[112px] shrink-0 text-[12.5px] text-ink2">
              {r.category.replace(/_/g, " ")}
            </span>
            <div className="h-4 flex-1 overflow-hidden rounded-[5px] bg-muted">
              <div className="h-full rounded-[5px] bg-primary"
                   style={{ width: `${((r.median_days ?? 0) / max) * 100}%` }} />
            </div>
            <span className="w-12 shrink-0 text-right text-[12.5px] font-semibold tabular-nums">
              {r.median_days}d
            </span>
            <span className="w-14 shrink-0 text-right text-[11.5px] tabular-nums text-ink3">
              {r.sell_through}% sold
            </span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

/* ------------------------------------------------- "does the idea hold up?" */

/**
 * One assumption, stated as a claim, with the evidence under it.
 *
 * The heading is deliberately a sentence rather than a chart title: "People
 * trade with people near them" invites you to check it, where "Sale distance
 * distribution" reads as homework.
 */
function Claim({
  heading,
  assumption,
  children,
}: {
  heading: string;
  assumption: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3">
      <div>
        <h3 className="text-[18px] font-bold tracking-[-0.01em]">{heading}</h3>
        <p className="max-w-[70ch] text-[13px] leading-[20px] text-ink2">{assumption}</p>
      </div>
      {children}
    </section>
  );
}

function TrustCurve({ data }: { data: Insights }) {
  const t = data.trust_curve;
  const all = t.steps[0]?.median || 1;
  const tightest = t.steps[t.steps.length - 1];

  return (
    <Panel
      title="Why the trust filters default to off"
      hint={`What a typical member would see with each filter on: median across ${t.sample} members, against ${t.total} live listings.`}
    >
      <div className="flex flex-col gap-2.5">
        {t.steps.map((s) => {
          const thin = s.below_threshold >= 50;
          return (
            <div key={s.label} className="flex items-center gap-3">
              <span className="w-[124px] shrink-0 text-[12.5px] text-ink2">{s.label}</span>
              <div className="h-5 flex-1 overflow-hidden rounded-[5px] bg-muted">
                <div
                  className={`h-full rounded-[5px] ${thin ? "bg-warn" : "bg-deep"}`}
                  style={{ width: `${Math.max((s.median / all) * 100, 0.8)}%` }}
                />
              </div>
              <span className="w-12 shrink-0 text-right text-[12.5px] font-semibold tabular-nums">
                {s.median}
              </span>
              <span
                className={`w-[86px] shrink-0 text-right text-[11.5px] tabular-nums ${
                  thin ? "font-semibold text-warn" : "text-ink3"
                }`}
                title={`Share of members whose feed falls below ${t.threshold} items`}
              >
                {s.below_threshold}% under {t.threshold}
              </span>
            </div>
          );
        })}
      </div>

      <p className="rounded-[10px] bg-muted px-4 py-3 text-[12.5px] leading-[19px] text-ink2">
        <span className="font-semibold text-ink">What it shows.</span> One filter is
        survivable — a typical member still sees around {t.steps[1]?.median} items. Two
        is where it breaks: the feed drops to single figures and over half of members
        fall below {t.threshold} items. With all three on, the median member sees{" "}
        {tightest?.median} and {tightest?.below_threshold}% have almost nothing. That is
        the trust-versus-selection trade-off, and it is why the filters default to off.
      </p>
    </Panel>
  );
}

/**
 * The sharper test: among everyone who saw the same listing, did the buyer share
 * more with the seller than the people who did not buy?
 *
 * Holding the listing constant is the point. "Buyers share a lot with sellers"
 * is not evidence — people near a seller see more of their listings to begin
 * with. Comparing within the same choice set cancels that out.
 */
function BuyerVsViewer({ data }: { data: Insights }) {
  const b = data.buyer_vs_viewer;
  const rows = b.by_attribute;
  const max = Math.max(1, ...rows.flatMap((r) => [r.buyers, r.viewers]));
  const meaningful = (b.lift ?? 0) >= 10;

  return (
    <Panel
      title="Did the buyer have more in common than the people who just looked?"
      hint={`Across ${b.listings} sold listings, comparing the buyer against everyone else who viewed the same item — so exposure is held constant.`}
    >
      <div className="flex flex-col gap-3.5">
        {rows.map((r) => (
          <div key={r.attribute} className="flex flex-col gap-1">
            <span className="text-[12.5px] font-medium">{r.attribute}</span>
            <div className="flex items-center gap-2">
              <span className="w-[52px] shrink-0 text-[11px] text-ink2">Buyer</span>
              <div className="h-3.5 flex-1 overflow-hidden rounded-[4px] bg-muted">
                <div className="h-full rounded-[4px] bg-deep"
                     style={{ width: `${(r.buyers / max) * 100}%` }} />
              </div>
              <span className="w-11 shrink-0 text-right text-[11.5px] font-semibold tabular-nums">
                {r.buyers}%
              </span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-[52px] shrink-0 text-[11px] text-ink2">Viewers</span>
              <div className="h-3.5 flex-1 overflow-hidden rounded-[4px] bg-muted">
                <div className="h-full rounded-[4px] bg-line-strong"
                     style={{ width: `${(r.viewers / max) * 100}%` }} />
              </div>
              <span className="w-11 shrink-0 text-right text-[11.5px] tabular-nums text-ink2">
                {r.viewers}%
              </span>
            </div>
          </div>
        ))}
      </div>

      <p className="rounded-[10px] bg-muted px-4 py-3 text-[12.5px] leading-[19px] text-ink2">
        <span className="font-semibold text-ink">
          {meaningful
            ? "Buyers do have more in common than the people who only looked."
            : "Barely any difference."}
        </span>{" "}
        {meaningful
          ? `Buyers shared ${b.buyer_mean} of the three attributes against ${b.viewer_mean} for other viewers.`
          : `Buyers shared ${b.buyer_mean} of the three attributes; everyone else who looked shared ${b.viewer_mean}. Same school is identical, and buyers were slightly less likely to share a country.`}{" "}
        Read alongside the panel to the left, the story is that having something in
        common makes people <em>reach out</em> — but among people considering the same
        item, it does not decide who goes through with it.
      </p>
    </Panel>
  );
}

function Overlap({ data }: { data: Insights }) {
  const levels = data.overlap.levels;
  const max = Math.max(0.01, ...levels.map((l) => l.rate));
  // Small denominators make the last bar jumpy; say so rather than let it mislead.
  const thin = levels.filter((l) => l.impressions < 2000).map((l) => l.shared);

  return (
    <Panel
      title="Contact rate by attributes shared with the seller"
      hint="Every impression, grouped by how many of ZIP, country and school the viewer and seller had in common."
    >
      <div className="flex items-end gap-4">
        {levels.map((l) => (
          <div key={l.shared} className="flex flex-1 flex-col items-center gap-2">
            <span className="text-[13px] font-bold tabular-nums text-deep">{l.rate}%</span>
            <div className="flex h-[120px] w-full items-end">
              <div
                className={`w-full rounded-t-[6px] ${
                  thin.includes(l.shared) ? "bg-line-strong" : "bg-deep"
                }`}
                style={{ height: `${Math.max((l.rate / max) * 100, 3)}%` }}
              />
            </div>
            <span className="text-[12px] font-semibold">{l.shared} shared</span>
            <span className="text-[11px] tabular-nums text-ink3">
              {l.impressions.toLocaleString()} views
            </span>
          </div>
        ))}
      </div>

      {thin.length > 0 && (
        <p className="rounded-[10px] bg-muted px-4 py-3 text-[12.5px] leading-[19px] text-ink2">
          <span className="font-semibold text-ink">Read the last bar carefully.</span>{" "}
          Sharing all three attributes is rare, so that group has only{" "}
          {levels[levels.length - 1]?.impressions.toLocaleString()} impressions behind it —
          a handful of contacts either way swings the percentage. The rise from 0 to 2
          shared attributes rests on far more data and is the part worth quoting.
        </p>
      )}
    </Panel>
  );
}

/* ------------------------------------------------------------------ pieces */

function Panel({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <Card className="flex flex-col gap-4 p-6">
      <div className="flex flex-col gap-1">
        <h2 className="text-[17px] font-bold">{title}</h2>
        {hint && <p className="text-[12.5px] leading-[18px] text-ink2">{hint}</p>}
      </div>
      {children}
    </Card>
  );
}

function Overview({ data }: { data: Insights }) {
  const o = data.overview;
  const tiles: [string, number][] = [
    ["Members", o.members],
    ["Listings", o.listings],
    ["On sale", o.active],
    ["Sold", o.sold],
    ["Views", o.views],
    ["Saves", o.saves],
    ["Contacts", o.enquiries],
    ["Visits", o.sessions],
  ];
  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded-[14px] border border-line bg-line md:grid-cols-4 lg:grid-cols-8">
      {tiles.map(([label, value]) => (
        <div key={label} className="bg-surface px-4 py-4">
          <p className="text-[22px] font-bold tracking-[-0.02em] tabular-nums text-deep">
            {value.toLocaleString()}
          </p>
          <p className="mt-0.5 text-[11px] font-semibold uppercase tracking-[0.07em] text-ink2">
            {label}
          </p>
        </div>
      ))}
    </div>
  );
}

/** Weekly posted vs sold. Two lines, shared scale, no library. */
function Activity({ data }: { data: Insights }) {
  const weeks = data.activity.slice(-52);
  const w = 560;
  const h = 190;
  const pad = { l: 34, r: 8, t: 10, b: 22 };
  const max = Math.max(1, ...weeks.map((d) => Math.max(d.posted, d.sold)));
  const x = (i: number) =>
    pad.l + (i * (w - pad.l - pad.r)) / Math.max(weeks.length - 1, 1);
  const y = (v: number) => pad.t + (1 - v / max) * (h - pad.t - pad.b);
  const path = (key: "posted" | "sold") =>
    weeks.map((d, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`).join(" ");

  return (
    <Panel
      title="Listings posted and sold, weekly"
      hint="The May and August peaks are move-out and arrival. Posting volume also rises as the platform grows, which is why posts per active seller is the honest version of this chart."
    >
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" role="img"
           aria-label="Weekly listings posted and sold over the last year">
        {[0, 0.5, 1].map((t) => (
          <g key={t}>
            <line x1={pad.l} x2={w - pad.r} y1={y(max * t)} y2={y(max * t)}
                  stroke="var(--color-line)" strokeWidth="1" />
            <text x={pad.l - 6} y={y(max * t) + 4} textAnchor="end"
                  fontSize="10" fill="var(--color-ink3)">
              {Math.round(max * t)}
            </text>
          </g>
        ))}
        <path d={path("posted")} fill="none" stroke="var(--color-deep)" strokeWidth="2" />
        <path d={path("sold")} fill="none" stroke="var(--color-ok)" strokeWidth="2" />
        {weeks.length > 0 && (
          <>
            <text x={pad.l} y={h - 6} fontSize="10" fill="var(--color-ink3)">
              {weeks[0].week}
            </text>
            <text x={w - pad.r} y={h - 6} textAnchor="end" fontSize="10" fill="var(--color-ink3)">
              {weeks[weeks.length - 1].week}
            </text>
          </>
        )}
      </svg>
      <div className="flex gap-4 text-[12px] text-ink2">
        <Key colour="var(--color-deep)" label="Posted" />
        <Key colour="var(--color-ok)" label="Sold" />
      </div>
    </Panel>
  );
}

function Key({ colour, label }: { colour: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="h-2 w-4 rounded-full" style={{ background: colour }} />
      {label}
    </span>
  );
}

function Funnel({ data }: { data: Insights }) {
  const max = data.funnel[0]?.count || 1;
  return (
    <Panel
      title="From impression to sale"
      hint="Each bar is a share of all impressions. The percentage on the right is how much of the previous stage survives — that is where the leak is."
    >
      <div className="flex flex-col gap-3">
        {data.funnel.map((s) => (
          <div key={s.stage} className="flex flex-col gap-1">
            <div className="flex items-baseline justify-between text-[13px]">
              <span className="font-semibold">{s.stage}</span>
              <span className="tabular-nums text-ink2">
                {s.count.toLocaleString()}
                {s.conversion !== null && (
                  <span className="ml-2 font-semibold text-deep">{s.conversion}%</span>
                )}
              </span>
            </div>
            <div className="h-3 overflow-hidden rounded-full bg-muted">
              <div className="h-full rounded-full bg-deep"
                   style={{ width: `${Math.max((s.count / max) * 100, 0.6)}%` }} />
            </div>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Distance({ data }: { data: Insights }) {
  const rows = data.sales_by_distance;
  const max = Math.max(1, ...rows.map((r) => r.sales));
  return (
    <Panel
      title="How far a sold item travelled"
      hint="Buyer's ZIP to the listing's ZIP. Sales with no identified buyer are shown rather than dropped — that share is a measurement too."
    >
      <div className="flex flex-col gap-2.5">
        {rows.map((r) => {
          const unknown = r.band.startsWith("Buyer not");
          return (
            <div key={r.band} className="flex items-center gap-3">
              <span className="w-[150px] shrink-0 text-[12.5px] text-ink2">{r.band}</span>
              <div className="h-4 flex-1 overflow-hidden rounded-[5px] bg-muted">
                <div className={`h-full rounded-[5px] ${unknown ? "bg-ink3" : "bg-primary"}`}
                     style={{ width: `${(r.sales / max) * 100}%` }} />
              </div>
              <span className="w-9 shrink-0 text-right text-[12.5px] font-semibold tabular-nums">
                {r.sales}
              </span>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

function Searches({ data }: { data: Insights }) {
  const s = data.searches;
  return (
    <Panel
      title="What people search for"
      hint={`${s.empty_share}% of searches return nothing. Those are the clearest signal of what the catalogue is missing.`}
    >
      <div className="flex flex-col">
        {s.top.map((row) => (
          <div key={row.query}
               className="flex items-center justify-between border-b border-line py-2 last:border-0">
            <span className="text-[13.5px] font-medium">{row.query}</span>
            <span className="flex items-center gap-3 text-[12.5px] tabular-nums text-ink2">
              <span>{row.searches} searches</span>
              {row.empty > 0 ? (
                <span className="rounded-full bg-[var(--color-warn)]/15 px-2 py-0.5 font-semibold text-warn">
                  {row.empty} empty
                </span>
              ) : (
                <span className="text-ink3">{row.clicks} clicks</span>
              )}
            </span>
          </div>
        ))}
      </div>
    </Panel>
  );
}

function Categories({ data }: { data: Insights }) {
  const max = Math.max(1, ...data.categories.map((c) => c.listings));
  return (
    <Panel title="Categories" hint="Volume, what sells, and the median asking price.">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[520px] text-[13px]">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-[0.07em] text-ink2">
              <th className="pb-2 font-semibold">Category</th>
              <th className="pb-2 font-semibold">Listings</th>
              <th className="pb-2 font-semibold">Sold</th>
              <th className="pb-2 font-semibold">Sell-through</th>
              <th className="pb-2 font-semibold">Median price</th>
            </tr>
          </thead>
          <tbody>
            {data.categories.map((c) => (
              <tr key={c.category} className="border-t border-line">
                <td className="py-2.5">
                  <span className="flex items-center gap-2">
                    <span className="h-2 rounded-full bg-accent"
                          style={{ width: `${Math.max((c.listings / max) * 60, 4)}px` }} />
                    {c.category.replace(/_/g, " ")}
                  </span>
                </td>
                <td className="py-2.5 tabular-nums">{c.listings}</td>
                <td className="py-2.5 tabular-nums">{c.sold}</td>
                <td className="py-2.5 tabular-nums">{c.sell_through}%</td>
                <td className="py-2.5 tabular-nums">${c.median_price}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Panel>
  );
}
