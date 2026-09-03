"use client";

import Link from "next/link";
import { useEffect, useRef, type ReactNode } from "react";

import { ItemCard, ItemRow } from "@/components/ItemCard";
import { MobileTabBar, TopNav } from "@/components/TopNav";
import type { ListingCard, Me } from "@/lib/types";

/**
 * The shell behind Saved items, My listings and Inbox — UX_SPEC.md §6.6.
 *
 * All three are the same shape: a heading, a count, and a grid of the same cards
 * the feed uses. Sharing the shell is what keeps a card identical wherever it
 * appears — same badges, same distance, same overlap-only disclosure — because
 * every one of them renders `ItemCard` off a `ListingCard` the API serialised.
 *
 * The empty state is a first-class argument, not an afterthought: these three
 * screens are empty for most members most of the time, so "nothing here yet" is
 * the common case and needs to say what to do about it.
 */
export function CollectionPage({
  me,
  title,
  blurb,
  loading,
  total,
  items,
  empty,
  onLoadMore,
  loadingMore,
  children,
}: {
  me: Me | null;
  title: string;
  blurb: string;
  loading: boolean;
  total: number;
  items?: ListingCard[];
  empty: { headline: string; body: string; cta?: { href: string; label: string } };
  onLoadMore?: () => void;
  loadingMore?: boolean;
  children?: ReactNode;
}) {
  const isEmpty = !loading && total === 0;
  const shown = items?.length ?? 0;
  const more = Boolean(onLoadMore) && shown > 0 && shown < total;
  const sentinel = useRef<HTMLDivElement>(null);

  // Same behaviour as the feed: auto-load when the sentinel comes into view,
  // with a real button so it works without an observer.
  useEffect(() => {
    const node = sentinel.current;
    if (!node || !more || !onLoadMore) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) onLoadMore();
      },
      { rootMargin: "600px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [more, onLoadMore]);

  return (
    <>
      <TopNav me={me} />

      <main className="mx-auto max-w-[1360px] px-4 py-7 pb-24 md:px-10 md:pb-7">
        <header className="mb-6 flex flex-col gap-1.5">
          <h1 className="text-[26px] font-bold tracking-[-0.02em] md:text-[32px]">{title}</h1>
          <p className="max-w-[62ch] text-[14.5px] leading-[23px] text-ink2">{blurb}</p>
          {!loading && total > 0 && (
            <p className="pt-1 text-[13px] font-semibold text-ink2">
              {total} {total === 1 ? "item" : "items"}
            </p>
          )}
        </header>

        {loading && <p className="py-16 text-center text-[14.5px] text-ink2">Loading…</p>}

        {isEmpty && (
          <div className="flex flex-col items-center gap-3 rounded-[16px] border border-line bg-surface px-6 py-20 text-center">
            <h2 className="text-[18px] font-bold">{empty.headline}</h2>
            <p className="max-w-[46ch] text-[14.5px] leading-[23px] text-ink2">{empty.body}</p>
            {empty.cta && (
              <Link
                href={empty.cta.href}
                className="mt-2 rounded-[10px] bg-deep px-5 py-3 text-[14px] font-semibold text-white"
              >
                {empty.cta.label}
              </Link>
            )}
          </div>
        )}

        {!loading && !isEmpty && children}

        {!loading && !isEmpty && items && (
          <>
            <div className="hidden grid-cols-2 gap-5 md:grid lg:grid-cols-4">
              {items.map((item) => (
                <ItemCard key={item.id} item={item} />
              ))}
            </div>
            <div className="-mx-4 md:hidden">
              {items.map((item) => (
                <ItemRow key={item.id} item={item} />
              ))}
            </div>

            <div ref={sentinel} className="flex flex-col items-center gap-3 py-10">
              {more ? (
                <>
                  <button
                    type="button"
                    onClick={onLoadMore}
                    disabled={loadingMore}
                    className="rounded-[10px] border border-line bg-surface px-5 py-3 text-[14px] font-semibold text-deep disabled:opacity-60"
                  >
                    {loadingMore ? "Loading…" : "Load more"}
                  </button>
                  <p className="text-[12.5px] text-ink3">
                    Showing {shown} of {total}
                  </p>
                </>
              ) : (
                shown > 0 && (
                  <p className="text-[12.5px] text-ink3">
                    That is all {total} {total === 1 ? "item" : "items"}.
                  </p>
                )
              )}
            </div>
          </>
        )}
      </main>

      <MobileTabBar />
    </>
  );
}
