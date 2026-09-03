"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { CollectionPage } from "@/components/CollectionPage";
import { MailIcon, SmsIcon } from "@/components/ui";
import { api } from "@/lib/api";
import { price, relativeTime } from "@/lib/format";
import type { EnquiryRow, Me } from "@/lib/types";

/**
 * Inbox — UX_SPEC.md §6.6, reached from the avatar menu and the mobile tab bar.
 *
 * There is no in-app chat in this product (§1), and this screen does not pretend
 * otherwise. It is a record of contacts made: which listing, which channel, when.
 * The label is "Inbox", not "Chats", for exactly that reason.
 *
 * Rows are not cards, because the thing being listed is the *contact*, not the
 * item. The item is the subject line.
 */
export default function InboxPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [rows, setRows] = useState<EnquiryRow[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.me().then(setMe).catch(() => router.replace("/signin"));
    api
      .myEnquiries()
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [router]);

  return (
    <CollectionPage
      me={me}
      title="Inbox"
      blurb="Every seller you have contacted. Columbia Market hands over an address and gets out of the way — the conversation itself happens in your email or your messages."
      loading={loading}
      total={rows.length}
      empty={{
        headline: "You have not contacted anyone yet",
        body: "When you tap Email seller or Text seller on a listing, it is recorded here so you can find your way back to it.",
        cta: { href: "/", label: "Browse the feed" },
      }}
    >
      <div className="overflow-hidden rounded-[16px] border border-line bg-surface">
        {rows.map((row, i) => (
          <Link
            key={row.id}
            href={`/listings/${row.listing.id}`}
            className={`flex items-center gap-4 px-4 py-4 md:px-5 ${
              i > 0 ? "border-t border-line" : ""
            }`}
          >
            <span
              className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[11px] bg-tint text-deep"
              aria-hidden
            >
              {row.channel === "sms" ? <SmsIcon /> : <MailIcon />}
            </span>

            <span className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="truncate text-[15px] font-bold">{row.listing.title}</span>
              <span className="text-[13px] text-ink2">
                {row.channel === "sms" ? "Texted" : "Emailed"}
                {row.seller_username ? ` @${row.seller_username}` : " the seller"} ·{" "}
                {relativeTime(row.created_at)}
              </span>
              {/* Deliberately not cardMeta(): that ends in the listing's own
                  "posted N weeks ago", which sits next to the contact's "N weeks
                  ago" on the line above and reads as a contradiction. Location
                  only. */}
              <span className="text-[12px] text-ink3">
                {row.listing.zip_code}
                {row.listing.distance_mi !== null && ` · ${row.listing.distance_mi} mi`}
              </span>
            </span>

            <span className="shrink-0 text-[15px] font-bold">
              {price(row.listing.price_cents, row.listing.is_free)}
            </span>
          </Link>
        ))}
      </div>
    </CollectionPage>
  );
}
