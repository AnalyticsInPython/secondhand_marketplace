"""Outbound email.

Three backends, chosen with MAIL_BACKEND so the whole auth flow is testable
without credentials:

    console  print the message to the terminal
    file     write a .eml into instance/outbox/ (default in dev -- you can open
             the file and click the invite link)
    smtp     really send it

Nothing else in the app knows which backend is live.
"""

import os
import re
import smtplib
from email.message import EmailMessage

from flask import current_app

from db import utcnow


def send(to, subject, body):
    backend = current_app.config["MAIL_BACKEND"]
    sender = current_app.config["MAIL_FROM"]

    if backend == "console":
        _send_console(sender, to, subject, body)
    elif backend == "file":
        _send_file(sender, to, subject, body)
    elif backend == "smtp":
        _send_smtp(sender, to, subject, body)
    else:
        raise ValueError(f"Unknown MAIL_BACKEND: {backend!r}")

    current_app.logger.info("mail[%s] -> %s: %s", backend, to, subject)


def _build(sender, to, subject, body):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def _send_console(sender, to, subject, body):
    print("\n" + "=" * 68)
    print(f"To:      {to}")
    print(f"Subject: {subject}")
    print("-" * 68)
    print(body)
    print("=" * 68 + "\n", flush=True)


def _send_file(sender, to, subject, body):
    outbox = os.path.join(current_app.instance_path, "outbox")
    os.makedirs(outbox, exist_ok=True)
    stamp = utcnow().replace(":", "-")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", to)[:40]
    path = os.path.join(outbox, f"{stamp}__{slug}.eml")
    with open(path, "w", encoding="utf-8") as f:
        f.write(_build(sender, to, subject, body).as_string())
    # Also echo it, so you never have to go hunting for the code during a demo.
    _send_console(sender, to, subject, body)


def _send_smtp(sender, to, subject, body):
    cfg = current_app.config
    msg = _build(sender, to, subject, body)
    with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=15) as smtp:
        if cfg["SMTP_USE_TLS"]:
            smtp.starttls()
        if cfg["SMTP_USER"]:
            smtp.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
        smtp.send_message(msg)
