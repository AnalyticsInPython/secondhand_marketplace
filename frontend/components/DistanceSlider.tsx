"use client";

import { api } from "@/lib/api";
import type { FacetCount } from "@/lib/types";

const STEPS = [0.5, 1, 2.5, 5, 10];

/**
 * Distance from the viewer's ZIP — UX_SPEC.md §6.3.
 *
 * The count next to the value is what you would get at this radius. It moves as
 * the handle moves, which is the honest version of a filter: the cost of a
 * tighter circle is visible before you choose it.
 *
 * Every release is logged, because "which filter is doing the work" is a
 * research question and the answer lives in `filter_events`.
 */
export function DistanceSlider({
  zip,
  value,
  count,
  steps,
  onChange,
}: {
  zip: string;
  value: number;
  count: number;
  steps?: FacetCount[];
  onChange: (miles: number) => void;
}) {
  function commit(miles: number) {
    onChange(miles);
    api.logFilter("radius_mi", count, String(miles));
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span className="flex-1 text-[15px] font-bold text-ink">
          Within {value} {value === 1 ? "mile" : "miles"}
        </span>
        <span className="rounded-full bg-tint px-2.5 py-1 text-[11px] font-semibold text-deep">
          {count.toLocaleString()} items
        </span>
      </div>

      <input
        type="range"
        min={0.5}
        max={10}
        step={0.5}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        onMouseUp={(e) => commit(Number((e.target as HTMLInputElement).value))}
        onTouchEnd={(e) => commit(Number((e.target as HTMLInputElement).value))}
        className="w-full accent-[var(--color-deep)]"
        aria-label={`Distance from ${zip} in miles`}
      />

      <div className="flex justify-between text-[11px] text-ink3">
        <span>0.5 mi</span>
        <span>10 mi</span>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {STEPS.map((s) => {
          const facet = steps?.find((f) => Number(f.key) === s);
          return (
            <button
              key={s}
              type="button"
              onClick={() => commit(s)}
              title={facet ? `${facet.count} items` : undefined}
              className={`rounded-full px-2.5 py-1.5 text-[11.5px] font-semibold transition-colors ${
                value === s ? "bg-deep text-white" : "bg-muted text-ink2 hover:bg-line"
              }`}
            >
              {s} mi
            </button>
          );
        })}
      </div>

      <p className="text-[11.5px] leading-[17px] text-ink3">
        Distance is measured between ZIP centroids — we never store or show a street address.
      </p>
    </div>
  );
}
