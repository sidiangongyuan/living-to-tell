# Changelog

Product-facing changes only. Internal planning notes, agent prompts, and local
experiment logs are intentionally not kept in the public repository.

## 0.2.0-alpha.35 — Splitter layout guardrails

- Added guardrails for restored splitter sizes so stale or extreme saved layout
  values cannot collapse the right context pane or squeeze the fragment editor
  into an unusable width after maximize / restore.
- Normalized fragment-list and editor splitter sizes on restore, show, and
  resize, while preserving the intentional collapsed-sidebar state.
- Normalized the outer shell splitter so the context pane keeps a usable width
  whenever it is visible.
- Added regression coverage for bad persisted splitter sizes and bad focus-mode
  restore sizes.

## 0.2.0-alpha.34 — Main-workspace sticky notes

- Moved fragment sticky notes from the editor panel layer to the full main
  workspace layer, so notes can be placed beyond the text panel instead of
  being limited to the fragment editor rectangle.
- Kept notes scoped to the active fragment: switching to another mode hides the
  floating cards so they do not leak into Works, AI, or other pages.
- Recomputed note controls and drag bounds on window resize, improving
  maximize / restore behavior.
- Added regression coverage for cross-workspace note placement and mode-switch
  hiding.

## 0.2.0-alpha.33 — Floating note board layout fix

- Changed the fragment note board control from a right-side layout column into
  a compact floating control, so it no longer squeezes the editor or the
  right-hand context pane.
- Shortened the collapsed note entry to a small "Notes / 便签" pill instead of
  the wider "Show notes / 展开便签" rail.
- Moved sticky note cards onto the whole editor panel layer, expanding their
  placement area beyond the body content wrapper.
- Added regression coverage for wide-window context-pane visibility and the
  floating note-board geometry.

## 0.2.0-alpha.32 — Larger readable sticky notes

- Changed fragment notes to normal square sticky notes with a larger default
  size, so short notes are readable without being squeezed.
- Added internal scrolling inside each note body for long note text.
- Expanded the drag bounds from the body editor to the full fragment workspace,
  so notes can be placed near the title, tags, epigraph, or editor area.
- Raised the stored note width defaults and validation range for existing and
  newly created note layouts.

## 0.2.0-alpha.31 — Freer sticky-note interaction

- Changed fragment notes from a constrained right-side card area into floating
  sticky notes over the editor surface.
- Fixed the note collapse control so it remains readable and can be reopened /
  closed reliably.
- Added direct pin buttons on notes; pinned notes stay fixed and cannot be
  dragged accidentally.
- Made note dragging smoother by removing snap-on-release and keeping movement
  continuous within the editor bounds.
- Improved note-board responsiveness so the board no longer squeezes note text
  into an unreadable narrow rail.

## 0.2.0-alpha.30 — Sticky fragment note board

- Replaced the rigid continuation-note list with a right-side sticky fragment
  note board beside the editor.
- Added note layout persistence: position, width, color, z-order, pinned state,
  done state, and per-fragment collapsed / completed visibility.
- Added note board actions for quick add, inline edit, pin, mark done / restore,
  color / width changes, arrange notes, and sending active notes to AI.
- Updated AI wording and context handling to use "fragment notes"; expand and
  continue still include open notes by default, sorted by pinned state and board
  position.
- Hardened legacy database migration for the new note-board columns and added
  regression coverage for old databases.
- Re-tightened delete-key typewriter suppression so deleting text does not
  restart a pending follow-scroll animation.

## 0.2.0-alpha.29 — Resizable settings dialog

- Made the Settings dialog resizable and maximizable.
- Moved settings content into a scrollable area so provider-specific fields no
  longer push Save / Cancel off-screen.
- Kept the dialog buttons fixed at the bottom, even when switching to Gemini
  CLI or other taller provider configurations.
- Added UI regression coverage for small-window settings layouts.

## 0.2.0-alpha.28 — Startup and reference-library polish

- Fixed transient label windows that could flash during startup, while opening
  the reference library, or while opening the AI specimen picker.
- Adjusted widget construction order so labels are attached to their parent
  layouts before their visibility is changed.
