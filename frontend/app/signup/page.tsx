"use client";

import { useEffect, useState } from "react";

import { Logo } from "@/components/Logo";
import { Button, Field, Input, MailIcon, PinIcon, Segmented, Select, ShieldIcon } from "@/components/ui";
import { api } from "@/lib/api";
import { DOMAIN_ERROR, isAllowedEmail } from "@/lib/domains";
import type { Country, EnumsRef, Grade, ZipResult } from "@/lib/types";

/**
 * Sign up — UX_SPEC.md §6.1. One screen, no wizard.
 *
 * Validation is inline and immediate: nothing is checked only on submit, and
 * the button stays disabled until every required field resolves, saying what is
 * still missing. The four matching attributes are fixed pickers, never free
 * text — that is what keeps the filters honest.
 */
export default function SignUpPage() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [phone, setPhone] = useState(""); // optional (§5.1)
  const [nationality, setNationality] = useState("");
  const [school, setSchool] = useState("");
  const [schoolTouched, setSchoolTouched] = useState(false);
  const [grade, setGrade] = useState<Grade>("graduate");
  const [zip, setZip] = useState("");
  const [zipResults, setZipResults] = useState<ZipResult[]>([]);
  const [zipPicked, setZipPicked] = useState<ZipResult | null>(null);
  const [usernameState, setUsernameState] = useState<"idle" | "checking" | "taken" | "ok">("idle");
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [countries, setCountries] = useState<Country[]>([]);
  const [enums, setEnums] = useState<EnumsRef | null>(null);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const emailValid = isAllowedEmail(email);

  useEffect(() => {
    api.countries().then(setCountries).catch(() => setCountries([]));
    api.enums().then(setEnums).catch(() => setEnums(null));
  }, []);

  // A gsb or tc address proves the school; prefill it, leave it editable (A2/A3).
  useEffect(() => {
    if (!emailValid) return;
    const t = setTimeout(() => {
      api
        .emailCheck(email)
        .then((r) => {
          if (r.suggested_school && !schoolTouched) setSchool(r.suggested_school);
        })
        .catch(() => {});
    }, 400);
    return () => clearTimeout(t);
  }, [email, emailValid, schoolTouched]);

  // Live availability, as the design shows — states A4–A6.
  useEffect(() => {
    if (username.replace(/^@/, "").length < 3) return setUsernameState("idle");
    setUsernameState("checking");
    const t = setTimeout(() => {
      api
        .usernameAvailable(username)
        .then((r) => {
          setUsernameState(r.available ? "ok" : "taken");
          setSuggestions(r.suggestions);
        })
        .catch(() => setUsernameState("idle"));
    }, 350);
    return () => clearTimeout(t);
  }, [username]);

  // ZIP autocomplete — state A7.
  useEffect(() => {
    if (zip.length < 2) return setZipResults([]);
    api.zips(zip).then(setZipResults).catch(() => setZipResults([]));
  }, [zip]);

  const missing = [
    !emailValid && "Columbia email",
    usernameState !== "ok" && "username",
    !nationality && "nationality",
    !school && "college",
    !zipPicked && "ZIP code",
  ].filter(Boolean) as string[];

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      const res = await api.signup({
        email: email.trim(),
        username,
        phone: phone || null,
        nationality,
        school,
        grade,
        zip_code: zipPicked!.zip_code,
      });
      setSent(res.dev_link ?? "sent");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  if (sent) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-4 p-6">
        <Logo />
        <h1 className="text-[28px] font-bold tracking-[-0.02em]">Check your Columbia inbox</h1>
        <p className="text-[15px] leading-6 text-ink2">
          We sent a sign-in link to {email.trim()}. It works once and expires in 15 minutes.
        </p>
        {sent !== "sent" && (
          <div className="flex flex-col gap-1 rounded-[10px] border border-dashed border-light bg-tint p-3">
            <p className="text-[10.5px] font-semibold tracking-[0.06em] text-ink3">
              DEVELOPMENT MODE · THE LINK WE WOULD HAVE EMAILED
            </p>
            <a href={sent} className="break-all text-[13px] font-semibold text-deep">
              Open the sign-in link
            </a>
          </div>
        )}
      </main>
    );
  }

  const pinned = countries.filter((c) => c.pinned);
  const rest = countries.filter((c) => !c.pinned);

  return (
    <main className="flex min-h-screen flex-col md:flex-row">
      {/* Brand panel */}
      <section className="flex flex-col justify-between bg-deep p-8 md:w-[560px] md:p-16">
        <Logo inverse />
        <div className="hidden flex-col gap-5 md:flex">
          <h1 className="text-[46px] font-bold leading-[54px] tracking-[-0.02em] text-white">
            Sell it to someone
            <br />
            who gets it.
          </h1>
          <p className="max-w-[400px] text-[16px] leading-[27px] text-light">
            The marketplace only Columbia students can enter. Filter by ZIP code, distance, country,
            school and year — and trade with people you already have something in common with.
          </p>
        </div>
        <p className="hidden text-[12px] text-light/70 md:block">ENGI 4503 · Analytics in Python</p>
      </section>

      {/* Form */}
      <section className="flex flex-1 items-start justify-center p-6 md:p-16">
        <div className="flex w-full max-w-[640px] flex-col gap-6 rounded-[20px] border border-line bg-surface p-6 md:p-11">
          <div className="flex flex-col gap-2">
            <h2 className="text-[32px] font-bold tracking-[-0.02em]">Create your account</h2>
            <p className="text-[15px] leading-6 text-ink2">
              One screen, one minute. Everything below shapes what you see in the feed.
            </p>
          </div>

          <Field
            label="Columbia email"
            hint="columbia.edu, gsb, cumc or tc addresses. We send a verification link — no password to remember."
            error={email && !emailValid ? DOMAIN_ERROR : undefined}
          >
            <Input
              value={email}
              onChange={setEmail}
              placeholder="uni1234@columbia.edu"
              type="email"
              state={!email ? "default" : emailValid ? "ok" : "error"}
              left={<MailIcon className="h-[17px] w-[17px] text-ink3" />}
              right={emailValid ? <ShieldIcon className="h-4 w-4 text-ok" /> : undefined}
            />
          </Field>

          <div className="grid gap-5 md:grid-cols-2">
            <Field
              label="Username"
              error={usernameState === "taken" ? `Taken. Try ${suggestions.join(", ")}` : undefined}
              hint={usernameState === "ok" ? "Available." : "3–20 letters, numbers, dots or underscores."}
            >
              <Input
                value={username}
                onChange={setUsername}
                placeholder="@yourname"
                state={usernameState === "taken" ? "error" : usernameState === "ok" ? "ok" : "default"}
              />
            </Field>

            {/* Optional. Blank means listings show a single Email button (§5.1). */}
            <Field label="Phone number" optional hint="Only if you want buyers to text you. Email always works.">
              <Input value={phone} onChange={setPhone} placeholder="+1 (646) 555-0142" type="tel" />
            </Field>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            <Field label="Nationality">
              <Select value={nationality} onChange={setNationality} placeholder="Choose a country">
                {pinned.length > 0 && (
                  <optgroup label="Most common at Columbia">
                    {pinned.map((c) => (
                      <option key={c.code} value={c.code}>
                        {c.name}
                      </option>
                    ))}
                  </optgroup>
                )}
                <optgroup label="All countries">
                  {rest.map((c) => (
                    <option key={c.code} value={c.code}>
                      {c.name}
                    </option>
                  ))}
                </optgroup>
              </Select>
            </Field>
            <Field label="College / School">
              <Select
                value={school}
                onChange={(v) => {
                  setSchoolTouched(true);
                  setSchool(v);
                }}
                placeholder="Choose your school"
              >
                <optgroup label="Undergraduate">
                  {enums?.schools.undergraduate.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Graduate & professional">
                  {enums?.schools.graduate.map((s) => (
                    <option key={s.value} value={s.value}>
                      {s.label}
                    </option>
                  ))}
                </optgroup>
              </Select>
            </Field>
          </div>

          <Field label="Grade">
            <Segmented<Grade>
              value={grade}
              onChange={setGrade}
              options={[
                { value: "undergraduate", label: "Undergraduate" },
                { value: "graduate", label: "Graduate" },
                { value: "faculty_staff", label: "Faculty / Staff" },
              ]}
            />
          </Field>

          <Field
            label="ZIP code"
            hint="Your ZIP is the centre of your feed. Everything else is sorted by how many miles away it is."
          >
            <Input
              value={zipPicked ? `${zipPicked.zip_code} — ${zipPicked.neighbourhood}` : zip}
              onChange={(v) => {
                setZipPicked(null);
                setZip(v);
              }}
              placeholder="10027"
              state={zipPicked ? "ok" : "default"}
              left={<PinIcon className="h-[17px] w-[17px] text-ink3" />}
            />
          </Field>

          {!zipPicked && zip.length >= 2 && zipResults.length === 0 && (
            <p className="-mt-3 text-[12px] text-danger">
              {zip} is not in the New York metro area. Columbia Market is NYC-only during the pilot.
            </p>
          )}

          {!zipPicked && zipResults.length > 0 && (
            <ul className="-mt-3 overflow-hidden rounded-[12px] border border-line bg-surface">
              {zipResults.map((z) => (
                <li key={z.zip_code}>
                  <button
                    type="button"
                    onClick={() => setZipPicked(z)}
                    className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-muted"
                  >
                    <PinIcon className="h-4 w-4 text-ink3" />
                    <span className="flex-1">
                      <span className="block text-[14px] font-medium">
                        {z.zip_code} — {z.neighbourhood}
                      </span>
                      <span className="block text-[11.5px] text-ink2">{z.borough}</span>
                    </span>
                    <span className="text-[11.5px] text-ink3">{z.miles_from_campus} mi from campus</span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {error && <p className="text-[13px] text-danger">{error}</p>}

          <Button full disabled={missing.length > 0 || busy} onClick={submit}>
            {busy ? "Creating…" : "Create account"}
          </Button>
          {missing.length > 0 && (
            <p className="-mt-3 text-center text-[12px] text-ink3">
              {missing.length} required {missing.length === 1 ? "field" : "fields"} left —{" "}
              {missing.join(", ")}.
            </p>
          )}

          <p className="text-center text-[14px] text-ink2">
            Already a member?{" "}
            <a href="/signin" className="font-semibold text-deep">
              Sign in
            </a>
          </p>
        </div>
      </section>
    </main>
  );
}
