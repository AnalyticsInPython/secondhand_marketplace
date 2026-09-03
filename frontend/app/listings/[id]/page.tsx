"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";

import { MobileTabBar, TopNav } from "@/components/TopNav";
import {
  Button,
  Card,
  ChevronLeftIcon,
  HeartIcon,
  MailIcon,
  MatchBadge,
  PinIcon,
  SectionLabel,
  ShareIcon,
  ShieldIcon,
  SmsIcon,
} from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import {
  absoluteDate,
  CATEGORY_LABELS,
  CONDITION_LABELS,
  placeholderGradient,
  price,
  relativeTime,
  SUBCATEGORY_LABELS,
} from "@/lib/format";
import type { ListingDetail, ListingStatus, Me } from "@/lib/types";

export default function ListingPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [listing, setListing] = useState<ListingDetail | null>(null);
  const [gone, setGone] = useState(false);

  useEffect(() => {
    api.me().then(setMe).catch(() => router.replace("/signin"));
    api
      .listing(id)
      .then(setListing)
      .catch((e) => {
        if (e instanceof ApiError && e.status === 401) router.replace("/signin");
        else setGone(true);
      });
  }, [id, router]);

  if (gone) {
    return (
      <>
        <TopNav me={me} />
        <main className="mx-auto flex max-w-[1200px] flex-col items-start gap-3 p-10">
          <h1 className="text-[22px] font-bold tracking-[-0.02em]">This listing is no longer available</h1>
          <p className="text-[14px] text-ink2">It was taken down by the seller, or the link is wrong.</p>
          <Link href="/" className="text-[14px] font-semibold text-deep">
            Back to the feed
          </Link>
        </main>
      </>
    );
  }

  if (!listing) {
    return (
      <>
        <TopNav me={me} />
        <div className="mx-auto max-w-[1200px] p-10 text-ink2">Loading…</div>
      </>
    );
  }

  const sold = listing.status === "sold";
  const categoryLabel = listing.subcategory
    ? `${CATEGORY_LABELS[listing.category]} · ${SUBCATEGORY_LABELS[listing.subcategory] ?? listing.subcategory}`
    : CATEGORY_LABELS[listing.category];

  return (
    <>
      <TopNav me={me} />

      <main className="mx-auto flex max-w-[1200px] flex-col gap-8 px-0 py-0 md:flex-row md:px-10 md:py-7">
        {/* ---------------- gallery + description ---------------- */}
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <Link
            href="/"
            className="hidden items-center gap-1 text-[13px] font-medium text-ink2 hover:text-ink md:flex"
          >
            <ChevronLeftIcon className="h-3.5 w-3.5" />
            Back to feed · {CATEGORY_LABELS[listing.category]} · {listing.zip_code}
          </Link>

          <Gallery listing={listing} />

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
              <ShieldIcon className="h-5 w-5 shrink-0 text-deep" />
              <div>
                <p className="text-[13.5px] font-semibold text-deep">Meet on campus</p>
                <p className="text-[12px] leading-[18px] text-ink2">
                  Lerner Hall lobby and the Butler entrance are the two most-used handover spots. Never
                  send a deposit before you see the item.
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
              {listing.is_negotiable && !sold && !listing.is_free && (
                <span className="ml-2 align-middle text-[12px] font-semibold tracking-normal text-ink2">
                  negotiable
                </span>
              )}
            </p>

            <dl className="flex flex-col">
              <Row label="Category" value={categoryLabel} />
              <Row label="Condition" value={CONDITION_LABELS[listing.condition]} />
              <Row
                label="Pickup"
                value={listing.neighbourhood ? `${listing.zip_code} · ${listing.neighbourhood}` : listing.zip_code}
              />
              {listing.distance_mi !== null && !listing.is_owner && (
                <Row label="From you" value={`${listing.distance_mi.toFixed(1)} mi`} />
              )}
              <Row label="Posted" value={absoluteDate(listing.posted_at)} />
            </dl>

            {listing.is_owner ? (
              <OwnerActions listing={listing} onChange={setListing} />
            ) : (
              <ContactBlock listing={listing} onChange={setListing} />
            )}
          </Card>

          {listing.seller && !listing.is_owner && <SellerCard listing={listing} />}

          <Card className="flex items-center gap-3 p-5">
            <PinIcon className="h-5 w-5 shrink-0 text-deep" />
            <p className="text-[12px] leading-[18px] text-ink2">
              Buyers see the ZIP and the distance, never a street address. Handover happens on campus or
              at a corner you both pick.
            </p>
          </Card>
        </aside>
      </main>

      <MobileTabBar />
    </>
  );
}

