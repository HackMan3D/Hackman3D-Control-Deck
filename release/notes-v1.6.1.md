# HackMan3D Control Deck 1.6.1

This maintenance release uses the same **1.6.1** version number on macOS,
Windows and Linux.

## Fixed

- prevents the Windows interface from freezing while listing or assigning an
  installed application;
- loads Windows application icons only when they are needed;
- keeps the integrated updater aligned with the correct installer for each
  operating system;
- adds a release check that detects inconsistent package version numbers.

The integrated updater downloads the installer matching the current operating
system and verifies its SHA-256 checksum before opening it.
