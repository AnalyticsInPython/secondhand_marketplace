/**
 * Which addresses may sign in. Mirrors ALLOWED_EMAIL_DOMAINS on the API
 * (backend/.env) — the API is the gate; this list only gives instant feedback
 * while the student is still typing. Keep the two in step (docs/DECISIONS.md).
 */

export const ALLOWED_EMAIL_DOMAINS = [
  "columbia.edu",
  "gsb.columbia.edu",
  "cumc.columbia.edu",
  "tc.columbia.edu",
];

export function emailDomain(email: string): string | null {
  const trimmed = email.trim().toLowerCase();
  const at = trimmed.indexOf("@");
  if (at <= 0 || at !== trimmed.lastIndexOf("@")) return null;
  const domain = trimmed.slice(at + 1);
  return domain.length > 0 ? domain : null;
}

export function isAllowedEmail(email: string): boolean {
  const domain = emailDomain(email);
  return domain !== null && ALLOWED_EMAIL_DOMAINS.includes(domain);
}

export const DOMAIN_ERROR = "Columbia addresses only — columbia.edu, gsb, cumc or tc.";
