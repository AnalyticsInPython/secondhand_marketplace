"""Sending the sign-in link — UX_SPEC.md §6.2.

Three backends, chosen by EMAIL_BACKEND:

    console   print the link to the server log (default; local development)
    resend    Resend's HTTP API — RESEND_API_KEY, EMAIL_FROM
    smtp      any SMTP relay — SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD

Nothing else in the sign-in flow knows which one is in use.
"""

from __future__ import annotations

import json
import smtplib
import urllib.error
import urllib.request
from email.message import EmailMessage
from html import escape

from ..config import settings


class MailError(RuntimeError):
    """The message could not be handed to the provider."""


def _render(*, to: str, link: str, username: str | None) -> tuple[str, str, str]:
    greeting = f"Hi @{username} —" if username else "Hi —"
    subject = "Sign in to Columbia Market"
    text = (
        f"{greeting} tap the link below to sign in as {to}. "
        "If you did not request this, you can ignore this email.\n\n"
        f"{link}\n\n"
        f"The link works once and expires in {settings.login_token_ttl_minutes} minutes.\n"
        "Columbia Market · Columbia University, New York, NY\n"
    )
    html = f"""\
<!doctype html>
<html><body style="margin:0;background:#f7fafc;font-family:Inter,-apple-system,Segoe UI,sans-serif;color:#111827">
  <div style="max-width:560px;margin:0 auto;padding:32px 24px">
    <div style="font-size:19px;font-weight:700;color:#1d4f91;margin-bottom:24px">Columbia Market</div>
    <div style="background:#fff;border:1px solid #e2e8f0;border-radius:16px;padding:32px">
      <h1 style="font-size:22px;margin:0 0 12px">Sign in to Columbia Market</h1>
      <p style="font-size:15px;line-height:23px;color:#64748b;margin:0 0 24px">
        {escape(greeting)} tap the button below to sign in as <b>{escape(to)}</b>.
        If you did not request this, you can ignore this email.
      </p>
      <a href="{escape(link)}" style="display:inline-block;background:#1d4f91;color:#fff;text-decoration:none;font-weight:600;font-size:15px;padding:14px 22px;border-radius:12px">Verify my Columbia email</a>
      <p style="font-size:12px;color:#94a3b8;margin:24px 0 0">
        Link expires in {settings.login_token_ttl_minutes} minutes · Columbia University, New York, NY
      </p>
    </div>
  </div>
</body></html>
"""
    return subject, text, html


def send_login_link(*, to: str, link: str, username: str | None = None) -> None:
    subject, text, html = _render(to=to, link=link, username=username)
    backend = settings.email_backend.lower()

    if backend == "console":
        print(f"[mail] sign-in link for {to}: {link}", flush=True)
        return

    if backend == "resend":
        if not settings.resend_api_key:
            raise MailError("EMAIL_BACKEND=resend but RESEND_API_KEY is empty")
        body = json.dumps(
            {"from": settings.email_from, "to": [to], "subject": subject, "html": html, "text": text}
        ).encode()
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310 (fixed host)
                if resp.status >= 300:
                    raise MailError(f"Resend answered {resp.status}")
        except urllib.error.URLError as exc:
            raise MailError(f"Resend request failed: {exc}") from exc
        return

    if backend == "smtp":
        if not settings.smtp_host:
            raise MailError("EMAIL_BACKEND=smtp but SMTP_HOST is empty")
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to
        msg.set_content(text)
        msg.add_alternative(html, subtype="html")
        try:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as smtp:
                if settings.smtp_starttls:
                    smtp.starttls()
                if settings.smtp_username:
                    smtp.login(settings.smtp_username, settings.smtp_password)
                smtp.send_message(msg)
        except (smtplib.SMTPException, OSError) as exc:
            raise MailError(f"SMTP send failed: {exc}") from exc
        return

    raise MailError(f"Unknown EMAIL_BACKEND {settings.email_backend!r}")
