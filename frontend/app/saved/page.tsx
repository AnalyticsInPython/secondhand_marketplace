"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { CollectionPage } from "@/components/CollectionPage";
import { api } from "@/lib/api";
import type { ListingCard, Me } from "@/lib/types";

/**
 * Saved items — the heart on every card, collected.
 *
 * Sold and reserved listings stay here on purpose. A save outlives the item's
 * availability, and having something quietly disappear because a seller marked
 * it sold reads as data loss rather than as a status change.
 */
export default function SavedPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [items, setItems] = useState<ListingCard[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  useEffect(() => {
    api.me().then(setMe).catch(() => router.replace("/signin"));
    api
      .mySaves()
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
      const page = await api.mySaves(items.length);
      setItems((current) => {
        const seen = new Set(current.map((i) => i.id));
        return [...current, ...page.items.filter((i) => !seen.has(i.id))];
      });
    } finally {
      setLoadingMore(false);
    }
  }, [items.length, loadingMore]);

  return (
    <CollectionPage
      me={me}
      title="Saved items"
      blurb="Everything you have tapped the heart on. Saving is private — the seller is never told."
      loading={loading}
      total={total}
      items={items}
      onLoadMore={loadMore}
      loadingMore={loadingMore}
      empty={{
        headline: "Nothing saved yet",
        body: "Tap the heart on any listing and it will wait for you here, even after it sells.",
        cta: { href: "/", label: "Browse the feed" },
      }}
    />
  );
}
