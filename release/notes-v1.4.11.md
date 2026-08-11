# HackMan3D Control Deck 1.4.11

This maintenance update fixes community roadmap refreshes.

- The public roadmap percentage is fetched at every application launch instead
  of reusing a six-hour-old value from local settings.
- The feed is checked again automatically every six hours while the application
  remains open.
- Requests continue to bypass the GitHub raw-file cache.
- Only the public percentage is downloaded. Donation amounts and targets remain
  private and are not included in the application or its public feed.

The current public roadmap progress is 4%.
