# Contributing

Thank you for your interest in Writer. The project is currently alpha-stage, so contributions should prioritize reliability, privacy, and a clear writing workflow.

## Development setup

Requirements:

- Windows
- Python 3.12+

Install dependencies:

```powershell
pip install -e .[dev]
```

Run the app:

```powershell
writer
```

Run tests:

```powershell
python -m pytest
```

Run Ruff on changed Python files before opening a pull request.

## Pull request expectations

- Keep changes focused and product-facing.
- Add or update tests for behavior changes.
- Update documentation when user-visible behavior changes.
- Do not commit generated artifacts, local databases, virtual environments, logs, screenshots with personal data, or private writing samples.
- Do not commit API keys, OAuth tokens, account emails, cloud project IDs, or local credential files.

## Documentation and screenshots

Documentation should be written in a professional tone and avoid internal planning notes. Public screenshots must use clean demo data only. See [docs/screenshots/README.md](docs/screenshots/README.md).

## Release discipline

Before a public release:

1. Confirm the version in `src/writer/app/version.py` and `pyproject.toml`.
2. Run the full test suite.
3. Build the Windows portable zip.
4. Review tracked files for credentials, local paths, databases, logs, and personal content.
5. Update release notes and the changelog.
