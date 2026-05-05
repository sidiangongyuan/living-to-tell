# Security Policy

Writer is a local-first desktop writing app. It can read user-selected AI
credentials at request time, but it should never persist raw API keys or OAuth
access tokens in this repository or in Writer's settings database.

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.2.x alpha | Best-effort security fixes |
| Earlier versions | Not supported |

## Credential handling

Writer may read the following local credential sources at runtime:

- environment variables such as `OPENAI_API_KEY` or `GEMINI_API_KEY`
- `~/.codex/auth.json` when API key source is `codex`
- `~/.gemini/.env` when API key source is `gemini`
- `~/.gemini/oauth_creds.json` when provider is Gemini CLI / OAuth

Rules for contributors:

- Do not commit real API keys, OAuth tokens, account emails, project IDs, local
  databases, or personal writing data.
- Keep generated artifacts such as `dist/`, `build/`, `.venv/`, and SQLite
  databases untracked.
- Use placeholder values in docs and tests, for example `env:OPENAI_API_KEY`,
  `http://127.0.0.1:PORT`, and `gm-test`.
- Do not paste credential files into issues, pull requests, logs, screenshots,
  or test fixtures.

## Reporting a vulnerability

If GitHub private vulnerability reporting is enabled for this repository, use
that channel first.

If private reporting is not available, open a GitHub issue with a minimal
non-secret reproduction and mark it as security-sensitive. Do not include raw
keys, OAuth tokens, local database files, account emails, or private writing
content.

## Local data locations

By default, Writer stores app data under the platform user-data directory, for
example `%APPDATA%\Writer\Writer\` on Windows. Development and test runs may
also use `WRITER_DATA_DIR`. These directories are user data, not source code,
and should not be committed.
