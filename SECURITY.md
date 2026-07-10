# Security Policy

Living to Tell is a local-first desktop writing app. It can read user-selected AI credentials at request time, but raw API keys and OAuth access tokens must never be committed to this repository or stored in the app's SQLite settings data.

## Supported versions

| Version | Supported |
| --- | --- |
| Latest `0.1.x` public preview | Best-effort security fixes |
| Earlier previews | Upgrade recommended |

## Credential handling

Living to Tell may read credentials from sources explicitly selected by the user:

- environment variables such as `OPENAI_API_KEY`, `GEMINI_API_KEY`, or profile-specific `LTT_AI_*` variables;
- local Codex authentication;
- local Gemini configuration or Gemini CLI/OAuth authentication;
- local OpenCode authentication.

Saved AI profiles retain the credential source name, provider, endpoint, and model. API responses and logs must never expose the raw credential value.

Rules for contributors:

- Do not commit real API keys, OAuth tokens, account emails, project IDs, local databases, or personal writing data.
- Keep generated artifacts such as `dist/`, `build/`, `.venv/`, `node_modules/`, Rust `target/`, and SQLite databases untracked.
- Use placeholder values in docs and tests, such as `env:OPENAI_API_KEY`, `http://127.0.0.1:PORT`, and `test-key`.
- Do not paste credential files into issues, pull requests, logs, screenshots, or test fixtures.
- Clean provider HTML, stack traces, and sensitive path details before presenting AI errors to users.

## Reporting a vulnerability

Use GitHub private vulnerability reporting when it is available for this repository.

If private reporting is unavailable, open a GitHub issue containing only a minimal, non-secret reproduction and mark it as security-sensitive. Do not include raw keys, OAuth tokens, local database files, account emails, or private writing content.

## Local data locations

On Windows, writing data is stored by default under `%APPDATA%\LivingToTell\LivingToTell\`. The primary database is `living-to-tell.sqlite3`; backups and checkpoints are kept outside the installed application directory.

Development and test runs may use `WRITER_DATA_DIR`. These locations contain user data, not source code, and must remain untracked. Uninstalling the application does not delete the writing database, backups, or checkpoints.
