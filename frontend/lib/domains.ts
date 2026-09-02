/**
 * Which email addresses may register.
 *
 * The API is authoritative — `backend/app/emails.py` enforces the gate, and
 * `/reference/enums` returns the same list under `email_domains`. This copy
 * exists only so sign-up and sign-in can validate as you type, before any
 * network call (UX_SPEC.md §6.1 asks for inline validation, not on submit).
 * Keep the two in step.
 *
 * Matching is on the whole domain. A suffix test would reject
 * `@gsb.columbia.edu` against a bare `columbia.edu`, which is the bug this
 * replaced.
 */

export const ALLOWED_EMAIL_DOMAINS = [
  "columbia.edu",
  "gsb.columbia.edu",
  "cumc.columbia.edu",
  "tc.columbia.edu",
] as const;

/** `@a, @b, @c` — for hints and error copy. */
export const EMAIL_DOMAIN_LIST = ALLOWED_EMAIL_DOMAINS.map((d) => `@${d}`).join(", ");

/** Mirrors `emails.rejection_message()` on the API. */
export const EMAIL_REJECTION = `Columbia Market is open to ${EMAIL_DOMAIN_LIST} addresses.`;

export function isColumbiaEmail(email: string): boolean {
  const parts = email.trim().toLowerCase().split("@");
  if (parts.length !== 2 || !parts[0]) return false;
  return (ALLOWED_EMAIL_DOMAINS as readonly string[]).includes(parts[1]);
}
