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

## HCD Supporter activation

The same Worker can validate the optional monthly `HCD Supporter` membership.
Ko-fi sends subscription payments to `/v1/kofi/webhook`. A supporter claims the
first payment once in the desktop app with the Ko-fi transaction ID, after which
the app stores a random access token. Later monthly webhooks extend the access
automatically with a 35-day grace period.

Apply `schema.sql`, then configure these Worker secrets (never commit their
values):

```text
wrangler secret put KOFI_VERIFICATION_TOKEN
wrangler secret put SUPPORTER_HASH_SECRET
```

`KOFI_VERIFICATION_TOKEN` is copied from Ko-fi's webhook settings.
`SUPPORTER_HASH_SECRET` must be a separate random value of at least 32
characters. Configure Ko-fi's webhook URL as:

```text
https://<worker-domain>/v1/kofi/webhook
```

Only keyed hashes of the Ko-fi email and transaction ID are stored. The Worker
does not store the email address, payer name, message, amount, profile data or
Control Deck configuration. One-time tips are accepted by the webhook but do
not unlock the monthly membership.