- Blocked reference-library splitter signals while restoring saved layout state,
  preventing initialization-time layout feedback and state churn.
- Added regression tests that watch for accidental top-level label windows in
  the main shell, reference library, and specimen picker.

## 0.2.0-alpha.27 — Reading-first reference library

- Reworked the reference library into a reading-first layout with a visible
  shelf, a large passage card stream, and an editor drawer that stays hidden
  until creating or editing a passage.
- Collapsed library statistics into a compact summary by default, with the
  full stats views still available on demand.
- Made passage cards body-first, so selecting a book shows the saved sentences
  immediately instead of repeating the same source title in the main list.
- Moved passage content to the top of the editor drawer and pushed source,
  author, type, usage, tags, and personal notes below it.
- Added persisted UI state for the stats panel, shelf visibility, editor drawer,
  and reference-library splitter sizes.

## 0.2.0-alpha.26 — Continuation notes density redesign

- Changed continuation notes to load collapsed by default and to preserve the
  user's per-fragment collapsed/expanded state during switching.
- Prevented normal fragment loading from being mistaken for a newly added note,
  so existing notes no longer auto-expand when returning to a fragment.
- Reworked note rows into a compact checklist-style layout with a small
  done/restore toggle, lighter inline actions, and text-first scanning.
- Styled completed notes like a TODO item: muted, struck through, recoverable,
  and visible only when the completed section is shown.
- Increased the notes scroll area only when needed so several notes are visible
  at once without making the body editor feel squeezed or clipping long notes.
- Added a writing setting for whether continuation notes should load collapsed
  by default.

## 0.2.0-alpha.25 — Notes layout and checkpoint access

- Remembered each fragment's continuation-note collapsed state during fragment
  switching, so a manually collapsed notes card no longer reopens and squeezes
  the writing area.
- Capped long continuation-note lists inside a small scroll area, keeping many
  notes available without pushing the body editor off the page.
- Added fragment context-pane shortcuts for saving a checkpoint, opening
  version history, and exporting the current fragment to Markdown.
- Added delete-selected-version support in Version History so old checkpoints
  and snapshots can be cleaned up without changing the live body.
- Clarified checkpoint access: fragment checkpoints live in File / context
  actions, work snapshots remain inside the Works editor, and exports still ask
  for an explicit save path.
- Added regression coverage for notes collapse persistence, notes scroll caps,
  version deletion, and the version-history delete UI.

## 0.2.0-alpha.24 — Continuation note workflow clarity

- Made continuation-note completion explicit: completing a note now reveals the
  completed section automatically so it feels moved and recoverable, not lost.
- Added clearer note state labels for active, pinned, and completed notes, plus
  a permanent-delete tooltip to separate "done" from deletion.
- Kept inline note editing visible and grouped note actions into a calmer two-row
  layout that avoids the old ambiguous left-side control.
- Clarified the AI workspace continuation-note panel with task-aware status
  text that explains whether the current AI tool will include notes by default.
- Split the AI note management action into "add" and "edit" states, and return
  automatically to AI after adding the first note from an empty AI note panel.
- Added regression coverage for completion visibility, AI status copy, empty
  note guidance, and add-note-return-to-AI flow.

## 0.2.0-alpha.23 — UI design and interaction polish

- Added a written UI design refresh plan with acceptance checks for the
  literary writing desk direction.
- Reworked theme tokens so preview, search, and completed-note surfaces use
  semantic colours instead of hard-coded light patches, improving dark-mode
  consistency.
- Split the top toolbar into clear Sidebar and Context controls so button
  labels, tooltips, and behaviour no longer conflict.
- Relaxed AI workspace text preview heights for selected text, extra
  instructions, pasted text, continuation notes, attachments, and chat input.
- Shared no-wheel combo and spin controls across AI, settings, reference
  library, specimen picker, and project/include dialogs to prevent accidental
  value changes while scrolling.
- Made continuation notes safer to complete by keeping completed notes
  recoverable from the editor card.
- Reduced scrollbar visual noise for a calmer reading and writing surface.

## 0.2.0-alpha.22 — Continuation note UX fixes

- Replaced the ambiguous left-side completion checkbox with a non-clickable
  accent rail and an explicit "Done" action, preventing accidental note
  disappearance.
