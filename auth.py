"""The Columbia-email gate.

The whole entry flow lives here. One screen asks for an email address; where it
goes next depends entirely on whether we have seen that address before.

    NEW address       -> create a pending user, email a signed invitation link,
                         and collect the affiliation attributes when they click it.
    KNOWN + active    -> email a 6-digit one-time passcode and verify it.

Both branches end in the same place: a logged-in session, then /home.

Security notes for the team:
  * OTPs and invite tokens are hashed before they touch the database, so a dump
    of marketplace.db cannot be replayed.
  * OTP comparison is constant-time; attempts are capped; codes expire.
  * The gate deliberately tells the visitor which branch they are on. That is a
    user-enumeration leak, and it is a conscious trade -- see WORKFLOW.md.
"""

import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint, current_app, flash, g, redirect, render_template, request,
    session, url_for,
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

import mailer
from db import get_db, log_event, utcnow

bp = Blueprint("auth", __name__)

# --- Policy knobs. Change these here, nowhere else. ------------------------

OTP_LENGTH = 6
OTP_TTL = timedelta(minutes=10)
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_COOLDOWN = timedelta(seconds=60)
INVITE_TTL = timedelta(days=7)

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

# Which school an email domain proves. Drives the `school` attribute, which is
# the one of the four the proposal says is verified rather than self-declared.
DOMAIN_TO_SCHOOL = {
    "columbia.edu": "Columbia University",
    "gsb.columbia.edu": "Columbia Business School",
    "cumc.columbia.edu": "Columbia University Irving Medical Center",
    "tc.columbia.edu": "Teachers College",
}


# --- Small helpers ---------------------------------------------------------

def _now():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def _parse(ts):
    return datetime.fromisoformat(ts)


def _hash(value):
    """Keyed hash, so a stolen database row is not a usable credential."""
    key = current_app.config["SECRET_KEY"].encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def _serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="invite")


def normalize_email(raw):
    return (raw or "").strip().lower()


def domain_of(email):
    return email.rsplit("@", 1)[-1] if "@" in email else ""


def validate_email(email):
    """Return an error string, or None when the address is acceptable."""
    if not email:
        return "Enter your Columbia email address."
    if not EMAIL_RE.match(email):
        return "That does not look like a valid email address."
    if domain_of(email) not in current_app.config["ALLOWED_EMAIL_DOMAINS"]:
        allowed = ", ".join("@" + d for d in current_app.config["ALLOWED_EMAIL_DOMAINS"])
        return f"MarketPlace is Columbia-only for now. Use an address at {allowed}."
    return None


def client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr or "")


# --- CSRF ------------------------------------------------------------------

def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def csrf_ok():
    sent = request.form.get("_csrf", "")
    known = session.get("_csrf", "")
    return bool(known) and hmac.compare_digest(sent, known)


# --- Session ---------------------------------------------------------------

def login(user_id):
    session.clear()
    session["user_id"] = user_id
    session.permanent = True
    get_db().execute(
        "UPDATE users SET last_login_at = ? WHERE id = ?", (utcnow(), user_id)
    )
    get_db().commit()


def current_user():
    if "user" not in g:
        uid = session.get("user_id")
        g.user = None
        if uid is not None:
            g.user = get_db().execute(
                "SELECT * FROM users WHERE id = ?", (uid,)
            ).fetchone()
    return g.user


def login_required(view):
    """Guard for every page behind the gate."""
    from functools import wraps

    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect(url_for("auth.gate"))
        if user["status"] == "pending":
            return redirect(url_for("auth.onboarding"))
        return view(*args, **kwargs)

    return wrapped


# --- Branch 1: invitation (new user) ---------------------------------------

def issue_invite(user):
    """Mint a signed, single-use invitation link and email it."""
    token = _serializer().dumps({"uid": user["id"], "email": user["email"]})
    db = get_db()
    db.execute(
        "INSERT INTO invites (user_id, token_hash, expires_at, created_at)"
        " VALUES (?, ?, ?, ?)",
        (user["id"], _hash(token), _iso(_now() + INVITE_TTL), utcnow()),
    )
    db.commit()

    link = url_for("auth.accept_invite", token=token, _external=True)
    mailer.send(
        user["email"],
        "Your MarketPlace invitation",
        "You're invited to MarketPlace, the Columbia-only marketplace.\n\n"
        "Finish setting up your account here:\n\n"
        f"{link}\n\n"
        f"This link works once and expires in {INVITE_TTL.days} days.\n"
        "If you did not request this, you can ignore this email.\n",
    )
    log_event("invite_sent", email=user["email"], user_id=user["id"], ip=client_ip())


