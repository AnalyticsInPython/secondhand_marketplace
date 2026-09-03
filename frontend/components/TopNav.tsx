"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { api, ApiError } from "@/lib/api";
import type { Me, ZipResult } from "@/lib/types";
import { Logo } from "./Logo";
import { ChevronIcon, PinIcon, PlusIcon, SearchIcon } from "./ui";


/**
 * The avatar menu — UX_SPEC.md §6.6: "My listings / Saved items / Inbox /
 * Profile & account / Sign out".
 *
 * A menu rather than a straight link to the profile, because those three
 * collections have no other entry point on desktop; on mobile they are reached
 * from the tab bar instead.
 */
const MENU = [
  { href: "/my-listings", label: "My listings" },
  { href: "/saved", label: "Saved items" },
  { href: "/inbox", label: "Inbox" },
  { href: "/settings/profile", label: "Profile & account" },
];

function AvatarMenu({ me }: { me: Me | null }) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Close on an outside click or Escape — a menu you cannot dismiss with the
  // keyboard is a trap for anyone not using a mouse.
  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  async function signOut() {
    await api.signout().catch(() => undefined);
    router.push("/signin");
  }

  return (
    <div className="relative" ref={box}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label="Account menu"
        className="flex h-[42px] w-[42px] items-center justify-center rounded-full bg-light text-[14px] font-bold text-deep"
      >
        {(me?.username ?? "cu").slice(0, 2).toUpperCase()}
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 top-[52px] z-30 w-[230px] overflow-hidden rounded-[12px] border border-line bg-surface py-1.5 shadow-[0_6px_24px_rgba(13,31,64,0.12)]"
        >
          {me && (
            <div className="border-b border-line px-4 pb-2.5 pt-1.5">
              <p className="truncate text-[14px] font-bold">@{me.username}</p>
              <p className="truncate text-[12px] text-ink2">{me.email}</p>
            </div>
          )}
          {MENU.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              role="menuitem"
              onClick={() => setOpen(false)}
              className="block px-4 py-2.5 text-[14px] text-ink hover:bg-muted"
            >
              {item.label}
            </Link>
          ))}
          <button
            type="button"
            role="menuitem"
            onClick={signOut}
            className="block w-full border-t border-line px-4 py-2.5 text-left text-[14px] text-danger hover:bg-muted"
          >
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * The location chip, which is also how you move.
 *
 * Changing ZIP lives in Profile & account too, and stays there — that is where
 * you go to edit your profile deliberately. But the ZIP is the origin every
 * distance on the feed is measured from, so trying a different one is a
 * browsing action, not a settings one. Four clicks into a settings page is the
 * wrong price for it.
 */
