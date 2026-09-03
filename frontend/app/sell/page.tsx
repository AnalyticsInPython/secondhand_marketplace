"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { MobileTabBar, TopNav } from "@/components/TopNav";
import {
  Button,
  CameraIcon,
  Card,
  Checkbox,
  Chip,
  Field,
  Input,
  MatchBadge,
  PinIcon,
  Segmented,
  XIcon,
} from "@/components/ui";
import { api } from "@/lib/api";
import { CATEGORY_LABELS, CONDITION_LABELS } from "@/lib/format";
import type { Category, Condition, EnumsRef, Me, Photo } from "@/lib/types";

/**
 * Post a listing — UX_SPEC.md §6.5.
 *
 * Note what is *not* on this page: an audience picker. Who sees a listing is
 * decided by each buyer's own filters, so the seller has no visibility control
 * to submit (UX_SPEC.md §2).
 */
export default function SellPage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [enums, setEnums] = useState<EnumsRef | null>(null);

  const [photos, setPhotos] = useState<Photo[]>([]);
  const [uploading, setUploading] = useState<string | null>(null);
  const [photoError, setPhotoError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<Category>("furniture");
  const [subcategory, setSubcategory] = useState<string | null>(null);
  const [condition, setCondition] = useState<Condition>("used_good");
  const [priceUsd, setPriceUsd] = useState("");
  const [isFree, setIsFree] = useState(false);
  const [negotiable, setNegotiable] = useState(true);
  const [zip, setZip] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .me()
      .then((u) => {
        setMe(u);
        setZip(u.zip_code);
      })
      .catch(() => router.replace("/signin"));
    api.enums().then(setEnums).catch(() => setEnums(null));
  }, [router]);

  const maxPhotos = enums?.photos.max_per_listing ?? 10;
  const subcategories = enums?.categories.find((c) => c.value === category)?.subcategories ?? [];

  async function addFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setPhotoError(null);
    const room = maxPhotos - photos.length;
    const picked = Array.from(files).slice(0, room);
    if (picked.length < files.length) setPhotoError(`Up to ${maxPhotos} photos per listing.`);
    for (let i = 0; i < picked.length; i++) {
      setUploading(`Uploading ${i + 1} of ${picked.length}…`);
      try {
        const photo = await api.uploadPhoto(picked[i]);
        setPhotos((p) => [...p, photo]);
      } catch (e) {
        setPhotoError(e instanceof Error ? e.message : "That photo could not be uploaded");
      }
    }
    setUploading(null);
    if (fileInput.current) fileInput.current.value = "";
  }

  function removePhoto(url: string) {
    setPhotos((p) => p.filter((x) => x.url !== url));
  }

  function makeCover(url: string) {
    setPhotos((p) => [p.find((x) => x.url === url)!, ...p.filter((x) => x.url !== url)]);
  }

  const zipOk = /^\d{5}$/.test(zip);
  const missing = [
    photos.length === 0 && "at least one photo",
    !title.trim() && "a title",
    !isFree && !(Number(priceUsd) > 0) && 'a price, or "free"',
    !zipOk && "a pickup ZIP code",
  ].filter(Boolean) as string[];

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      const listing = await api.createListing({
        title: title.trim(),
        description: description.trim() || null,
        category,
        subcategory: subcategories.length > 0 ? subcategory : null,
        condition,
        price_cents: isFree ? 0 : Math.round(Number(priceUsd) * 100),
        is_free: isFree,
        is_negotiable: negotiable,
        zip_code: zip,
        photo_urls: photos.map((p) => p.url),
      });
      router.push(`/listings/${listing.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
      setBusy(false);
    }
  }

  return (
    <>
      <TopNav me={me} />

      <main className="mx-auto flex max-w-[1240px] flex-col gap-6 p-4 md:flex-row md:items-start md:gap-9 md:p-10">
        <div className="flex min-w-0 flex-1 flex-col gap-6">
          <div className="flex flex-col gap-2">
            <h1 className="text-[30px] font-bold tracking-[-0.02em]">List an item</h1>
            <p className="text-[15px] leading-6 text-ink2">
              Everything here is public to any verified member whose filters match it. Posting takes
              about two minutes.
            </p>
          </div>

          <Card className="flex flex-col gap-7 p-6 md:p-8">
            <Field
              label="Photos"
              hint={`Up to ${maxPhotos} · JPG, PNG or WebP · 10 MB each. The first is the cover. Daylight, whole item in frame, and a shot of any damage.`}
              error={photoError ?? undefined}
            >
              <input
                ref={fileInput}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/heic"
                multiple
                hidden
                onChange={(e) => addFiles(e.target.files)}
              />
              <div className="flex flex-wrap gap-3">
                <button
                  type="button"
                  disabled={uploading !== null || photos.length >= maxPhotos}
                  onClick={() => fileInput.current?.click()}
                  className="flex h-[124px] w-[124px] flex-col items-center justify-center gap-1.5 rounded-[12px] border-[1.5px] border-dashed border-light bg-tint text-deep transition-colors hover:bg-light/40 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  <CameraIcon className="h-6 w-6" />
                  <span className="text-[13px] font-semibold">{uploading ? "Uploading…" : "Add photos"}</span>
                  <span className="text-[11px] text-ink2">
                    {photos.length} / {maxPhotos}
                  </span>
                </button>
                {photos.map((p, i) => (
                  <div
                    key={p.url}
                    className="group relative h-[124px] w-[124px] overflow-hidden rounded-[12px] border border-line bg-muted"
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={p.url} alt="" className="h-full w-full object-cover" />
                    {i === 0 ? (
                      <span className="absolute left-2 top-2 rounded-full bg-white px-2 py-0.5 text-[9.5px] font-semibold tracking-[0.02em] text-deep">
                        COVER
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => makeCover(p.url)}
                        className="absolute left-2 top-2 rounded-full bg-white/90 px-2 py-0.5 text-[9.5px] font-semibold tracking-[0.02em] text-ink2 opacity-0 transition-opacity group-hover:opacity-100"
                      >
                        MAKE COVER
                      </button>
                    )}
                    <button
                      type="button"
                      aria-label="Remove photo"
                      onClick={() => removePhoto(p.url)}
                      className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-full bg-[var(--color-overlay)] text-white"
                    >
                      <XIcon className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
              {uploading && <p className="text-[12px] text-ink2">{uploading}</p>}
            </Field>

            <Field label="Title" hint={`${title.length} / 60`}>
              <Input value={title} onChange={(v) => setTitle(v.slice(0, 60))} placeholder="IKEA MALM desk 140×65, white" />
            </Field>

            <Field label="Category">
              <div className="flex flex-wrap gap-2">
                {(Object.keys(CATEGORY_LABELS) as Category[]).map((c) => (
                  <Chip
                    key={c}
                    active={category === c}
                    onClick={() => {
                      setCategory(c);
                      setSubcategory(null);
                      if (c === "free_stuff") setIsFree(true);
                    }}
                  >
                    {CATEGORY_LABELS[c]}
                  </Chip>
                ))}
              </div>
              {subcategories.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-2 border-l-2 border-line pl-3">
                  {subcategories.map((s) => (
                    <Chip key={s.value} active={subcategory === s.value} onClick={() => setSubcategory(subcategory === s.value ? null : s.value)}>
                      {s.label}
                    </Chip>
                  ))}
                </div>
              )}
            </Field>

            <Field label="Condition">
              <Segmented<Condition>
                value={condition}
                onChange={setCondition}
                options={(Object.keys(CONDITION_LABELS) as Condition[]).map((c) => ({
                  value: c,
                  label: CONDITION_LABELS[c],
                }))}
              />
            </Field>

            <div className="grid gap-5 md:grid-cols-2">
              <Field label="Price" error={!isFree && priceUsd !== "" && !(Number(priceUsd) > 0) ? 'Enter a price, or tick "free".' : undefined}>
                <Input
                  value={isFree ? "Free" : priceUsd}
                  onChange={(v) => setPriceUsd(v.replace(/[^\d.]/g, ""))}
                  disabled={isFree}
                  placeholder="60"
                  type={isFree ? "text" : "text"}
                  left={<span className="text-[16px] font-bold text-ink2">$</span>}
                  right={<span className="text-[12px] font-semibold text-ink3">USD</span>}
                />
              </Field>
              <div className="flex flex-col justify-end gap-3 pb-1">
                <label className="flex items-center gap-2.5 text-[14px] text-ink2">
                  <Checkbox on={isFree} onChange={setIsFree} />
                  Give it away for free
                </label>
                <label className="flex items-center gap-2.5 text-[14px] text-ink2">
                  <Checkbox on={negotiable} onChange={setNegotiable} />
                  Price is negotiable
                </label>
              </div>
            </div>

            <Field
              label="Pickup ZIP code"
              hint="Buyers see the ZIP and the distance, never your street address. Handover happens on campus or at a corner you pick."
              error={zip && !zipOk ? "Five digits, e.g. 10027." : undefined}
            >
              <Input
                value={zip}
                onChange={(v) => setZip(v.replace(/\D/g, "").slice(0, 5))}
                placeholder="10027"
                left={<PinIcon className="h-[17px] w-[17px] text-ink3" />}
              />
            </Field>

            <Field label="Description" hint={`${description.length} / 1000 · Say why you are selling, what condition it is really in, and when you can hand it over.`}>
              <textarea
                value={description}
                maxLength={1000}
                onChange={(e) => setDescription(e.target.value)}
                rows={6}
                placeholder="Bought new in August, used it for two semesters. Solid, no wobble…"
                className="rounded-[10px] border border-line-strong bg-surface p-4 text-[14.5px] leading-6 outline-none placeholder:text-ink3"
              />
            </Field>

            <div className="flex items-center gap-3 rounded-[12px] border border-line bg-muted p-4">
              <div>
                <p className="text-[13.5px] font-semibold">You do not choose the audience</p>
                <p className="text-[12.5px] leading-[19px] text-ink2">
                  Who sees this listing is decided by each buyer’s own filters — their distance radius,
                  category and trust settings. Your ZIP and affiliations only decide where it sits in
                  their results.
                </p>
              </div>
            </div>

            {error && <p className="text-[13px] text-danger">{error}</p>}

            <div className="flex items-center justify-end gap-4">
              {missing.length > 0 && (
                <p className="text-right text-[12px] text-ink3">Still needs {missing.join(", ")}.</p>
              )}
              <Button disabled={missing.length > 0 || busy || uploading !== null} onClick={submit}>
                {busy ? "Posting…" : "Post listing"}
              </Button>
            </div>
          </Card>
        </div>

        {/* Live preview of the feed card (desktop) */}
        <aside className="hidden w-[300px] shrink-0 flex-col gap-4 md:flex">
          <p className="text-[11px] font-semibold tracking-[0.08em] text-ink2">LIVE PREVIEW</p>
          <div className="overflow-hidden rounded-[14px] border border-line bg-surface">
            <div className="photo-placeholder relative aspect-[4/3] p-2.5">
              {photos[0] && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={photos[0].url} alt="" className="absolute inset-0 h-full w-full object-cover" />
              )}
              <span className="relative rounded-full bg-white px-2.5 py-1 text-[10px] font-semibold tracking-[0.02em] text-deep">
                {CONDITION_LABELS[condition].toUpperCase()}
              </span>
            </div>
            <div className="flex flex-col gap-1.5 px-3 pb-3.5 pt-3">
              <p className="line-clamp-2 text-[14px] font-semibold leading-5 text-ink">
                {title.trim() || "Your title"}
              </p>
              <p className="text-[17px] font-bold tracking-[-0.02em] text-ink">
                {isFree ? "Free" : Number(priceUsd) > 0 ? `$${Math.round(Number(priceUsd)).toLocaleString()}` : "$—"}
              </p>
              <p className="text-[11.5px] text-ink3">{zipOk ? zip : "ZIP"} · 0.0 mi · just now</p>
              <div className="flex flex-wrap gap-1">
                <MatchBadge>SAME ZIP</MatchBadge>
                <MatchBadge>SAME COUNTRY</MatchBadge>
                <MatchBadge>SAME SCHOOL</MatchBadge>
              </div>
            </div>
          </div>
          <div className="rounded-[12px] border border-light bg-tint p-4">
            <p className="text-[13.5px] font-semibold text-deep">Badges are automatic</p>
            <p className="text-[12.5px] leading-[19px] text-ink2">
              Buyers see only the attributes they share with you. Someone with nothing in common sees
              no badges at all — and never learns your country or school.
            </p>
          </div>
        </aside>
      </main>

      <MobileTabBar />
    </>
  );
}
