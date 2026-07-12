# Living to Tell Preview 0.1.47

0.1.47 is a stability release for AI setup and article editing. It replaces two drifting configuration systems with AI profiles plus one clear default, binds AI modification to a real article or selection, and makes multi-model work recoverable for the current app session.

## Highlights

- **One AI configuration model**: every provider connection is a profile, one profile is the default, and legacy settings migrate without guessing or losing their transport.
- **Three-step profile setup**: choose the access method, enter only the necessary details, then save and optionally send a minimal real test. Failed tests keep the profile and entered configuration.
- **Visible profile health**: Untested, Passed, Failed, or Configuration Changed; local checks are separate from real provider tests that may use tokens and cost money.
- **Article-bound AI Edit**: Polish, Rewrite, Expand, and Continue work on one selected article or explicit selection. The old arbitrary paste workflow is gone from the interface.
- **Recoverable multi-model runs**: selected models run independently, faster results appear first, one failure does not block another result, and leaving the page does not resend the provider request.
- **Safer write-back**: every apply opens a before/after preview, verifies the article has not changed under the run, creates an `AI_BEFORE_APPLY` version, and applies only once.
- **Article AI Chat drawer**: discuss the current article without leaving it. Closing the drawer keeps the draft, thread, and in-flight reply; saving a reply elsewhere remains explicit.

## Settings and diagnostics

Settings now opens by category: **AI**, **Data & Backup**, **Interface & Tutorials**, and **Updates & About**. Ordinary profile cards show only name, model, access method, default state, and health; endpoint, transport, and credential-source details stay behind Details or Advanced settings.

Missing credentials or local login, authentication timeout, 401, 403, 404, 429, provider timeout, HTML gateway pages, and traceback-shaped responses are converted to safe actionable messages. The interface never needs raw provider HTML, secret values, stack traces, or local credential paths.

## Compatibility and migration

- Existing profiles remain intact.
- When the old global AI configuration exactly matches a profile, that profile becomes the default.
- When it does not match, the old configuration is preserved as `原默认配置` with its original transport.
- A fresh install with no persisted configuration remains empty instead of receiving a fake `env:OPENAI_API_KEY` profile.
- Legacy AI task endpoints and saved task presets remain available for compatibility, although the current AI Edit interface shows only the four article-focused tasks.
- Writing data and database schema are unchanged by the article AI task manager; task results live only for the current application process.

## Safety boundaries

- Multi-model runs send exactly the profiles selected at start. The default profile is never silently injected.
- Reconnection queries the original run and never resends it.
- Local cancellation cannot guarantee that an already-sent remote request stops generating or billing.
- Ordinary chat, failed suggestions, and unapplied AI output never enter the article, references, AI Cards, motifs, or Collection Agent memory automatically.
- Deleting a profile keeps its local key by default and requires a replacement when the profile is default or used by a Collection Agent.

## Quality pass

The release audit covers the complete Python suite, frontend unit tests, Mock browser workflows, isolated real-backend workflows, real-provider probes with synthetic text, frontend production build, locked Rust check, nine primary surfaces at three release viewports in Chinese and English, and accessibility checks for Settings, Articles, Collections, AI Edit, and Backup.

GitHub Actions now runs the full non-provider quality gate on pushes, pull requests, and manual dispatch. Real provider requests remain local-only and never enter CI.

See the [0.1.47 quality report](../quality/0.1.47-quality-report.md) for exact evidence and any environment-specific provider result.

## Windows assets

- `LivingToTell_0.1.47_x64-setup.exe`
- `LivingToTell_0.1.47_x64_zh-CN.msi`

Preview installers remain unsigned. Download them only from this repository's GitHub Release page and verify the published asset digest when available.
