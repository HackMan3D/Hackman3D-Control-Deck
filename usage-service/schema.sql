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
