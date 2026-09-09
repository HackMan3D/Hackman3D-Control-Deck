# Anonymous usage service

This optional service receives only a random session value kept in application
memory, a heartbeat and grouped action counts. It does not receive profile names,
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
the token stored in macOS Keychain.
