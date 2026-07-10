# Contributing

Thank you for your interest in Living to Tell. The project is a public preview, so contributions should prioritize writing comfort, reliability, privacy, and understandable workflows.

## Development setup

The current desktop app uses Python 3.12+, Node.js, Rust, Vue 3, and Tauri 2 on Windows. Follow the [desktop developer guide](tauri-mvp/README.md) for the complete setup and run commands.

Install the Python and frontend dependencies:

```powershell
pip install -e .[dev]
cd tauri-mvp\frontend
npm install
```

Run the main checks before opening a pull request:

```powershell
python -m pytest tests\test_tauri_mvp_api.py tests\storage -q
cd tauri-mvp\frontend
npm test -- --run
npm run test:e2e -- --project=msedge --workers=1
npm run build
cargo check --manifest-path src-tauri\Cargo.toml
```

Run Ruff on changed Python files. Add focused regression coverage when behavior changes.

## Pull request expectations

- Keep changes focused and product-facing.
- Preserve existing user data and document any migration behavior.
- Add or update tests in proportion to the affected workflow.
- Update English and Chinese documentation when user-visible behavior changes.
- Keep AI writes previewable and explicit; do not silently change articles, references, motifs, or project memory.
- Do not commit generated artifacts, local databases, virtual environments, logs, screenshots with personal data, or private writing samples.
- Do not commit API keys, OAuth tokens, account emails, cloud project IDs, or local credential files.

## Documentation and screenshots

Write for people encountering the project for the first time. Public screenshots must use disposable demo data only and must not show private text, credentials, local usernames, or private paths. See [the screenshot checklist](docs/screenshots/README.md).

## Release discipline

Before a public release:

1. Confirm the version in the frontend package, Tauri/Cargo files, and backend version metadata.
2. Run backend, frontend, E2E, production-build, and Cargo checks.
3. Scan tracked changes for credentials, private writing, databases, and machine-specific paths.
4. Build the Windows installers with `tauri-mvp\build-release.ps1`.
5. Update release notes, the changelog, and current README download links.
6. Upload both installer assets and verify their remote sizes and SHA256 digests.
