# HackMan3D Control Deck 1.5.8

## Anonymous audience measurement

- Adds a random installation identifier so the private dashboard can count
  unique installations instead of confusing application launches with users.
- Counts new installations today, installations seen during the last 30 days,
  and total unique installations.
- The identifier is generated locally and is not derived from the computer,
  hardware, account, name or email address.
- Only a SHA-256 hash is stored by the private statistics service.
- Profiles, configured actions, application names and shortcuts are never sent.
- Audience measurement remains enabled by default without a startup prompt and
  can be disabled at any time from the application settings.

Historical unique installations cannot be reconstructed. Counts begin when an
installation runs version 1.5.8 or newer.
