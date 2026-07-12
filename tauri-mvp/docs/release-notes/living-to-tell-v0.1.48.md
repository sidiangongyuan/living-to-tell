# Living to Tell Preview 0.1.48

0.1.48 makes reference material useful at the moment an author asks for an AI edit. **Reference Specimens** now sits in the main AI Edit workflow, with a readable picker designed for deliberate style and technique choices instead of tiny checkboxes hidden under More Requirements.

## Highlights

- **Reference specimens are a main step**: the current selection is always visible between task controls and model selection, including title, author, purpose, tags, total count, and total characters.
- **A proper selection workspace**: search title, author, text, tags, or personal notes; filter by purpose; click the whole card to select; and inspect full text without losing the staged selection.
- **Confirm before context changes**: opening the picker copies the active selection. Cancel, Escape, or backdrop close discards draft changes; only **Use N Specimens** commits them.
- **No hidden attachments**: the app never recommends, auto-selects, or silently sends a reference. Empty selection means no specimen context in the provider request.
- **One frozen context for every model**: all selected profiles receive the same specimen set captured when Run is clicked. Changing the picker during a run affects only the next run.
- **Recoverable provenance**: after navigation, a background result still lists the specimen names and count used for that run, without returning their text in task-status responses.

## How specimens guide an edit

Each confirmed specimen is sent as a dedicated `style_specimen` attachment with its purpose, tags, personal note, and text. The model decides which relevant aspects to borrow for Polish, Rewrite, Expand, or Continue.

The prompt explicitly forbids copying or near-copying sentences, mechanically mixing every selected style, or importing source facts, characters, plot, and named entities. The article's facts, point of view, and the author's explicit instructions always take priority.

Reference specimens are writing-method evidence, not factual sources. AI Cards and article notes remain separate optional context under **More Requirements**.

## Context size and privacy

- More than 20,000 selected specimen characters shows a token, cost, and mixed-style warning but does not block the run.
- One attachment keeps the existing 40,000-character send limit. Purpose, tags, and author note come first, followed by as much specimen text as fits; the complete saved reference is never modified.
- Task status exposes only attachment kind, reference ID, display name, and sent character count. It never returns specimen text.
- Selection exists only in the current AI Edit page session. It is not written to the database or `localStorage`.
- OpenAI-compatible calls now use a 120-second default timeout and disable the SDK's internal automatic retries. Reconnection remains status-only, and a new paid request happens only after the author starts a new run. `WRITER_OPENAI_TIMEOUT_SECONDS` is available for advanced overrides.

## Compatibility

- No database migration or reference-library schema change is required.
- Existing synchronous, streaming, and background task APIs remain compatible with ordinary `reference` attachments.
- Only the new Article AI Edit picker sends selected passages as `style_specimen`.
- This package also includes the CI sidecar-path compatibility and muted article placeholder contrast fixes that reached `main` after the 0.1.47 installers were published.

See the [0.1.48 quality report](../quality/0.1.48-quality-report.md) for automated, real-backend, real-provider, visual, packaging, and release evidence.

## Windows assets

- `LivingToTell_0.1.48_x64-setup.exe`
- `LivingToTell_0.1.48_x64_zh-CN.msi`

Preview installers remain unsigned. Download them only from this repository's GitHub Release page and verify the published asset digest when available.
