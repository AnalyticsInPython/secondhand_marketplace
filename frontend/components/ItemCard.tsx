"use client";

import Link from "next/link";

import { cardMeta, CATEGORY_LABELS, CONDITION_LABELS, placeholderGradient, price } from "@/lib/format";
import type { ListingCard as Item } from "@/lib/types";
import { ExternalBadge, HeartIcon, MatchBadge } from "./ui";

/**
 * One card in the feed — UX_SPEC.md §6.3.
 *
 * Badges come straight from `item.badges`. Do not compute them here: the client
 * is deliberately not given the seller's attributes to compare.
 */
export function ItemCard({ item }: { item: Item }) {
  return (
    <Link
      href={`/listings/${item.id}`}
      className="group flex flex-col overflow-hidden rounded-[14px] border border-line bg-surface"
    >
      <div
        className="photo-placeholder relative flex aspect-[4/3] flex-col justify-between p-2.5"
        style={placeholderGradient(item.id)}
      >
        {item.cover_photo_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={item.cover_photo_url}
            alt=""
            className="absolute inset-0 h-full w-full object-cover"
          />
        )}
        <div className="relative flex items-start justify-between">
          {item.is_external ? (
            <ExternalBadge label={item.source_label} />
          ) : (
            <span className="rounded-full bg-white px-2.5 py-1 text-[10px] font-semibold tracking-[0.02em] text-deep">
              {CONDITION_LABELS[item.condition].toUpperCase()}
            </span>
          )}
          <span className="flex h-7 w-7 items-center justify-center rounded-full bg-white text-ink2">
            <HeartIcon className="h-4 w-4" />
          </span>
        </div>
        <span className="relative text-[10px] font-bold tracking-[0.08em] text-[var(--color-overlay)]/55">
          {CATEGORY_LABELS[item.category].toUpperCase()}
        </span>
      </div>

      <div className="flex flex-col gap-1.5 px-3 pb-3.5 pt-3">
        <h3 className="line-clamp-2 text-[14px] font-semibold leading-5 text-ink">{item.title}</h3>
        <p className="text-[17px] font-bold tracking-[-0.02em] text-ink">
          {price(item.price_cents, item.is_free)}
        </p>
        <p className="text-[11.5px] text-ink3">{cardMeta(item)}</p>
        {(item.badges.length > 0 || item.is_external) && (
          <div className="flex flex-wrap gap-1">
            {item.badges.map((b) => (
              <MatchBadge key={b}>{b}</MatchBadge>
            ))}
            {item.is_external && (
              <span className="rounded-full bg-muted px-2 py-1 text-[9.5px] font-semibold text-ink2">
                {item.source_label}
              </span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
}

/** The mobile feed uses rows, not a grid (UX_SPEC.md §6.3). */
export function ItemRow({ item }: { item: Item }) {
  return (
    <Link href={`/listings/${item.id}`} className="flex gap-3.5 border-b border-line px-4 py-4">
      <div
        className="photo-placeholder h-28 w-28 shrink-0 rounded-[12px]"
        style={placeholderGradient(item.id)}
      />
      <div className="flex min-w-0 flex-col gap-1.5">
        <h3 className="line-clamp-2 text-[14.5px] font-semibold leading-5 text-ink">{item.title}</h3>
        <p className="text-[11.5px] text-ink3">{cardMeta(item)}</p>
        <p className="text-[16.5px] font-bold tracking-[-0.01em] text-ink">
          {price(item.price_cents, item.is_free)}
        </p>
        <div className="flex flex-wrap gap-1">
          {item.badges.map((b) => (
            <MatchBadge key={b}>{b}</MatchBadge>
          ))}
        </div>
      </div>
    </Link>
  );
}
