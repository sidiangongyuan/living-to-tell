# Writer Tauri Preview 0.1.6

This is a public preview cleanup release for the Tauri version of Writer.

## Highlights

- GitHub Actions are now manual-only to avoid consuming CI minutes on every push.
- The public preview forces light mode and hides dark mode entry points until the dark theme is fully polished.
- The window close button now opens the expected close behavior flow.
- Added static screenshots for article writing, focus mode, collections, reference library, AI, and settings.
- Reworked the Tauri README into a public product overview with download, quick start, AI setup, privacy, and development sections.

## Assets

Recommended Windows installer:

- `Writer_0.1.6_x64-setup.exe`

Optional:

- `Writer_0.1.6_x64_en-US.msi`
- `writer-app.exe`

## Notes

- This is a preview build, not a final stable release.
- Builds are unsigned; Windows SmartScreen may show a warning.
- Release assets are built locally and uploaded manually, not by automatic GitHub Actions.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest`
- `npm test`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`
