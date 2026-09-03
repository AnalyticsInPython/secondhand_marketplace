"use client";

import { use, useEffect, useState } from "react";

import { MobileTabBar, TopNav } from "@/components/TopNav";
import {
  Button,
  Card,
  HeartIcon,
  MailIcon,
  MatchBadge,
  PinIcon,
  ShieldIcon,
  SmsIcon,
} from "@/components/ui";
import { api } from "@/lib/api";
import { CATEGORY_LABELS, CONDITION_LABELS, placeholderGradient, price, relativeTime } from "@/lib/format";
import type { ListingDetail, Me } from "@/lib/types";

export default function ListingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [me, setMe] = useState<Me | null>(null);
  const [listing, setListing] = useState<ListingDetail | null>(null);
  const [photoIndex, setPhotoIndex] = useState(0);

  useEffect(() => {
    api.me().then(setMe).catch(() => setMe(null));
    api.listing(id).then(setListing).catch(() => setListing(null));
  }, [id]);

  if (!listing) {
    return (
      <>
        <TopNav me={me} />
        <div className="mx-auto max-w-[1200px] p-10 text-ink2">Loading…</div>
      </>
    );
  }

  const sold = listing.status === "sold";

  return (
    <>
      <TopNav me={me} />

      <main className="mx-auto flex max-w-[1200px] flex-col gap-10 px-0 py-0 md:flex-row md:px-10 md:py-7">
        {/* ---------------- gallery + description ---------------- */}
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          {/* Gallery. The gradient stays underneath as the fallback, so a
              missing file degrades to the placeholder rather than to a broken
              image icon. Thumbnails only appear when there is more than one
              photo — state D1 in UX_SPEC §7. */}
          <div
            className="photo-placeholder relative aspect-[4/3] w-full overflow-hidden md:rounded-[16px]"
            style={placeholderGradient(listing.id)}
          >
            {listing.photo_urls[photoIndex] && (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={listing.photo_urls[photoIndex]}
                alt={listing.title}
                className="absolute inset-0 h-full w-full object-cover"
              />
            )}
          </div>

          {listing.photo_urls.length > 1 && (
            <div className="flex gap-2.5 overflow-x-auto px-4 md:px-0">
              {listing.photo_urls.map((url, i) => (
                <button
                  key={url}
                  type="button"
                  onClick={() => setPhotoIndex(i)}
                  aria-label={`Photo ${i + 1} of ${listing.photo_urls.length}`}
                  aria-current={i === photoIndex}
                  className={`photo-placeholder relative h-[86px] w-[116px] shrink-0 overflow-hidden rounded-[12px] border-2 ${
                    i === photoIndex ? "border-deep" : "border-transparent"
                  }`}
                  style={placeholderGradient(listing.id + i)}
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={url}
                    alt=""
                    className="absolute inset-0 h-full w-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}

          <div className="flex flex-col gap-3.5 px-4 md:px-0">
            <Card className="flex flex-col gap-3 p-6">
              <h2 className="text-[17px] font-bold">Description</h2>
              <p className="whitespace-pre-line text-[14.5px] leading-[25px] text-ink2">
                {listing.description ?? "No description."}
              </p>
              <div className="flex gap-4 pt-2 text-[13px] text-ink2">
                <span>{listing.view_count} views</span>
                <span>{listing.save_count} saved</span>
                <span>{listing.enquiry_count} enquiries</span>
              </div>
            </Card>

            <Card className="flex items-center gap-3 border-light bg-tint p-5">
              <PinIcon className="h-5 w-5 shrink-0 text-deep" />
              <div>
                <p className="text-[13.5px] font-semibold">
                  {listing.zip_code}
                  {listing.distance_mi !== null && ` · ${listing.distance_mi.toFixed(1)} mi from you`}
                </p>
                <p className="text-[12px] text-ink2">
                  Buyers see the ZIP and the distance, never a street address.
                </p>
              </div>
            </Card>
          </div>
        </div>

        {/* ---------------- action panel ---------------- */}
        <aside className="flex w-full flex-col gap-4 px-4 pb-6 md:w-[420px] md:shrink-0 md:px-0">
          <Card className="flex flex-col gap-4 p-7">
            <div className="flex gap-2">
              <StatusPill status={listing.status} />
              <span className="rounded-full bg-muted px-2.5 py-1.5 text-[10px] font-semibold tracking-[0.02em] text-ink2">
                LISTED {relativeTime(listing.posted_at).toUpperCase()}
              </span>
            </div>

            <h1 className="text-[24px] font-bold leading-8 tracking-[-0.02em]">{listing.title}</h1>
            <p className={`text-[36px] font-bold tracking-[-0.03em] ${sold ? "text-ink3 line-through" : ""}`}>
              {price(listing.price_cents, listing.is_free)}
            </p>

            <dl className="flex flex-col">
              <Row label="Category" value={CATEGORY_LABELS[listing.category]} />
              <Row label="Condition" value={CONDITION_LABELS[listing.condition]} />
              <Row label="Pickup" value={listing.zip_code} />
            </dl>

            <ContactBlock listing={listing} />
          </Card>

          {listing.seller && <SellerCard listing={listing} />}
        </aside>
      </main>

      <MobileTabBar />
    </>
  );
}

/**
 * The two contact shapes — UX_SPEC.md §5.1.
 *
 * Phone is optional at sign-up, so a seller may have no number. When they do
 * not, this is a single full-width Email button — not a disabled Text button
 * and not a gap where one used to be.
 */
function ContactBlock({ listing }: { listing: ListingDetail }) {
  const [revealed, setRevealed] = useState<string | null>(null);
  const canText = listing.seller?.can_receive_sms ?? false;
  const sold = listing.status === "sold";

  async function contact(channel: "email" | "sms") {
    const res = await api.enquire(listing.id, channel);
    const target = channel === "email" ? res.address : res.phone;
    if (!target) return;
    setRevealed(target);
    window.location.href = channel === "email" ? `mailto:${target}` : `sms:${target}`;
  }

  if (listing.is_external) {
    return (
      <a
        href={listing.external_url ?? "#"}
        target="_blank"
        rel="noreferrer"
        className="rounded-[12px] bg-deep px-5 py-3.5 text-center text-[15px] font-semibold text-white"
      >
        Continue to {listing.source_label}
      </a>
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex gap-2.5">
        <div className="flex-1">
          <Button full disabled={sold} icon={<MailIcon />} onClick={() => contact("email")}>
            Email seller
          </Button>
        </div>
        {canText && (
          <div className="flex-1">
            <Button full variant="ghost" disabled={sold} icon={<SmsIcon />} onClick={() => contact("sms")}>
              Text seller
            </Button>
          </div>
        )}
      </div>

      <div className="flex gap-2.5">
        <div className="flex-1">
          <Button full variant="ghost" icon={<HeartIcon />}>
            {listing.is_saved ? "Saved" : "Save"}
          </Button>
        </div>
        <div className="flex-1">
          <Button full variant="ghost">
            Share
          </Button>
        </div>
      </div>

      <p className="text-[11.5px] leading-[17px] text-ink3">
        {canText
          ? "The seller’s number is only shared when you tap Text. In-app chat is not part of this version."
          : "This seller has no number on file, so email is the only way to reach them."}
      </p>

      {revealed && <p className="text-[12px] text-ok">Opening your app for {revealed}…</p>}
    </div>
  );
}

/**
 * Overlap-only disclosure made visible — UX_SPEC.md §5.3.
 *
 * The item, the price and the photos are identical for every viewer. Only this
 * block changes, which is what makes the internal-vs-external comparison a
 * clean experiment.
 */
function SellerCard({ listing }: { listing: ListingDetail }) {
  const seller = listing.seller!;
  return (
    <Card className="flex flex-col gap-4 p-6">
      <p className="text-[11px] font-semibold tracking-[0.08em] text-ink2">SELLER</p>
      <div className="flex items-center gap-3.5">
        <span className="flex h-13 w-13 items-center justify-center rounded-full bg-light p-3 text-[17px] font-bold text-deep">
          {seller.username.slice(0, 2).toUpperCase()}
        </span>
        <div>
          <p className="flex items-center gap-1.5 text-[16px] font-bold">
            @{seller.username}
            {seller.is_verified && <ShieldIcon className="h-4 w-4 text-ok" />}
          </p>
          <p className="text-[12.5px] text-ink2">Verified Columbia member</p>
        </div>
      </div>

      {seller.badges.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {seller.badges.map((b) => (
            <MatchBadge key={b}>{b}</MatchBadge>
          ))}
        </div>
      ) : (
        <p className="rounded-[10px] bg-muted p-3 text-[12px] leading-[17px] text-ink2">
          No shared attributes — nothing about this seller is revealed.
        </p>
      )}
    </Card>
  );
}

function StatusPill({ status }: { status: ListingDetail["status"] }) {
  const map = {
    active: ["ON SALE", "bg-ok text-white"],
    reserved: ["RESERVED", "bg-warn text-white"],
    sold: ["SOLD", "bg-ink2 text-white"],
    draft: ["DRAFT", "bg-muted text-ink2"],
  } as const;
  const [label, cls] = map[status];
  return (
    <span className={`rounded-full px-2.5 py-1.5 text-[10px] font-semibold tracking-[0.02em] ${cls}`}>
      {label}
    </span>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 border-t border-line py-3 first:border-t-0">
      <dt className="flex-1 text-[13.5px] text-ink2">{label}</dt>
      <dd className="text-[13.5px] font-semibold">{value}</dd>
    </div>
  );
}
