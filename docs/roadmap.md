# Roadmap

Writer is currently an alpha-stage local-first writing app. The project is
usable for daily writing, but the UI, packaging, and AI workflows are still
moving quickly.

## Current alpha focus

- Local-first fragment, work, collection, reference, and project data.
- Autosave and version-history safeguards for destructive edits.
- AI Workspace with task tools, scoped chat, manual context attachments, and
  safe write-back.
- GPT / OpenAI-compatible providers, native Gemini API-key provider, and
  Gemini CLI / OAuth provider.
- Windows portable packaging.

## Before beta

- Add screenshots captured from a clean demo profile with no personal writing
  data, credentials, account emails, or local paths.
- Improve first-run onboarding for data location, language, AI provider, and
  Gemini proxy/OAuth setup.
- Add import/export backup flows for the SQLite data directory.
- Expand accessibility review for keyboard navigation and screen-reader labels.
- Add safer failure copy for AI quota, model availability, network, and proxy
  errors.
- Stabilize the AI task template and card UI that is currently repository-level
  only.
- Improve the AI revision workflow so quick actions open editable settings,
  rewrite-style results show original text beside AI output, and task parameters
  remain isolated per task. See [AI Revision Workflow Plan](ai-revision-workflow.md).

## Later candidates

- Cross-platform packaging beyond Windows.
- Richer manuscript front matter and print/PDF-oriented export.
- Optional encrypted-at-rest local database support.
- Optional cloud sync adapter, kept separate from the local-first core.
- Plugin-style AI provider adapters.
- Better token counting using provider-native count-token endpoints.
- Rich tracked-changes review mode for AI edits, with muted deletions and
  highlighted additions.

## Non-goals for the current alpha

- No bundled API keys or shared cloud account.
- No automatic upload of private writing data.
- No committed personal databases, OAuth state, or generated release bundles.
