"use client";

import { useEffect, useState } from "react";

import { Logo } from "@/components/Logo";
import { Button, Card, Field, Input, MailIcon, ShieldIcon } from "@/components/ui";
import { api } from "@/lib/api";

/**
 * Sign in — UX_SPEC.md §6.2. There is no password anywhere in this product.
 *
 * States B1–B7 live here; B8–B10 (what the link does) live in /signin/verify.
 */
export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState<string | null>(null);
  const [wait, setWait] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const valid = /^[^@]+@columbia\.edu$/i.test(email);

  // Resend stays locked for a minute — long enough for the first mail to
  // arrive, short enough that a stuck user is not stranded.
  useEffect(() => {
    if (wait <= 0) return;
    const t = setTimeout(() => setWait((w) => w - 1), 1000);
    return () => clearTimeout(t);
  }, [wait]);

  async function send() {
    setError(null);
    try {
      const res = await api.requestLink(email);
      setSent(res.sent);
      setDevLink(res.dev_link);
      setWait(res.resend_available_in_seconds);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    }
  }

  return (
    <main className="min-h-screen">
      <div className="flex flex-col items-center bg-deep px-6 pb-11 pt-9">
        <Logo inverse />
      </div>

      <div className="mx-auto flex max-w-[520px] flex-col gap-6 p-6 md:py-14">
        <Card className="flex flex-col gap-6 p-8 md:p-12">
          <div className="flex flex-col gap-2.5">
            <h1 className="text-[30px] font-bold tracking-[-0.02em]">Welcome back</h1>
            <p className="text-[15px] leading-6 text-ink2">
              Sign in with your Columbia email. We send a one-time link — there is no password to
              forget.
            </p>
          </div>

          <Field
            label="Columbia email"
            error={email && !valid ? "Columbia Market is @columbia.edu only." : undefined}
          >
            <Input
              value={email}
              onChange={setEmail}
              type="email"
              placeholder="you@columbia.edu"
              state={!email ? "default" : valid ? "ok" : "error"}
              left={<MailIcon className="h-[17px] w-[17px] text-deep" />}
              right={valid ? <ShieldIcon className="h-4 w-4 text-ok" /> : undefined}
            />
          </Field>

          {sent ? (
            <div className="flex flex-col gap-3 rounded-[12px] border border-light bg-tint p-5">
              <p className="text-[16px] font-bold text-deep">Check your Columbia inbox</p>
              <p className="text-[12.5px] leading-[19px] text-ink2">
                The link works once and expires in 15 minutes.
              </p>
              {devLink && (
                <a href={devLink} className="break-all text-[12px] font-semibold text-deep">
                  {devLink}
                </a>
              )}
              <Button variant="ghost" disabled={wait > 0} onClick={send}>
                {wait > 0 ? `Resend available in 0:${String(wait).padStart(2, "0")}` : "Resend the link"}
              </Button>
            </div>
          ) : (
            <Button full disabled={!valid} onClick={send}>
              Email me a sign-in link
            </Button>
          )}

          {error && <p className="text-[13px] text-danger">{error}</p>}

          <p className="text-center text-[14px] text-ink2">
            New to Columbia Market?{" "}
            <a href="/signup" className="font-semibold text-deep">
              Create an account
            </a>
          </p>
        </Card>
      </div>
    </main>
  );
}
