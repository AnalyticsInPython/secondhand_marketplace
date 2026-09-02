"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import type { Me } from "@/lib/types";
import { Logo } from "./Logo";
import { PinIcon, PlusIcon, SearchIcon } from "./ui";

/**
 * Desktop top bar — UX_SPEC.md §6.3.
 *
 * The location chip shows the ZIP and nothing else. Mileage belongs to the
 * distance slider (a filter you set) and to each card (a real distance to that
 * item); on the chip it reads as neither.
 */
export function TopNav({ me, query, onQuery }: { me: Me | null; query?: string; onQuery?: (v: string) => void }) {
  return (
    <header className="sticky top-0 z-20 hidden border-b border-line bg-surface md:block">
      <div className="mx-auto flex h-[76px] max-w-[1360px] items-center gap-7 px-10">
        <Link href="/">
          <Logo />
        </Link>

        <div className="flex h-12 flex-1 items-center rounded-[12px] border border-line bg-muted px-1.5">
          <span className="flex items-center gap-1.5 rounded-[9px] border border-line bg-surface px-3 py-2 text-[13px] font-semibold text-deep">
            <PinIcon className="h-[15px] w-[15px]" />
            {me?.zip_code ?? "10027"}
          </span>
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

        <Link
          href="/settings/profile"
          className="flex h-[42px] w-[42px] items-center justify-center rounded-full bg-light text-[14px] font-bold text-deep"
          aria-label="Profile & account"
        >
          {(me?.username ?? "cu").slice(0, 2).toUpperCase()}
        </Link>
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
