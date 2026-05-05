# Changelog

Product-facing changes only. Internal planning notes, agent prompts, and local
experiment logs are intentionally not kept in the public repository.

## 0.2.0-alpha.6 — AI providers and open-source readiness

- Added Gemini CLI / OAuth provider that reuses the local Gemini CLI login and
  calls Gemini Code Assist directly for text generation.
- Added Gemini 3 / 2.5 text model presets and kept custom model entry for
  compatible future models.
- Added Gemini tier / quota status display in Settings.
- Fixed AI context estimation so it updates for bound scopes, pasted text, and
  manual attachments.
- Added native Gemini API-key provider and local Gemini config import.
- Added Dates view for daily writing navigation.
- Added typed reference passages for characters, locations, settings, and
  excerpts.
- Added open-source hygiene: MIT license, security policy, CI, roadmap, and
  screenshot checklist.

## 0.2.0-alpha.5 and earlier

- Fragment editor with autosave, tags, search, version history, and exports.
- Works and collections for long-form organization.
- Reference library for source material.
- AI Workspace with structured writing tools, scoped chat, source-backed Q&A,
  and safe write-back.
- Windows portable packaging.
