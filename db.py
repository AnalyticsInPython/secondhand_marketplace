"""SQLite access layer.

One connection per request, opened lazily and stashed on `flask.g` so every
helper in a request shares the same transaction.
"""

import sqlite3
from datetime import datetime, timezone

import click
from flask import current_app, g


def utcnow():
    """Single source of 'now' for the whole app, as an ISO-8601 UTC string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.open_resource("schema.sql") as f:
        db.executescript(f.read().decode("utf-8"))
    db.commit()


@click.command("init-db")
def init_db_command():
    """Drop every table and recreate it from schema.sql."""
    init_db()
    click.echo(f"Initialized {current_app.config['DATABASE']}")


def log_event(event, email=None, user_id=None, detail=None, ip=None):
    """Append to auth_events. Never raises -- logging must not break a flow."""
    try:
        db = get_db()
        db.execute(
            "INSERT INTO auth_events (email, user_id, event, detail, ip, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (email, user_id, event, detail, ip, utcnow()),
        )
        db.commit()
    except sqlite3.Error as e:
        current_app.logger.warning("auth_events write failed: %s", e)


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