# --- Branch 2: OTP (returning user) ----------------------------------------

def issue_otp(user):
    """Mint a 6-digit code and email it. Returns False if still cooling down."""
    db = get_db()
    last = db.execute(
        "SELECT created_at FROM otp_codes WHERE user_id = ?"
        " ORDER BY id DESC LIMIT 1",
        (user["id"],),
    ).fetchone()
    if last and _parse(last["created_at"]) + OTP_RESEND_COOLDOWN > _now():
        return False

    code = "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))
    # Any older code for this user is dead the moment a new one is issued.
    db.execute(
        "UPDATE otp_codes SET consumed_at = ?"
        " WHERE user_id = ? AND consumed_at IS NULL",
        (utcnow(), user["id"]),
    )
    db.execute(
        "INSERT INTO otp_codes (user_id, code_hash, expires_at, created_at)"
        " VALUES (?, ?, ?, ?)",
        (user["id"], _hash(code), _iso(_now() + OTP_TTL), utcnow()),
    )
    db.commit()

    minutes = int(OTP_TTL.total_seconds() // 60)
    mailer.send(
        user["email"],
        f"{code} is your MarketPlace code",
        f"Your MarketPlace sign-in code is:\n\n    {code}\n\n"
        f"It expires in {minutes} minutes and can be used once.\n"
        "If you did not try to sign in, ignore this email.\n",
    )
    log_event("otp_sent", email=user["email"], user_id=user["id"], ip=client_ip())
    return True


def check_otp(user, submitted):
    """Return (ok, message). Consumes the code on success."""
    db = get_db()
    row = db.execute(
        "SELECT * FROM otp_codes WHERE user_id = ? AND consumed_at IS NULL"
        " ORDER BY id DESC LIMIT 1",
        (user["id"],),
    ).fetchone()

    if row is None:
        return False, "That code is no longer valid. Request a new one."
    if _parse(row["expires_at"]) < _now():
        return False, "That code has expired. Request a new one."
    if row["attempts"] >= OTP_MAX_ATTEMPTS:
        return False, "Too many attempts. Request a new code."

    db.execute(
        "UPDATE otp_codes SET attempts = attempts + 1 WHERE id = ?", (row["id"],)
    )
    db.commit()

    submitted = re.sub(r"\D", "", submitted or "")
    if not hmac.compare_digest(_hash(submitted), row["code_hash"]):
        left = OTP_MAX_ATTEMPTS - (row["attempts"] + 1)
        log_event("otp_failed", user_id=user["id"], email=user["email"], ip=client_ip())
        if left <= 0:
            return False, "Too many attempts. Request a new code."
        return False, f"That code is not right. {left} attempt(s) left."

    db.execute(
        "UPDATE otp_codes SET consumed_at = ? WHERE id = ?", (utcnow(), row["id"])
    )
    db.commit()
    return True, ""


# --- Routes ----------------------------------------------------------------

@bp.route("/", methods=("GET", "POST"))
def gate():
    """Screen 1. The only door into the application."""
    if current_user() is not None and current_user()["status"] == "active":
        return redirect(url_for("home"))

    email = ""
    if request.method == "POST":
        if not csrf_ok():
            flash("Your session expired. Please try again.", "error")
            return redirect(url_for("auth.gate"))

        email = normalize_email(request.form.get("email"))
        error = validate_email(email)
        if error:
            flash(error, "error")
            log_event("gate_rejected", email=email, detail=error, ip=client_ip())
            return render_template("gate.html", email=email)

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

        # --- New address: create the shell account and invite them.
        if user is None:
            cur = db.execute(
                "INSERT INTO users (email, status, school, created_at)"
                " VALUES (?, 'pending', ?, ?)",
                (email, DOMAIN_TO_SCHOOL.get(domain_of(email)), utcnow()),
            )
            db.commit()
            user = db.execute(
                "SELECT * FROM users WHERE id = ?", (cur.lastrowid,)
            ).fetchone()
            log_event("user_created", email=email, user_id=user["id"], ip=client_ip())
            issue_invite(user)
            session["pending_email"] = email
            return redirect(url_for("auth.invite_sent"))

        if user["status"] == "suspended":
            flash("This account is not active. Contact the MarketPlace team.", "error")
            return render_template("gate.html", email=email)

        # --- Known but never finished onboarding: same branch, fresh invite.
        if user["status"] == "pending":
            issue_invite(user)
            session["pending_email"] = email
            return redirect(url_for("auth.invite_sent"))

        # --- Returning user: one-time passcode.
        session["pending_email"] = email
        issue_otp(user)
        return redirect(url_for("auth.verify"))

    return render_template("gate.html", email=email)


@bp.route("/invite/sent")
def invite_sent():
    email = session.get("pending_email")
    if not email:
        return redirect(url_for("auth.gate"))
    return render_template("invite_sent.html", email=email, ttl_days=INVITE_TTL.days)


@bp.route("/invite/accept")
def accept_invite():
    """Landing point for the emailed link. Single use."""
    token = request.args.get("token", "")
    try:
        data = _serializer().loads(token, max_age=int(INVITE_TTL.total_seconds()))
    except SignatureExpired:
        flash("That invitation has expired. Enter your email to get a new one.", "error")
        return redirect(url_for("auth.gate"))
    except BadSignature:
        flash("That invitation link is not valid.", "error")
        return redirect(url_for("auth.gate"))

    db = get_db()
    row = db.execute(
        "SELECT * FROM invites WHERE token_hash = ?", (_hash(token),)
    ).fetchone()
    if row is None or row["consumed_at"] is not None:
        flash("That invitation has already been used. Enter your email to sign in.", "error")
        return redirect(url_for("auth.gate"))

    db.execute("UPDATE invites SET consumed_at = ? WHERE id = ?", (utcnow(), row["id"]))
    db.commit()

    login(data["uid"])
    log_event("invite_accepted", email=data["email"], user_id=data["uid"], ip=client_ip())
    return redirect(url_for("auth.onboarding"))


@bp.route("/verify", methods=("GET", "POST"))
def verify():
    email = session.get("pending_email")
    if not email:
        return redirect(url_for("auth.gate"))

    db = get_db()
    user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user is None:
        session.pop("pending_email", None)
        return redirect(url_for("auth.gate"))

    if request.method == "POST":
        if not csrf_ok():
            flash("Your session expired. Please try again.", "error")
            return redirect(url_for("auth.gate"))

        ok, message = check_otp(user, request.form.get("code"))
        if not ok:
            flash(message, "error")
            return render_template("verify.html", email=email, length=OTP_LENGTH)

        login(user["id"])
        session.pop("pending_email", None)
        log_event("login", email=email, user_id=user["id"], ip=client_ip())
        return redirect(url_for("home"))

    return render_template("verify.html", email=email, length=OTP_LENGTH)


@bp.post("/verify/resend")
def resend():
    email = session.get("pending_email")
    if not email:
        return redirect(url_for("auth.gate"))
    if not csrf_ok():
        flash("Your session expired. Please try again.", "error")
        return redirect(url_for("auth.gate"))

    user = get_db().execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if user and issue_otp(user):
        flash("A new code is on its way.", "ok")
    else:
        flash("Hold on a moment before requesting another code.", "error")
    return redirect(url_for("auth.verify"))


@bp.route("/onboarding", methods=("GET", "POST"))
def onboarding():
    """Activate the account.

    Only a display name for now. The three self-declared attributes --
    location, nationality, industry -- are deliberately not collected yet;
    their option sets are undecided, and free text would be unfilterable. The
    columns already exist in `users`, so adding the step back later is a
    template change and nothing more.
    """
    user = current_user()
    if user is None:
        return redirect(url_for("auth.gate"))
    if user["status"] == "active":
        return redirect(url_for("home"))

    if request.method == "POST":
        if not csrf_ok():
            flash("Your session expired. Please try again.", "error")
            return redirect(url_for("auth.gate"))

        display_name = (request.form.get("display_name") or "").strip()
        if not display_name:
            flash("Enter the name you want to appear on your listings.", "error")
            return render_template("onboarding.html", user=user, values={})

        db = get_db()
        db.execute(
            "UPDATE users SET display_name = ?, status = 'active',"
            " activated_at = ? WHERE id = ?",
            (display_name, utcnow(), user["id"]),
        )
        db.commit()
        log_event("onboarded", email=user["email"], user_id=user["id"], ip=client_ip())
        return redirect(url_for("home"))

    return render_template("onboarding.html", user=user, values={})


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.gate"))
