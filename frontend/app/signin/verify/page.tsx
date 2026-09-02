"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { Logo } from "@/components/Logo";
import { Button, Card } from "@/components/ui";
import { api } from "@/lib/api";

/**
 * What the link does — UX_SPEC.md states B8, B9 and B10.
 *
 * Two of the three outcomes are failures, and both offer the same one-tap
 * recovery rather than an error page.
 */
export default function VerifyPage() {
  // useSearchParams needs a Suspense boundary to prerender.
  return (
    <Suspense fallback={<div className="p-10 text-ink2">Verifying…</div>}>
      <Verify />
    </Suspense>
  );
}

function Verify() {
  const params = useSearchParams();
  const router = useRouter();
  const [state, setState] = useState<"working" | "ok" | "expired" | "already_used" | "unknown">(
    "working",
  );

  useEffect(() => {
    const token = params.get("token");
    if (!token) return setState("unknown");
    api
      .verify(token)
      .then(() => {
        setState("ok");
        setTimeout(() => router.push("/"), 900);
      })
      .catch((e) => setState((e?.message as typeof state) ?? "unknown"));
  }, [params, router]);

  const copy = {
    working: ["Verifying…", ""],
    ok: ["You're verified", "Opening your feed."],
    expired: ["This link expired", "Links last 15 minutes. Nothing is wrong with your account."],
    already_used: [
      "This link was already used",
      "It signed in a device a few minutes ago. If that was not you, send a new link.",
    ],
    unknown: ["We could not read that link", "Send a fresh one and try again."],
  }[state];

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-5 p-6">
      <Logo />
      <Card className="flex flex-col gap-3 p-8">
        <h1 className="text-[22px] font-bold tracking-[-0.02em]">{copy[0]}</h1>
        {copy[1] && <p className="text-[14px] leading-6 text-ink2">{copy[1]}</p>}
        {state !== "ok" && state !== "working" && (
          <Button variant="ghost" onClick={() => router.push("/signin")}>
            Send a new link
          </Button>
        )}
      </Card>
    </main>
  );
}
