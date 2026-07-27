# Living to Tell Preview 0.1.53

0.1.53 is a focused startup reliability hotfix for the Windows desktop preview.

## Fixed

- The app now waits for the packaged backend sidecar to publish its local port during a cold start.
- Concurrent first-screen requests share the same readiness wait instead of each failing with a misleading backend-connection message.
- If the sidecar genuinely cannot start within the bounded wait, the app still shows the existing recovery guidance and never falls back to a development endpoint.

This update does not change the database, AI profiles, articles, collections, or any other writing data.

## Verification

- Frontend unit tests: `98 passed`, including delayed-port and concurrent cold-start requests.
- Production frontend build and locked Cargo check passed.
- The packaged sidecar returned `health=ok` and version `0.1.53` from an isolated temporary data directory.

## Downloads

- `LivingToTell_0.1.53_x64-setup.exe`
- `LivingToTell_0.1.53_x64_zh-CN.msi`

The Windows preview is unsigned, so SmartScreen may show a warning. Download installers only from this repository's GitHub Release.