function ZipPicker({ me, onChange }: { me: Me | null; onChange?: (me: Me) => void }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState<ZipResult[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const box = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (box.current && !box.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  // Same autocomplete the sign-up screen uses (§6.1): three digits is enough to
  // narrow the metro list, and each row shows how far it is from campus.
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => {
      api
        .zips(q)
        .then(setResults)
        .catch(() => setResults([]));
    }, 200);
    return () => clearTimeout(t);
  }, [q, open]);

  async function choose(zip: string) {
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateMe({ zip_code: zip });
      setOpen(false);
      setQ("");
      // Distances and the facet counts are computed from the viewer's ZIP on
      // the server, so the page has to ask again rather than patch in place.
      if (onChange) onChange(updated);
      else window.location.reload();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not change your ZIP code.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="relative" ref={box}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={`Location ${me?.zip_code ?? ""}. Change ZIP code`}
        title="Change ZIP code"
        className="flex items-center gap-1.5 rounded-[9px] border border-line bg-surface px-3 py-2 text-[13px] font-semibold text-deep transition-colors hover:border-light hover:bg-tint"
      >
        <PinIcon className="h-[15px] w-[15px]" />
        {me?.zip_code ?? "10027"}
        <ChevronIcon className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`} />
      </button>

      {open && (
        <div className="absolute left-0 top-[calc(100%+8px)] z-30 w-[320px] overflow-hidden rounded-[12px] border border-line bg-surface shadow-[var(--shadow-pop)]">
          <div className="border-b border-line px-4 py-3">
            <p className="text-[13px] font-bold">Change your ZIP code</p>
            <p className="mt-0.5 text-[11.5px] leading-[16px] text-ink3">
              Every distance on the feed is measured from here. This updates your profile.
            </p>
          </div>

          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value.replace(/\D/g, "").slice(0, 5))}
            inputMode="numeric"
            placeholder="Type a ZIP — 100…"
            className="w-full border-b border-line px-4 py-2.5 text-[14px] outline-none placeholder:text-ink3"
          />

          {error && (
            <p className="border-b border-line bg-page px-4 py-2.5 text-[12.5px] text-danger">{error}</p>
          )}

          <div className="max-h-[260px] overflow-y-auto">
            {results.length === 0 ? (
              <p className="px-4 py-4 text-[12.5px] text-ink3">
                No New York metro ZIP matches that. The pilot is NYC-only.
              </p>
            ) : (
              results.map((z) => (
                <button
                  key={z.zip_code}
                  type="button"
                  disabled={saving}
                  onClick={() => void choose(z.zip_code)}
                  className={`flex w-full items-baseline gap-2 px-4 py-2.5 text-left transition-colors hover:bg-muted disabled:opacity-50 ${
                    z.zip_code === me?.zip_code ? "bg-tint" : ""
                  }`}
                >
                  <span className="text-[13.5px] font-semibold text-ink">{z.zip_code}</span>
                  <span className="flex-1 truncate text-[12.5px] text-ink2">{z.neighbourhood}</span>
                  {z.miles_from_campus !== null && (
                    <span className="text-[11.5px] text-ink3">{z.miles_from_campus} mi</span>
                  )}
                </button>
              ))
            )}
          </div>

          <Link
            href="/settings/profile"
            onClick={() => setOpen(false)}
            className="block border-t border-line px-4 py-2.5 text-[12.5px] font-semibold text-deep hover:bg-muted"
          >
            Edit the rest of your profile
          </Link>
        </div>
      )}
    </div>
  );
}

/**
 * Desktop top bar — UX_SPEC.md §6.3.
 *
 * The location chip shows the ZIP and nothing else. Mileage belongs to the
 * distance slider (a filter you set) and to each card (a real distance to that
 * item); on the chip it reads as neither.
 */
export function TopNav({
  me,
  query,
  onQuery,
  onZipChange,
}: {
  me: Me | null;
  query?: string;
  onQuery?: (v: string) => void;
  onZipChange?: (me: Me) => void;
}) {
  return (
    <header className="sticky top-0 z-20 hidden border-b border-line bg-surface md:block">
      <div className="mx-auto flex h-[76px] max-w-[1360px] items-center gap-7 px-10">
        <Link href="/">
          <Logo />
        </Link>

        <div className="flex h-12 flex-1 items-center rounded-[12px] border border-line bg-muted px-1.5">
          <ZipPicker me={me} onChange={onZipChange} />
          <input
            value={query ?? ""}
            onChange={(e) => onQuery?.(e.target.value)}
            placeholder="Search desks, textbooks, winter coats…"
            className="mx-3 flex-1 bg-transparent text-[14px] text-ink outline-none placeholder:text-ink3"
          />
          <span className="flex h-[38px] w-[38px] items-center justify-center rounded-[9px] bg-deep text-white">
            <SearchIcon />
          </span>
        </div>

        <Link
          href="/sell"
          className="flex items-center gap-1.5 rounded-[10px] bg-deep px-4 py-3 text-[14px] font-semibold text-white"
        >
          <PlusIcon />
          Sell an item
        </Link>

        <AvatarMenu me={me} />
      </div>
    </header>
  );
}

/** Mobile bottom tabs. `Inbox`, not `Chats` — there is no in-app chat. */
export function MobileTabBar() {
  const path = usePathname();
  const tabs = [
    { href: "/", label: "Home" },
    { href: "/search", label: "Search" },
    { href: "/sell", label: "Sell" },
    { href: "/inbox", label: "Inbox" },
    { href: "/settings/profile", label: "My page" },
  ];

  return (
    <nav className="fixed inset-x-0 bottom-0 z-20 flex border-t border-line bg-surface px-2 pb-2 pt-2.5 md:hidden">
      {tabs.map((t) => {
        const active = path === t.href;
        const isSell = t.href === "/sell";
        return (
          <Link key={t.href} href={t.href} className="flex flex-1 flex-col items-center gap-1">
            {isSell ? (
              <span className="flex h-[46px] w-[46px] items-center justify-center rounded-full bg-deep text-white">
                <PlusIcon className="h-5 w-5" />
              </span>
            ) : (
              <span
                className={`h-[23px] w-[23px] rounded-md ${active ? "bg-deep" : "bg-line-strong"}`}
              />
            )}
            <span
              className={`text-[10.5px] ${
                active || isSell ? "font-semibold text-deep" : "font-medium text-ink3"
              }`}
            >
              {t.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