/** Cover plus thumbnails (state D1). The gradient stands in when there are no photos. */
function Gallery({ listing }: { listing: ListingDetail }) {
  const [index, setIndex] = useState(0);
  const photos = listing.photo_urls;
  const current = photos[index];
  return (
    <div className="flex flex-col gap-3">
      <div
        className="photo-placeholder relative aspect-[4/3] w-full overflow-hidden md:rounded-[16px]"
        style={placeholderGradient(listing.id)}
      >
        {current && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={current} alt={listing.title} className="absolute inset-0 h-full w-full object-cover" />
        )}
        <span className="absolute left-4 top-4 rounded-full bg-white px-2.5 py-1 text-[10px] font-semibold tracking-[0.02em] text-deep">
          {CONDITION_LABELS[listing.condition].toUpperCase()}
        </span>
        {photos.length > 1 && (
          <span className="absolute right-4 top-4 rounded-full bg-[var(--color-overlay)]/85 px-2.5 py-1 text-[11px] font-semibold text-white">
            {index + 1} / {photos.length}
          </span>
        )}
        {!current && (
          <span className="absolute bottom-4 left-4 text-[10px] font-bold tracking-[0.08em] text-[var(--color-overlay)]/55">
            {CATEGORY_LABELS[listing.category].toUpperCase()}
          </span>
        )}
      </div>
      {photos.length > 1 && (
        <div className="flex gap-2.5 overflow-x-auto px-4 md:px-0">
          {photos.map((url, i) => (
            <button
              key={url}
              type="button"
              onClick={() => setIndex(i)}
              className={`h-[72px] w-[96px] shrink-0 overflow-hidden rounded-[10px] border-[1.5px] ${
                i === index ? "border-deep" : "border-line"
              }`}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={url} alt="" className="h-full w-full object-cover" />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * The two contact shapes — UX_SPEC.md §5.1.
 *
 * Phone is optional at sign-up, so a seller may have no number. When they do
 * not, this is a single full-width Email button — not a disabled Text button
 * and not a gap where one used to be.
 */
function ContactBlock({
  listing,
  onChange,
}: {
  listing: ListingDetail;
  onChange: (l: ListingDetail) => void;
}) {
  const [revealed, setRevealed] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const canText = listing.seller?.can_receive_sms ?? false;
  const sold = listing.status === "sold";

  async function contact(channel: "email" | "sms") {
    setBusy(true);
    try {
      const res = await api.enquire(listing.id, channel);
      const target = channel === "email" ? res.address : res.phone;
      if (!target) return;
      setRevealed(target);
      onChange({ ...listing, enquiry_count: listing.enquiry_count + 1 });
      window.location.href =
        channel === "email"
          ? `mailto:${target}?subject=${encodeURIComponent(`Columbia Market: ${listing.title}`)}`
          : `sms:${target}`;
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Could not reach the seller");
    } finally {
      setBusy(false);
    }
  }

  async function toggleSave() {
    setBusy(true);
    try {
      if (listing.is_saved) {
        await api.unsave(listing.id);
        onChange({ ...listing, is_saved: false, save_count: Math.max(0, listing.save_count - 1) });
      } else {
        await api.save(listing.id);
        onChange({ ...listing, is_saved: true, save_count: listing.save_count + 1 });
      }
    } finally {
      setBusy(false);
    }
  }

  async function share() {
    const url = window.location.href;
    try {
      if (navigator.share) {
        await navigator.share({ title: listing.title, url });
      } else {
        await navigator.clipboard.writeText(url);
        setNote("Link copied.");
      }
    } catch {
      /* the user dismissed the sheet */
    }
  }

  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex gap-2.5">
        <div className="flex-1">
          <Button full disabled={sold || busy} icon={<MailIcon />} onClick={() => contact("email")}>
            Email seller
          </Button>
        </div>
        {canText && (
          <div className="flex-1">
            <Button full variant="ghost" disabled={sold || busy} icon={<SmsIcon />} onClick={() => contact("sms")}>
              Text seller
            </Button>
          </div>
        )}
      </div>

      <div className="flex gap-2.5">
        <div className="flex-1">
          <Button
            full
            variant="ghost"
            disabled={busy}
            icon={<HeartIcon filled={listing.is_saved} className={listing.is_saved ? "h-[18px] w-[18px] text-deep" : undefined} />}
            onClick={toggleSave}
          >
            {listing.is_saved ? "Saved" : "Save"}
          </Button>
        </div>
        <div className="flex-1">
          <Button full variant="ghost" icon={<ShareIcon />} onClick={share}>
            Share
          </Button>
        </div>
      </div>

      <p className="text-[11.5px] leading-[17px] text-ink3">
        {sold
          ? "This item has been sold. The seller can no longer be contacted through this listing."
          : canText
            ? "The seller’s number is only shared when you tap Text. In-app chat is not part of this version."
            : "This seller has no number on file, so email is the only way to reach them."}
      </p>

      {revealed && <p className="text-[12px] text-ok">Opening your app for {revealed}…</p>}
      {note && <p className="text-[12px] text-ink2">{note}</p>}
    </div>
  );
}

/** What the seller sees instead of the contact buttons (state D10). */
function OwnerActions({
  listing,
  onChange,
}: {
  listing: ListingDetail;
  onChange: (l: ListingDetail) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function set(status: ListingStatus) {
    setBusy(true);
    setError(null);
    try {
      onChange(await api.updateListing(listing.id, { status }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update the listing");
    } finally {
      setBusy(false);
    }
  }

  const s = listing.status;
  return (
    <div className="flex flex-col gap-3">
      <SectionLabel>YOUR LISTING</SectionLabel>
      <p className="text-[12.5px] leading-[18px] text-ink2">
        Buyers see this page without these controls. Marking it sold keeps the page reachable but
        removes it from every feed.
      </p>
      <div className="flex flex-wrap gap-2">
        {s !== "sold" && (
          <Button disabled={busy} onClick={() => set("sold")}>
            Mark as sold
          </Button>
        )}
        {s === "active" && (
          <Button variant="ghost" disabled={busy} onClick={() => set("reserved")}>
            Mark reserved
          </Button>
        )}
        {s !== "active" && (
          <Button variant="ghost" disabled={busy} onClick={() => set("active")}>
            {s === "sold" ? "Relist" : "Put back on sale"}
          </Button>
        )}
        {s !== "delisted" && (
          <Button variant="danger" disabled={busy} onClick={() => set("delisted")}>
            Take down
          </Button>
        )}
      </div>
      {error && <p className="text-[12px] text-danger">{error}</p>}
    </div>
  );
}

/**
 * Overlap-only disclosure made visible — UX_SPEC.md §5.3.
 *
 * The item, the price and the photos are identical for every viewer. Only this
 * block changes.
 */
function SellerCard({ listing }: { listing: ListingDetail }) {
  const seller = listing.seller!;
  return (
    <Card className="flex flex-col gap-4 p-6">
      <SectionLabel>SELLER</SectionLabel>
      <div className="flex items-center gap-3.5">
        <span className="flex h-12 w-12 items-center justify-center rounded-full bg-light text-[17px] font-bold text-deep">
          {seller.username.slice(0, 2).toUpperCase()}
        </span>
        <div>
          <p className="flex items-center gap-1.5 text-[16px] font-bold">
            @{seller.username}
            {seller.is_verified && <ShieldIcon className="h-4 w-4 text-ok" />}
          </p>
          <p className="text-[12.5px] text-ink2">
            Verified Columbia member · since {absoluteDate(seller.member_since)}
          </p>
        </div>
      </div>

      {seller.badges.length > 0 ? (
        <>
          <div className="flex flex-wrap gap-1.5">
            {seller.badges.map((b) => (
              <MatchBadge key={b}>{b}</MatchBadge>
            ))}
          </div>
          <p className="text-[12px] leading-[17px] text-ink2">
            {seller.badges.length === 3
              ? "You share all three with this seller."
              : `You share ${seller.badges.length === 1 ? "one thing" : "two things"} with this seller. Anything you do not share is not shown.`}
          </p>
        </>
      ) : (
        <p className="rounded-[10px] bg-muted p-3 text-[12px] leading-[17px] text-ink2">
          No shared attributes — nothing about this seller is revealed.
        </p>
      )}
    </Card>
  );
}

function StatusPill({ status }: { status: ListingStatus }) {
  const map: Record<ListingStatus, [string, string]> = {
    active: ["ON SALE", "bg-ok text-white"],
    reserved: ["RESERVED", "bg-warn text-white"],
    sold: ["SOLD", "bg-ink2 text-white"],
    draft: ["DRAFT", "bg-muted text-ink2"],
    delisted: ["TAKEN DOWN", "bg-muted text-ink2"],
  };
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
      <dd className="text-right text-[13.5px] font-semibold">{value}</dd>
    </div>
  );
}
