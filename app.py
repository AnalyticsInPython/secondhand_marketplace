"""MarketPlace -- a Columbia-only secondhand marketplace.

Run it:
    pip install -r requirements.txt
    flask --app app init-db
    flask --app app run --debug
"""

import os

from dotenv import load_dotenv
from flask import Flask, render_template

import auth
import db

load_dotenv()


def _domains():
    raw = os.environ.get("ALLOWED_EMAIL_DOMAINS", "columbia.edu")
    return {d.strip().lower() for d in raw.split(",") if d.strip()}


def create_app():
    app = Flask(__name__, instance_relative_config=True)
    os.makedirs(app.instance_path, exist_ok=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev-only-insecure-key"),
        DATABASE=os.path.join(app.instance_path, "marketplace.db"),
        ALLOWED_EMAIL_DOMAINS=_domains(),
        MAIL_BACKEND=os.environ.get("MAIL_BACKEND", "file"),
        MAIL_FROM=os.environ.get("MAIL_FROM", "MarketPlace <no-reply@marketplace.local>"),
        SMTP_HOST=os.environ.get("SMTP_HOST", ""),
        SMTP_PORT=int(os.environ.get("SMTP_PORT", 587)),
        SMTP_USER=os.environ.get("SMTP_USER", ""),
        SMTP_PASSWORD=os.environ.get("SMTP_PASSWORD", ""),
        SMTP_USE_TLS=os.environ.get("SMTP_USE_TLS", "true").lower() == "true",
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )

    db.init_app(app)
    app.register_blueprint(auth.bp)

    # Templates need these on every render.
    app.jinja_env.globals["csrf_token"] = auth.csrf_token
    app.context_processor(lambda: {"current_user": auth.current_user()})

    @app.route("/home")
    @auth.login_required
    def home():
        """The blank canvas. Everything after the gate gets built here."""
        return render_template("home.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
