# Living to Tell Preview 0.1.52

0.1.52 makes the planning board genuinely sortable and gives AI edits a dedicated place to be read, compared, revised, and safely applied.

## Planning priority without changing the book

- Drag a card up or down inside one status column to decide what to work on first.
- Drag across columns to change the current card's status and exact landing position.
- Use Move Up, Move Down, Move to Top, or Move to Bottom when dragging is inconvenient.
- Board priority never changes manuscript order, export order, parent/child structure, or another card's status.

Existing projects are migrated deterministically from their current manuscript order, so the first upgraded board does not shuffle unexpectedly.

## AI results have their own workspace

Running Polish, Rewrite, Expand, or Continue now opens `/ai/results/:runId` immediately. The setup page stays focused on the article, purpose, references, and model selection.

The results workspace provides:

- The latest 20 runs from the current app session.
- Per-model waiting, success, failure, latency, token, cost, and transport status.
- Original comparison, two-model comparison, and paragraph difference views.
- An immutable model result plus a separately editable copy with short-delay saving.
- Early `Ready / Article Changed / Article Missing` write-back status.
- Idempotent, versioned write-back that creates `AI_BEFORE_APPLY` before changing the article.

Runs and edited copies remain in process memory only and expire when the app closes. Opening an expired link never resends a provider request.

## Twenty-five writing purposes

The four article tasks now start from a clear writing purpose instead of a blank prompt:

- Polish: clarity, tightening, rhythm, natural dialogue, prose quality, and less forced writing.
- Rewrite: natural rephrasing, directness, show-don't-tell, subtext, literary language, and viewpoint/tense conversion.
- Expand: action, psychology, atmosphere, five senses, argument depth, and scene expansion.
- Continue: natural continuation, scene movement, dialogue, emotional depth, argument continuation, closure, and foreshadowing.

Purposes are grouped into Common, Creative, and My Presets, with General, Fiction, Essay, and Nonfiction filters. Higher-change purposes show a risk note, while viewpoint, tense, argument direction, and scene focus use structured controls.

Personal presets save only task controls and supplementary instructions. They never store article text, selections, models, or reference attachments.

## Cleaner prose output

All four article tasks now share an explicit prose-format contract. Before a model result reaches display, copy, comparison, statistics, or raw write-back, the app:

- Converts line endings consistently.
- Removes leading and trailing blank paragraphs.
- Removes line-end whitespace.
- Collapses repeated blank lines to one paragraph break.

It does not flatten nonempty indentation, single line breaks, list markers, poetry lines, or internal spaces. Once the author edits a copy, that deliberate spacing is preserved.

## Verification

- Python: `923 passed, 1 skipped`; the skipped test is the explicitly gated Gemini quota probe.
- Frontend unit tests: `97 passed`.
- Mock Edge workflows: `80 passed`, including accessibility and Chinese/English overflow checks.
- Isolated real-backend workflows: `2 passed`.
- Production frontend build and locked Cargo check passed.
- One isolated synthetic DeepSeek check completed Polish, Rewrite, Expand, and Continue through OpenAI Chat Completions. No user article or reference text was read, no result was applied, and GLM was neither called nor retried.

## Downloads

- `LivingToTell_0.1.52_x64-setup.exe`
- `LivingToTell_0.1.52_x64_zh-CN.msi`

The Windows preview is unsigned, so SmartScreen may show a warning. Download installers only from this repository's GitHub Release.
