# Anonymous usage service

This optional service receives a random locally persisted installation value,
a random temporary session value, a heartbeat and grouped action counts. The
installation value is SHA-256 hashed before storage and is never derived from
hardware or an account. It does not receive profile names,
configured actions, application names, shortcuts, hardware identifiers or user
accounts. Observability is disabled so request bodies are not kept in application
logs.

Statistics are stored in a private Cloudflare D1 database. The administrative
endpoint requires the private `ADMIN_TOKEN` secret. Never place that token in the
desktop application, the release manifest or this repository.

Deployment requires a private Cloudflare account: create the D1 database, copy
`wrangler.toml.example` to the ignored `wrangler.toml`, apply `schema.sql`, set
`ADMIN_TOKEN` with Wrangler secrets, and deploy. Put only the public `/v1/usage`
URL in `release/manifest.json`; the private Mac viewer uses `/v1/admin/stats` and
the private token stored only on the owner's Mac.

The authenticated statistics endpoint exposes unique installations in total and
new installations today, as well as installations seen over the rolling last
30 days. Old clients without an installation value remain
compatible but do not contribute to unique counts. These count installations,
not people; deleting settings or using another computer creates another ID.
An installation ID is persistent pseudonymous data, not a claim of complete
anonymity. Sharing is optional and can be disabled in the desktop application.
