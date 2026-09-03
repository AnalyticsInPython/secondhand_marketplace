"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CollectionPage } from "@/components/CollectionPage";
import { api } from "@/lib/api";
import type { ListingCard, Me } from "@/lib/types";

/**
 * My listings — everything this member has posted, in every status.
 *
 * Deliberately unfiltered: drafts and sold items are exactly what the owner came
 * here for, even though the feed hides both (UX_SPEC.md §6.4). The status pill on
 * each card is what distinguishes them.
 */
export default function MyListingsPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [items, setItems] = useState<ListingCard[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    api.me().then(setMe).catch(() => router.replace("/signin"));
    api
      .myListings()
      .then((page) => {
        setItems(page.items);
        setTotal(page.total);
      })
      .catch(() => setTotal(0))
      .finally(() => setLoading(false));
  }, [router]);

  const loadMore = useCallback(async () => {
    if (loadingMore) return;
    setLoadingMore(true);
    try {
      const page = await api.myListings(items.length);
      setItems((current) => {
        const seen = new Set(current.map((i) => i.id));
        return [...current, ...page.items.filter((i) => !seen.has(i.id))];
      });
    } finally {
      setLoadingMore(false);
    }
  }, [items.length, loadingMore]);

  const sold = items.filter((i) => i.status === "sold").length;

  return (
    <CollectionPage
      me={me}
      title="My listings"
      blurb={
        sold > 0
          ? `Everything you have posted, including drafts and the ${sold} you have sold.`
          : "Everything you have posted, including drafts and anything you have sold."
      }
      loading={loading}
      total={total}
      items={items}
      onLoadMore={loadMore}
      loadingMore={loadingMore}
      empty={{
        headline: "You have not posted anything yet",
        body: "Posting takes about two minutes: photos, a title, a price and the ZIP you can hand it over at.",
        cta: { href: "/sell", label: "Sell an item" },
      }}
    />
  );
}
