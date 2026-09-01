-- MarketPlace schema. Auth only for now; listings land in a later migration.
-- All timestamps are ISO-8601 UTC strings, so plain string comparison sorts them.

DROP TABLE IF EXISTS auth_events;
DROP TABLE IF EXISTS otp_codes;
DROP TABLE IF EXISTS invites;
DROP TABLE IF EXISTS users;

CREATE TABLE users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'active', 'suspended')),

  -- The four affiliation attributes from the proposal. Null until onboarding.
  -- `school` is derived from the email domain; the other three are self-declared.
  display_name  TEXT,
  location      TEXT,
  nationality   TEXT,
  school        TEXT,
  industry      TEXT,

  created_at    TEXT NOT NULL,
  activated_at  TEXT,
  last_login_at TEXT
);

-- One row per invitation sent to a brand-new email address.
-- The emailed link carries a signed token; we store only its hash.
CREATE TABLE invites (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token_hash  TEXT NOT NULL,
  expires_at  TEXT NOT NULL,
  consumed_at TEXT,
  created_at  TEXT NOT NULL
);
CREATE INDEX idx_invites_user ON invites(user_id);

-- One row per OTP issued to a returning user. Codes are hashed at rest.
CREATE TABLE otp_codes (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  code_hash   TEXT NOT NULL,
  expires_at  TEXT NOT NULL,
  attempts    INTEGER NOT NULL DEFAULT 0,
  consumed_at TEXT,
  created_at  TEXT NOT NULL
);
CREATE INDEX idx_otp_user ON otp_codes(user_id, created_at);

-- Append-only audit log. Doubles as the raw event feed for the funnel analysis
-- ("interaction events") described in the proposal.
CREATE TABLE auth_events (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  email      TEXT,
  user_id    INTEGER REFERENCES users(id) ON DELETE SET NULL,
  event      TEXT NOT NULL,
  detail     TEXT,
  ip         TEXT,
  created_at TEXT NOT NULL
);
CREATE INDEX idx_events_created ON auth_events(created_at);
