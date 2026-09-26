CREATE TABLE IF NOT EXISTS counters (
    name TEXT PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS active_sessions (
    session TEXT PRIMARY KEY,
    started_at INTEGER NOT NULL,
    last_seen INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS active_sessions_last_seen ON active_sessions(last_seen);

CREATE TABLE IF NOT EXISTS installations (
    installation_hash TEXT PRIMARY KEY,
    first_seen INTEGER NOT NULL,
    last_seen INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS installations_last_seen ON installations(last_seen);

-- HCD Supporter membership data. Email addresses and Ko-fi transaction IDs are
-- never stored directly: the Worker keeps only keyed hashes. Access tokens are
-- random and stored as SHA-256 hashes so a database export cannot activate the
-- desktop application.
CREATE TABLE IF NOT EXISTS supporter_memberships (
    id TEXT PRIMARY KEY,
    email_hash TEXT NOT NULL UNIQUE,
    tier_name TEXT NOT NULL,
    active_until INTEGER NOT NULL,
    last_payment_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS supporter_memberships_active_until
    ON supporter_memberships(active_until);

CREATE TABLE IF NOT EXISTS supporter_transactions (
    transaction_hash TEXT PRIMARY KEY,
    membership_id TEXT NOT NULL,
    received_at INTEGER NOT NULL,
    FOREIGN KEY(membership_id) REFERENCES supporter_memberships(id)
);

CREATE TABLE IF NOT EXISTS supporter_tokens (
    token_hash TEXT PRIMARY KEY,
    membership_id TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    last_seen INTEGER NOT NULL,
    revoked_at INTEGER,
    FOREIGN KEY(membership_id) REFERENCES supporter_memberships(id)
);
CREATE INDEX IF NOT EXISTS supporter_tokens_membership
    ON supporter_tokens(membership_id);
