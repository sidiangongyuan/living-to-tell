# Changelog

Product-facing changes only. Internal planning notes, agent prompts, and local
experiment logs are intentionally not kept in the public repository.

## 0.2.0-alpha.15 — Public alpha release

- Published a Windows portable zip release for direct download.
- Improved the writing layout so maximized and focus-mode windows use the
  available horizontal space instead of keeping the editor in a narrow column.
- Expanded the daily reference card on the Dates page so it reads comfortably
  on wider screens.
- Added quick capture, tray-friendly writing, and configurable global hotkeys.
- Added the style specimen library for saving reference passages and applying
  them as AI style constraints.
- Clarified that the daily quote is drawn from the existing reference library,
  with no separate quote database or special quote type.
- Added public user guides, release notes, and a roadmap/TODO structure for
  open-source users.

## 0.2.0-alpha.7 to 0.2.0-alpha.14 — Writing comfort and polish

- Added editor display settings for font size, line height, paragraph spacing,
  visual first-line indentation, content width, and typewriter mode.
- Added focus mode for distraction-reduced writing.
- Added a daily reference card on the Dates page.
- Improved button sizing and layout in the AI workspace and context pane.
- Improved Windows packaging so release zips are versioned and reproducible.

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
