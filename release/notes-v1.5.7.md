# HackMan3D Control Deck 1.5.7

- Fixes secure update checks in packaged applications by bundling a verified CA certificate store.
- Makes optional anonymous usage reporting reliable on macOS, Windows and Linux without depending on Qt's TLS backend.
- Removes an active session immediately after a clean application exit.
- Keeps the automatic expiry fallback for crashes, power loss and offline shutdowns.
- Sends no profiles, configured actions, application names, shortcuts, hardware identifiers or personal data.
