"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MobileTabBar, TopNav } from "@/components/TopNav";
import { Button, Card, Checkbox, Chip, Field, Input, PinIcon, Segmented } from "@/components/ui";
import { api } from "@/lib/api";
import { CATEGORY_LABELS, CONDITION_LABELS } from "@/lib/format";
import type { Category, Condition, Me } from "@/lib/types";

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

  const [title, setTitle] = useState("");
  const [category, setCategory] = useState<Category>("furniture");
  const [condition, setCondition] = useState<Condition>("used_good");
  const [priceUsd, setPriceUsd] = useState("");
  const [isFree, setIsFree] = useState(false);
  const [negotiable, setNegotiable] = useState(true);
  const [zip, setZip] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .me()
      .then((u) => {
        setMe(u);
        setZip(u.zip_code);
      })
      .catch(() => router.push("/signin"));
  }, [router]);

  const missing = [
    !title && "a title",
    !isFree && !Number(priceUsd) && 'a price, or "free"',
    !zip && "a pickup ZIP code",
  ].filter(Boolean) as string[];

  async function submit() {
    setError(null);
    try {
      const listing = await api.createListing({
        title,
        description: description || null,
        category,
        condition,
        price_cents: isFree ? 0 : Math.round(Number(priceUsd) * 100),
        is_free: isFree,
        is_negotiable: negotiable,
        zip_code: zip,
        photo_urls: [],
      });
      router.push(`/listings/${listing.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    }
  }

  return (
    <>
      <TopNav me={me} />

      <main className="mx-auto flex max-w-[1000px] flex-col gap-6 p-4 md:p-10">
        <div className="flex flex-col gap-2">
          <h1 className="text-[30px] font-bold tracking-[-0.02em]">List an item</h1>
          <p className="text-[15px] leading-6 text-ink2">
            Everything here is public to any verified member whose filters match it. Posting takes
            about two minutes.
          </p>
        </div>

        <Card className="flex flex-col gap-7 p-6 md:p-8">
          {/* Photos: the uploader is Brian's — it needs the Figma asset export
              and the storage decision. Wired to an empty array until then. */}
          <Field label="Photos" hint="Up to 10 · JPG, PNG or HEIC · 10 MB each. First one is the cover.">
            <div className="flex h-32 items-center justify-center rounded-[12px] border-[1.5px] border-dashed border-light bg-tint text-[13px] font-semibold text-deep">
              Photo uploader — not wired yet
            </div>
          </Field>

          <Field label="Title">
            <Input value={title} onChange={setTitle} placeholder="IKEA MALM desk 140×65, white" />
          </Field>

          <Field label="Category">
            <div className="flex flex-wrap gap-2">
              {(Object.keys(CATEGORY_LABELS) as Category[]).map((c) => (
                <Chip key={c} active={category === c} onClick={() => setCategory(c)}>
                  {CATEGORY_LABELS[c]}
                </Chip>
              ))}
            </div>
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
            <Field label="Price">
              <Input
                value={isFree ? "Free" : priceUsd}
                onChange={setPriceUsd}
                disabled={isFree}
                placeholder="60"
                left={<span className="text-[16px] font-bold text-ink2">$</span>}
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
            hint="Buyers see the ZIP and the distance, never your street address."
          >
            <Input
              value={zip}
              onChange={setZip}
              placeholder="10027"
              left={<PinIcon className="h-[17px] w-[17px] text-ink3" />}
            />
          </Field>

          <Field label="Description" hint={`${description.length} / 1000`}>
            <textarea
              value={description}
              maxLength={1000}
              onChange={(e) => setDescription(e.target.value)}
              rows={6}
              placeholder="Say why you are selling, what condition it is really in, and when you can hand it over."
              className="rounded-[10px] border border-line-strong bg-surface p-4 text-[14.5px] leading-6 outline-none placeholder:text-ink3"
            />
          </Field>

          <div className="flex items-center gap-3 rounded-[12px] border border-line bg-muted p-4">
            <div>
              <p className="text-[13.5px] font-semibold">You do not choose the audience</p>
              <p className="text-[12.5px] leading-[19px] text-ink2">
                Who sees this listing is decided by each buyer’s own filters — their distance radius,
                category and trust settings.
              </p>
            </div>
          </div>

          {error && <p className="text-[13px] text-danger">{error}</p>}

          <div className="flex justify-end gap-3">
            <Button variant="ghost">Save draft</Button>
            <Button disabled={missing.length > 0} onClick={submit}>
              Post listing
            </Button>
          </div>
          {missing.length > 0 && (
            <p className="-mt-4 text-right text-[12px] text-ink3">Still needs {missing.join(", ")}.</p>
          )}
        </Card>
      </main>

      <MobileTabBar />
    </>
  );
}
