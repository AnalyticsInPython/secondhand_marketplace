"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { MobileTabBar, TopNav } from "@/components/TopNav";
import { Button, Card, Field, Input, PinIcon, SectionLabel, Toggle } from "@/components/ui";
import { api } from "@/lib/api";
import type { Me } from "@/lib/types";

/**
 * Profile & account — UX_SPEC.md §6.6.
 *
 * Reached from the avatar in the top-right. Everything here is editable except
 * the Columbia email, which has no route on purpose: it is the identity, and
 * changing it would mean a different account.
 */
export default function ProfilePage() {
  const router = useRouter();
  const [me, setMe] = useState<Me | null>(null);
  const [draft, setDraft] = useState<Partial<Me>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.me().then(setMe).catch(() => router.push("/signin"));
  }, [router]);

  if (!me) return <div className="p-10 text-ink2">Loading…</div>;

  const value = <K extends keyof Me>(k: K): Me[K] => (draft[k] ?? me[k]) as Me[K];
  const changed = Object.keys(draft).filter((k) => draft[k as keyof Me] !== me[k as keyof Me]);

  async function save() {
    setSaving(true);
    try {
      setMe(await api.updateMe(draft));
      setDraft({});
    } finally {
      setSaving(false);
    }
  }

  const hasPhone = Boolean(value("phone"));

  return (
    <>
      <TopNav me={me} />

      <main className="mx-auto flex max-w-[1000px] flex-col gap-6 p-4 md:p-10">
        <div className="flex flex-col gap-2">
          <h1 className="text-[30px] font-bold tracking-[-0.02em]">Profile & account</h1>
          <p className="text-[15px] leading-6 text-ink2">
            Four of these fields decide what you see and what buyers see about you. Your Columbia
            email is fixed — everything else can change at any time.
          </p>
        </div>

        {/* Identity */}
        <Card className="flex flex-col gap-5 p-6 md:p-7">
          <SectionLabel>IDENTITY</SectionLabel>
          <Field
            label="Columbia email"
            locked
            hint="Your email is your membership. A different address would mean a different account."
          >
            <Input value={me.email} onChange={() => {}} disabled />
          </Field>
        </Card>

        {/* Public profile */}
        <Card className="flex flex-col gap-5 p-6 md:p-7">
          <SectionLabel>PUBLIC PROFILE</SectionLabel>
          <Field label="Username" hint="Shown on every listing, whether or not the buyer overlaps with you.">
            <Input value={value("username")} onChange={(v) => setDraft({ ...draft, username: v })} />
          </Field>
        </Card>

        {/* Matching attributes */}
        <Card className="flex flex-col gap-5 p-6 md:p-7">
          <SectionLabel>MATCHING ATTRIBUTES</SectionLabel>
          <div className="grid gap-5 md:grid-cols-2">
            <Field label="Nationality">
              <Input
                value={value("nationality")}
                onChange={(v) => setDraft({ ...draft, nationality: v.toUpperCase() })}
              />
            </Field>
            <Field label="College / School">
              <Input value={value("school")} onChange={(v) => setDraft({ ...draft, school: v })} />
            </Field>
            <Field label="Grade">
              <Input value={value("grade")} onChange={(v) => setDraft({ ...draft, grade: v as Me["grade"] })} />
            </Field>
            <Field label="ZIP code" hint="Changing this re-centres your feed.">
              <Input
                value={value("zip_code")}
                onChange={(v) => setDraft({ ...draft, zip_code: v })}
                left={<PinIcon className="h-[17px] w-[17px] text-ink3" />}
              />
            </Field>
          </div>
          <p className="rounded-[10px] border border-light bg-tint p-4 text-[12.5px] leading-[19px] text-ink2">
            A buyer is shown one of these only where they share it with you. Someone with nothing in
            common sees no badges and learns neither your country nor your school.
          </p>
        </Card>

        {/* Contact */}
        <Card className="flex flex-col gap-5 p-6 md:p-7">
          <SectionLabel>CONTACT</SectionLabel>
          <div className="flex items-center gap-3 rounded-[10px] border border-line bg-muted p-4">
            <div className="flex-1">
              <p className="text-[14px] font-semibold">{me.email}</p>
              <p className="text-[11.5px] text-ink3">Always the fallback — cannot be turned off</p>
            </div>
            <span className="rounded-full bg-surface px-2.5 py-1 text-[9.5px] font-semibold text-ink2">
              ALWAYS ON
            </span>
          </div>

          <Field
            label="Phone number"
            optional
            hint="Leave it blank and your listings simply show a single Email seller button. Nothing else changes."
          >
            <Input
              value={value("phone") ?? ""}
              onChange={(v) => setDraft({ ...draft, phone: v })}
              placeholder="+1 (646) 555-0142"
            />
          </Field>

          <div className="flex items-center gap-3.5 rounded-[10px] border border-line p-4">
            <div className="flex-1">
              <p className="text-[14px] font-semibold">Let buyers text me</p>
              <p className="text-[12px] text-ink2">
                Adds a Text seller button next to Email on every listing you post.
              </p>
            </div>
            <Toggle
              on={hasPhone && Boolean(value("phone_contact_enabled"))}
              onChange={(v) => setDraft({ ...draft, phone_contact_enabled: v })}
            />
          </div>
        </Card>

        {/* Feed defaults */}
        <Card className="flex flex-col gap-5 p-6 md:p-7">
          <SectionLabel>FEED DEFAULTS</SectionLabel>
          <Field label={`Distance radius — ${value("default_radius_mi")} miles`}>
            <input
              type="range"
              min={0.5}
              max={10}
              step={0.5}
              value={value("default_radius_mi")}
              onChange={(e) => setDraft({ ...draft, default_radius_mi: Number(e.target.value) })}
              className="w-full accent-[var(--color-deep)]"
            />
          </Field>
          {(
            [
              ["default_filter_same_zip", "Same ZIP code"],
              ["default_filter_same_nationality", "Same nationality"],
              ["default_filter_same_school", "Same college"],
            ] as const
          ).map(([key, label]) => (
            <div key={key} className="flex items-center gap-3.5 border-t border-line pt-4">
              <p className="flex-1 text-[14px] font-semibold">{label}</p>
              <Toggle on={Boolean(value(key))} onChange={(v) => setDraft({ ...draft, [key]: v })} />
            </div>
          ))}
          <p className="text-[12px] text-ink3">
            Where the sliders and toggles start each time you open the app — you can still move them
            per search.
          </p>
        </Card>

        {/* Save bar */}
        <Card className="flex items-center gap-3 p-5">
          <div className="flex-1">
            <p className="text-[13.5px] font-semibold">
              {changed.length === 0 ? "No unsaved changes" : `${changed.length} unsaved changes`}
            </p>
            {changed.length > 0 && <p className="text-[12px] text-ink2">{changed.join(" · ")}</p>}
          </div>
          <Button variant="ghost" onClick={() => setDraft({})} disabled={changed.length === 0}>
            Discard
          </Button>
          <Button onClick={save} disabled={changed.length === 0 || saving}>
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </Card>
      </main>

      <MobileTabBar />
    </>
  );
}