- Added inline editing for continuation notes with save and cancel controls.
- Added a "Continue with notes" shortcut that opens the AI workspace on the
  Continue task, targets the current fragment, and forces note context on.
- Clarified note-completion copy so "done" means hidden from the active
  continuation list, not deleted from the database.
- Added regression coverage for editing notes and launching AI continuation
  directly from the notes card.

## 0.2.0-alpha.21 — Fragment continuation notes

- Added fragment-bound continuation notes for private "what should happen next"
  ideas that stay out of the body, export, and full-text search.
- Added an editor-top notes card with quick add, done, delete, and pin actions,
  plus a context-pane shortcut and open-note count.
- Added AI integration so continuation / expansion tasks can include open notes
  as reference context by default, while analysis tasks keep them opt-in.
- Added local persistence for multiple notes per fragment with cascade cleanup
  when a fragment is deleted.
- Added regression coverage for note persistence, schema upgrades, editor note
  actions, fragment switching, and AI note attachments.

## 0.2.0-alpha.20 — AI result isolation and manual checkpoints

- Isolated AI tool results by function so switching from polish to expand,
  continue, summarize, or diagnostics no longer shows the wrong result.
- Added clear-current-result and clear-all-results actions for the AI tools
  workspace without clearing attachments, parameters, custom presets, or
  version history.
- Added user-defined AI task presets stored locally per task, with inline add
  and delete controls alongside the built-in presets.
- Added fragment version checkpoints so writers can deliberately save a
  recoverable point in Version History without turning every autosave into a
  historical version.
- Clarified the save model: autosave keeps the live text current; checkpoints
  and AI/write-back snapshots are the recoverable history.
- Added regression coverage for AI task result isolation, result clearing,
  custom preset persistence, manual checkpoints, and Ctrl+S staying a normal
  save.

## 0.2.0-alpha.19 — AI write-back safety hotfix

- Prevented mouse-wheel scrolling from changing AI target, output destination,
  model tier, intensity, and output-limit controls.
- Added explicit confirmation before replacing a selection, an entire fragment,
  or a work section with AI output.
- Added a fragment-level "Undo last write-back" action that restores the
  version-history snapshot saved before the last AI write-back.
- Synchronized the fragment editor after AI write-back / undo so hidden stale
  editor content cannot overwrite the restored database state.
- Added regression coverage for selection-only replacement, no-wheel controls,
  and AI write-back undo.

## 0.2.0-alpha.18 — Reliable soft paging and cleaner editor surface

- Fixed soft page navigation so the next / previous page controls refresh after
  content and layout changes and reliably move through long fragments.
- Fixed soft page counting so the final page is based on a real reachable
  scroll position instead of leaving a disabled-looking extra page.
- Removed in-body grey page guide lines that could overlap wrapped text and
  opening epigraph previews.
- Added regression coverage for a long `绵绵`-style fragment with an opening
  epigraph and many body paragraphs.
- Hardened typewriter-scroll teardown so delayed timer callbacks do not fire
  against a deleted editor widget during close or tests.

## 0.2.0-alpha.17 — Single instance, soft paging, and AI selection flow

- Added single-instance startup so reopening Writer wakes the existing process
  instead of starting a second tray, hotkey, and database session.
- Reworked soft paging from decorative separators into page controls with
  previous / next navigation and page counts for fragment and work editors.
- Added paper spacing settings for vertical padding and page gaps alongside
  existing line height, paragraph spacing, and content width controls.
- Added AI selection previews with copy and return-to-selection actions.
- Added safe AI replacement for selected ranges inside work sections.

## 0.2.0-alpha.16 — Writing feel and literary workflow polish

- Added in-document find with match highlighting for fragment and work editors.
- Added a soft paper-page writing surface and epigraph preview for literary
  openings while keeping plain-text storage unchanged.
- Improved reference library browsing with book-style shelves, source pages,
  clearer quote cards, deletion access, and stronger duplicate review flows.
- Fixed editor mouse-wheel scrolling so one wheel notch no longer jumps from
  the start of a long document to the end.
- Published an updated Windows portable zip release for direct download.

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
