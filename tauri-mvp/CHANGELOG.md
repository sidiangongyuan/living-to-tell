# Living to Tell Tauri Preview Changelog

## 0.1.39 - Collection Agent Usability (2026-07-07)

### Changed

- Collection Agent reference search now opens as a compact, collapsible picker. Typing `@` in the Agent input also opens the picker, and selected references become context chips instead of long inline text.
- Quick tasks such as continuity checks and memory organizing now require confirmation before any provider request is sent, showing the selected model, context scope, and prompt preview first.
- The Agent tab now includes a prompt index for the current collection, so long sessions can be searched by user prompt and jumped back to without scrolling through every answer.
- Long Agent answers collapse by default and can be expanded on demand, keeping the workspace closer to a usable desk than an endless transcript.
- Article collection cards now include an `Open` action that jumps directly from an article to its owning collection and highlights the current article in the manuscript structure.

### Added

- Added `/clear` and a `Clear conversation` action for Collection Agent sessions. Clearing removes current conversation messages, terminal runs, and processed proposal history while preserving the project bible, writing data, and pending proposals.

### Fixed

- Fixed the reference picker staying expanded and stretching the Agent page.
- Fixed quick-task buttons looking like a persistent selected state when they were actually one-click run actions.
- Fixed Agent sessions becoming hard to inspect after several long results.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py tests\storage\test_collection_outline_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`

## 0.1.38 - Collection Agent (2026-07-06)

### Added

- Added a collection-bound **Agent** tab for long-form book projects. It works as a manuscript editor / continuity assistant rather than a prose-writing bot.
- Added persistent project memory for each collection, organized into project core, characters, timeline, world, style, foreshadowing, decisions, and open questions.
- Added explicit `@`-style reference chips for structure nodes, articles, AI Cards, motifs, and reference passages so each Agent run shows what context it will read.
- Added background Agent runs with honest stages, reconnectable status, and local cancellation semantics that do not resend provider requests.
- Added reviewable Agent proposals for updating project memory, creating or updating structure nodes, and creating article notes. Proposals only write data after the user applies them.
- Added backend persistence for Agent settings, memory, runs, and actions, plus the `collection_agent` capability.

### Changed

- Collection Agent uses a per-collection AI profile setting, falling back to the global default only when the collection has not chosen a profile.
- Agent context is index-first: it reads manuscript structure and project memory by default, and reads full article/card/reference text only when explicitly referenced.
- Public README, Chinese README, and Tauri README now point to `0.1.38`.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py::test_tauri_app_version_capabilities tests\test_tauri_mvp_api.py::test_tauri_collection_agent_run_memory_and_actions -q`
- `npm run build`

## 0.1.37 - Manuscript Structure Collections (2026-07-06)

### Changed

- Reworked Collections around one canonical **Manuscript Structure** tree instead of separate Article Order and Outline surfaces.
- Added project types for General, Novel, Essay Collection, and Nonfiction; labels now adapt to the project, such as part / chapter / scene for novels and section / group / essay for essay collections.
- Structure nodes can now have parents and children in the UI, so a chapter can contain multiple article-bearing child nodes while still optionally linking one article directly.
- Added an **Unplanned Articles** area for articles that belong to the collection but have not yet been placed into the manuscript tree.
- Export now prefers the manuscript tree when structure nodes link articles; old article-list export remains as a fallback for collections that do not have linked structure nodes yet.
- Updated the Collections guided tutorial, user guide, README copy, and Tauri README for the new book-project workflow.

### Added

- Added collection project-type persistence with a safe migration default of `general`.
- Added cycle protection so a structure node cannot be moved under its own child.
- Added helper coverage for manuscript-tree building, project-aware labels, unplanned articles, and parent-cycle checks.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py tests\storage\test_collection_outline_repository.py tests\storage\test_article_collections.py tests\services\test_article_collection_export.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`

## 0.1.36 - Collection Guided Tutorial (2026-07-06)

### Added

- Added an interactive Collections tutorial with a focused spotlight, floating explanation card, Previous / Next / Skip / Finish controls, and a no-data path that does not create user content.
- The tutorial explains Collections as book/project containers, then walks through Article Order, Outline, outline item Type and Title fields, Linked Article, Planning Board, and Export.
- Added a Settings entry to restart the Collections tutorial after it has been dismissed.

### Changed

- Renamed the Collections `Manuscript` tab to `Article Order` / `文章顺序`.
- Added short in-context explanations for Article Order, Outline, Planning Board, outline item Title, Type, and Linked Article fields.
- Updated public README and user guide copy for the new terminology and tutorial restart path.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.36_x64-setup.exe`
  - SHA256: `5E21EA0DE137E5219B7C4176B7D17AB3A0EA4B011AEFB6DD43B8AFF03376E409`
- `LivingToTell_0.1.36_x64_zh-CN.msi`
  - SHA256: `1A0A9977A323E78C761DA8E530BF08626F646871501558CE523D769ACB5D068C`

## 0.1.35 - Bidirectional Motif Anchors (2026-07-06)

### Removed

- Removed the article-side Motif Invocation section and its copy/insert/save-as-note material actions.
- Removed the Motif Star Map Writing Lens, `/api/motifs/writing-index`, and the `motif_writing_index` capability.

### Added

- Added a lighter article-side "Motifs in this article" anchor list that shows linked motif names and anchor counts only.
- Added motif detail source-anchor grouping by article/reference source, with a chooser for sources that contain multiple anchors.
- Added direct anchor navigation from article to motif and from motif back to the original article/reference location without creating new graph links.

### Changed

- Motif UI now keeps authorship explicit: motifs are linked from selected text and navigated as anchors, not inserted as prepared writing material.
- AI enrichment wording now frames results as concept archives for reference, not automatic writing invocation.
- Public README links and installer names now point to `0.1.35`.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.35_x64-setup.exe`
  - SHA256: `E0EAF08814A9CD181907213B85A78299DB3E1903A68994C0494D35CB578703D9`
- `LivingToTell_0.1.35_x64_zh-CN.msi`
  - SHA256: `2EDA2AE6E7A6D84C761773CB5132DA61E2B6273B4F661958A2BBD60336B460EE`

## 0.1.34 - Article Motif Invocation (2026-07-06)

### Added

- Added an article-side Motif Invocation section in the right context pane, so existing motif profiles and related sentences can be called while drafting.
- Added explicit actions to copy motif material, insert the selected material into the current article body, save it as an article note, or open the source motif in the Motif Star Map.

### Changed

- Motif invocation reuses the existing read-only writing index and does not create motifs, excerpts, or graph links automatically.
- Article context pane tests now wait more reliably for the editor to mount in the mocked browser environment.
- Updated public documentation links and installer names to `0.1.34`.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.34_x64-setup.exe`
  - SHA256: `FDDDF2B8093D0420F0B3E46888469CC661C979614334A512198085C030075654`
- `LivingToTell_0.1.34_x64_zh-CN.msi`
  - SHA256: `B3C119F0F5B8C7D0B280AC7F1DE5DDBC7337150A5B49063640055F2A493A49F3`

## 0.1.33 - Motif Writing Lens (2026-07-05)

### Added

- Added a read-only Motif Star Map Writing Lens that groups existing motifs by tags, writing functions, and sources, then surfaces callable concept cards with related sentence snippets.
- Added `/api/motifs/writing-index` and the `motif_writing_index` backend capability for deriving writing material from existing motif profiles and excerpts without changing graph relationships.

### Changed

- The co-occurrence star map remains unchanged and continues to show only real excerpt/source co-occurrence links.
- Documentation now describes AI multi-model comparison as supporting one or more selected profiles, with a cost and latency reminder when many models are selected.
- Updated public documentation links and installer names to `0.1.33`.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.33_x64-setup.exe`
  - SHA256: `D58CF805921EADD3ACEDAEE1EDADFEA4CEAB384C3EBA1B1119E9CF123636115E`
- `LivingToTell_0.1.33_x64_zh-CN.msi`
  - SHA256: `5FDEAD596C71D9B2A6FE52BC21095D6555B2DA67EDDFFEDD9826D6DA3D7E42EF`

## 0.1.32 - Recoverable AI Jobs And Error Polish (2026-07-03)

### Added

- AI Tools multi-model comparison now streams model results as they complete, so a faster model can be reviewed before slower models finish.
- Motif Star Map AI Enrich now runs through a recoverable background job during the current app session. Users can close the dialog, reopen it, inspect the current stage, and cancel local waiting without resending the AI request.

### Changed

- Multi-model comparison no longer injects the default AI profile when the user selected other profiles, and it no longer has a hard three-model limit.
- AI result pages keep completed comparison results visible until the user explicitly clears them; the confusing result-hiding return path was removed.
- Central frontend API error handling now translates raw `Not Found`, `Failed to fetch`, HTML provider pages, traceback text, and key-shaped secrets into safer user-facing messages.
- Sample-project wording and date prompts are localized more consistently for Chinese/English UI states.
- Updated public documentation links and installer names to `0.1.32`.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.32_x64-setup.exe`
  - SHA256: `0F54953DC103CDD92FD3F3ABA7E93FA2EE44F757ED038360737242714BE98264`
- `LivingToTell_0.1.32_x64_zh-CN.msi`
  - SHA256: `2C30E4FA49FE5D17DDDD586317D654E66119BBA80DBA769C3E70FE32554DA79B`

## 0.1.31 - AI Profile Key Isolation (2026-07-01)

### Fixed

- AI configuration profiles can now keep separate locally saved API key sources even when they use the same OpenAI-compatible provider.
- Saving a key again while editing an existing profile reuses that profile's `env:LTT_AI_...` source instead of creating a drifting replacement.
- Settings keeps locally saved `env:LTT_AI_...` credential sources visible in the credential dropdown after switching to another credential source.

### Verification

- Real relay smoke tests:
  - `glm-5.2` through `https://elysiver.h-e.top/v1/chat/completions`: success.
  - `deepseek-v4-pro` through `https://elysiver.h-e.top/v1/chat/completions`: success.
  - Multi-model comparison with both saved profiles: success.
- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\services\ai -q`
- `npm test -- --run`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.31_x64-setup.exe`
  - SHA256: `A966050500808490F9FE42B15FCD7EA25AC6E88B16BBC1F6120FA19EEEE4C0AA`
- `LivingToTell_0.1.31_x64_zh-CN.msi`
  - SHA256: `AB7C25E9EB14A6E9E1A2D6B9DCE171BFFD215431B6670644D8BA813B51B19E9F`

## 0.1.30 - Local AI Key Entry And Relay Model Presets (2026-07-01)

### Added

- Added a direct API key entry flow in Settings. Users can paste a key in the AI configuration or profile editor, save it to the current Windows user environment, and have the app switch the credential source to the generated `env:LTT_AI_...` value.
- Added `deepseek-v4-pro` and `glm-5.2` to OpenAI-compatible model presets after real relay connectivity tests against `https://elysiver.h-e.top/`.

### Changed

- Settings now keeps custom `env:LTT_AI_...` credential sources visible in the credential-source dropdown instead of losing them when they are not one of the built-in options.
- OpenAI-compatible provider configuration now accepts a relay origin such as `https://elysiver.h-e.top/` and normalizes it to the SDK-ready `/v1` base URL internally.
- Updated AI settings copy so it distinguishes inline app settings from explicit local key saving through user environment variables.
- Updated public documentation links and installer names to `0.1.30`.

### Verification

- Real relay smoke tests:
  - `glm-5.2` through `https://elysiver.h-e.top/v1/chat/completions`: success.
  - `deepseek-v4-pro` through `https://elysiver.h-e.top/v1/chat/completions`: success.
- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py -q`
- `D:\anaconda\envs\writer\python.exe -m pytest tests\services\ai\test_preflight.py tests\services\ai\test_openai_provider.py tests\services\ai\test_gemini_provider.py -q`
- `npm test -- --run`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.30_x64-setup.exe`
  - SHA256: `CF00E16F78E39AC6BB20B1FBDFC6B1CAB97963654B4D04BFCD84A2C3CB5727E9`
- `LivingToTell_0.1.30_x64_zh-CN.msi`
  - SHA256: `35256E5C948FF63DE3A6696EBDA2575393663F193EDB64C1F37132E1CEF0B442`

## 0.1.29 - Motif Enrichment Logic And Resizable Dialog (2026-06-30)

### Fixed

- Fixed AI enrichment drafts becoming impossible to apply after closing and reopening the dialog for a newly typed concept. New-concept drafts are no longer invalidated just because the concept/name field changed.
- Fixed the left-panel `AI` button requiring a new motif name before opening the enrichment dialog. The dialog can now open empty, let the user enter the concept inside, and generate from there.
- Fixed a misleading stale-draft warning for new concepts. The stale guard now protects only drafts generated for a different selected motif.

### Changed

- Made the AI enrichment dialog manually resizable in addition to viewport-adaptive, with larger maximum width and more readable candidate sentence layout.
- Increased motif enrichment request timeout from 2 minutes to 5 minutes for longer concept cards.
- Broadened `请求联网补充` prompts: source hints and candidate sentences may include original sources, criticism, research, later quotations, rewrites, intertextual uses, and literary/film examples instead of only author-owned material.
- Increased enrichment source-hint and reference-candidate parsing limits so richer web-context responses are preserved.
- Updated public documentation links and installer names to `0.1.29`.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py::test_tauri_motifs_enrich_draft_uses_context_and_does_not_mutate -q`
- `D:\anaconda\envs\writer\python.exe -m pytest tests\storage\test_database_migration.py tests\storage\test_motif_repository.py tests\test_tauri_mvp_api.py -q`
- `npm test -- --run`
- `npm run test:e2e -- e2e/motifs-flow.e2e.ts --workers=1`
- `npm test -- --run src/api/base.test.ts`
- `npm run test:e2e -- --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.29_x64-setup.exe`
  - SHA256: `A4C32E8457BF1D9EC7A84E99BF5BB2F9325D5A80237378A5192C73A72F369698`
- `LivingToTell_0.1.29_x64_zh-CN.msi`
  - SHA256: `C64BC6D4798BB18587AAFB871EC579DDBD53253A2E5997F9B0F2C5A3FD7E0B0F`

## 0.1.28 - Adaptive Motif Enrichment Polish (2026-06-30)

### Fixed

- Fixed AI Enrich applying a newly typed concept with the same name as an existing motif. It now updates or merges into the existing motif instead of creating a duplicate and hitting `Motif name already exists`.
- Fixed AI Enrich drafts being discarded when closing and reopening the dialog for the same motif or concept. Drafts are now preserved until the app closes, the target changes, or the user generates a new draft.
- Fixed the AI Enrich dialog layout in non-maximized windows: footer actions stay visible, reference candidates scroll cleanly, and long source/reason text wraps instead of squeezing the cards.

### Changed

- Widened and rebalanced the AI Enrich preview so structured profile content and reference candidates remain readable on compact and wide screens.
- Added explicit stale-target protection so an enrichment draft generated for one motif cannot be accidentally applied to another.
- Stabilized the backup action E2E mock by covering the data-location dependency and host-independent API routing.
- Updated public documentation links and installer names to `0.1.28`.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\storage\test_database_migration.py tests\storage\test_motif_repository.py tests\test_tauri_mvp_api.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.28_x64-setup.exe`
  - SHA256: `DBE9F07542A72F053EECA1A5BFF8E1D9A7A496A065B2C0E4E1EA78830EE004DC`
- `LivingToTell_0.1.28_x64_zh-CN.msi`
  - SHA256: `52DCE1DCDF57E83EA268E3CFA9238D8E64AF7A6465F20954A43FD9BC51ADED30`

## 0.1.27 - Motif Concept Archives (2026-06-30)

### Added

- Added structured motif concept archives backed by `profile_json`, with automatic migration for existing SQLite databases.
- Added readable motif profile sections for definition, core tension, writing functions, scene triggers, character signals, imagery translations, examples, misuse warnings, micro exercises, and source hints.
- Added AI enrichment reference candidates. Candidates with text, author, and source title can be imported into the Reference Library and linked to the current motif as real reference excerpts.

### Changed

- Reworked motif detail editing into a chip-first and reader-first flow: tags and aliases display as removable chips, detailed profile fields live in drawers, and chip/profile edits persist only after saving the motif.
- Changed AI enrichment drafts to return structured profile data plus optional reference candidates while keeping the legacy note text for compatibility.
- Kept motif graph semantics unchanged: AI suggestions do not create semantic edges, and imported candidates only affect the graph after they become real reference excerpts.
- Updated public documentation links and installer names to `0.1.27`.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\storage\test_database_migration.py tests\storage\test_motif_repository.py tests\test_tauri_mvp_api.py -q`
- `npm test -- --run`
- `npm run test:e2e -- e2e/motifs-flow.e2e.ts --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.27_x64-setup.exe`
  - SHA256: `011BABA3E38F97E667C28E50030674C2EF71882447364C4BD214805A1DBE6E4B`
- `LivingToTell_0.1.27_x64_zh-CN.msi`
  - SHA256: `2C994D35362103DB6EEFE30EDAF99AF8E35CBF6DF723809711E4F294D8CE64EC`

## 0.1.26 - Motif AI Reliability And Detail Layout (2026-06-30)

### Fixed

- Fixed motif AI enrichment failures with `opencode/deepseek-v4-flash-free` when the model returns a complete template card as plain text instead of strict JSON.
- Added safer motif enrichment parsing: direct JSON, fenced JSON, balanced JSON objects, conservative trailing-comma cleanup, and a template-text fallback. Random non-template text still fails instead of being treated as success.
- Replaced the raw "unparseable JSON" failure with a Chinese retry/model guidance message.

### Changed

- Reworked the motif detail/archive pane for readability: wider default panel, non-truncated long concept names, clearer stats, compact local star map, related-node chips, and larger single-column edit fields for tags, aliases, and notes.
- Made version-related API tests read the current app version from `version_info.py` so patch releases no longer break update-check tests through stale hard-coded values.
- Updated public documentation links and installer names to `0.1.26`.

### Verification

- Real OpenCode smoke test: `opencode/deepseek-v4-flash-free` created an isolated test motif, generated an AI enrichment draft, saved it to the motif note, verified required short-card headings, deleted the motif, and confirmed no test motif remained.
- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- e2e/motifs-flow.e2e.ts --workers=1`
- `npm run test:e2e -- --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.26_x64-setup.exe`
  - SHA256: `1A290FDB2E53E6067D1E983C2531BAA65D44A53A6B9E09C01BC875BFF9EE93ED`
- `LivingToTell_0.1.26_x64_zh-CN.msi`
  - SHA256: `A3F83674FACFAE3D79906A8E6A1CD05478A7D9A804A1950F105C9258FDB96442`

## 0.1.25 - Motif AI Enrichment (2026-06-28)

### Added

- Added AI Enrich to the Motif Star Map detail pane. Existing motifs and newly typed concepts can generate a compact writing-oriented concept card before anything is saved.
- Added the motif enrichment draft API with profile selection, optional excerpt context, optional web-context request wording, strict JSON parsing, and Chinese provider-error copy.
- Added motif enrichment capability metadata so the frontend can detect backend support.

### Changed

- Motif AI drafts now keep the user's typed concept as the authoritative motif name even when the model rewrites the JSON `concept` field.
- Motif detail refresh now loads excerpts and local graph data sequentially to avoid shared SQLite connection contention after saving.
- Duplicate source-excerpt repair now keeps the row whose current source range is already correct before falling back to timestamps and id ordering.

### Verification

- Real OpenCode smoke test: `opencode/deepseek-v4-flash-free` generated an AI enrichment draft, saved it as a test motif, verified the note template through the API, and deleted the test motif.
- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`

### Release artifacts

- `LivingToTell_0.1.25_x64-setup.exe`
  - SHA256: `0B70F96BB533BAFF00C342635E45373D0D05F8B14CCA13808F1605EF39FD94BC`
- `LivingToTell_0.1.25_x64_zh-CN.msi`
  - SHA256: `0C301DEE8BADF8D09A1079371AE0F0699228DBFA1DC693EE68CF84B58726F339`

## 0.1.24 - Export, Backup, Long-Form Planning, and Sample Project (2026-06-28)

### Added

- Added an explicit disposable sample project from the Date welcome checklist. It creates sample articles, a collection outline, a reference passage, an article note, and a scene AI Card only after the user asks.
- Added sample-project state, create, and remove APIs. Removal uses only the marker-recorded entity IDs and never deletes by title or tag.
- Expanded Export & Backup into a recovery-centered surface with safety summary, restore-point selection, backup/checkpoint age, local backup reminder threshold, and real data-path cards.
- Added recent article and recent collection export shortcuts from the Export & Backup center.
- Added a collection planning board that groups outline cards by status for long-form project review.
- Added Playwright coverage for the sample project panel, backup restore planner, and collection planning board.

### Changed

- The onboarding checklist remains state-based and does not create data automatically. The sample project is optional and removable.
- Collection headers now show stronger long-form progress context, including linked outline count, target words, linked article words, and progress percentage.
- The backup page now prioritizes restore confidence before raw backup lists, while keeping existing backup/checkpoint create, delete, and restore actions.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py::test_tauri_app_version_capabilities tests\test_tauri_mvp_api.py::test_tauri_onboarding_sample_project_is_explicit_and_disposable -q`
- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\services\ai -q`
- `npm test -- --run`
- `npm run test:e2e -- --grep "backup center|collection planning board|dates calendar" --workers=1`
- `npm run test:e2e -- --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.24_x64-setup.exe`
  - SHA256: `CB38580324BD3FE6E6FBD0DAA52724B0E477AFE1858C3E55E861897A61CF70B2`
- `LivingToTell_0.1.24_x64_zh-CN.msi`
  - SHA256: `E82B6EF08907226C51AF53798903601255089F2C20AFBAF60EC70DFE00F3A3D1`

## 0.1.21 - Onboarding, Command Palette, and Reference Capture (2026-06-28)

### Added

- Added a first-run checklist on the Date view that reads local app state without creating sample data.
- Added AI settings diagnostics that distinguish provider, model, transport, credential source, local config checks, real request checks, and model-list source.
- Added AI request-size diagnostics in AI Tools, including character count, paragraph count, estimated tokens, selected model count, and long-request warnings.
- Added honest pending result cards while AI model comparison requests are still in flight.
- Reworked the command palette into grouped commands and search results for articles, collections, references, motifs, AI Cards, settings, backup, and common actions.
- Added reference-library overview cards and active-group summaries for source count, possible duplicate groups, usage distribution, authors, and character totals.
- Added AI chat capture previews so assistant replies can be reviewed and edited before saving as reference material or a new article.

### Changed

- AI chat assistant-message actions now use a quieter action row; article-note saving remains direct, while reference/article capture requires confirmation.
- Reference-library overview labels are kept compact in narrow panes to avoid broken Chinese text.
- The updated documentation screenshots now show the current AI Workspace, Reference Library, and Settings diagnostics surfaces.

### Verification

- Visual browser screenshots:
  - `output/playwright/0.1.21-visual/dates-onboarding.png`
  - `output/playwright/0.1.21-visual/settings-ai-diagnostics.png`
  - `output/playwright/0.1.21-visual/library-overview-after-nowrap.png`
  - `output/playwright/0.1.21-visual/ai-chat-capture-reference.png`
  - `output/playwright/0.1.21-visual/ai-tools-compare-result.png`
  - `output/playwright/0.1.21-visual/command-palette-ai.png`
- Real OpenCode smoke test: `opencode/deepseek-v4-flash-free` returned `OK`, `cost=0`.
- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\services\ai -q`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`

### Release artifacts

- `LivingToTell_0.1.21_x64-setup.exe`
  - SHA256: `9F33EF9B784B79E7143C520BF29244EFA9FEA9533BF01D28295AD7FE9CE19DBD`
- `LivingToTell_0.1.21_x64_zh-CN.msi`
  - SHA256: `B0D745AB1800E623364DC0B500146D3A2D029EA67CC66DD7BE88D280C8DC7AFB`

## 0.1.18 - In-App Update Flow (2026-06-28)

### Fixed

- Fixed version display mismatch after installing 0.1.17: the Tauri app binary was updated, but the bundled backend still reported `0.1.16` from `version_info.py`.
- Tauri now passes the app package version to the backend sidecar on startup, and the backend default version is synchronized to this release.
- Update-check failures now include safer diagnostics for proxy, timeout, SSL, and GitHub API failure cases.

### Changed

- Update checks still prefer GitHub Releases API, but now fall back to GitHub's `/releases/latest` redirect when the API fails.
- Settings and the update banner now offer **Download and Install**: the app downloads the installer internally, verifies the GitHub SHA256 digest when available, launches the installer, and exits.
- Browser download remains available as a fallback path.
- Update check responses report detected proxy routing in a safe `scheme=host:port` form without exposing credentials.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py -q`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.18_x64-setup.exe`
  - SHA256: `E60937E71DF462943B0AFC540A5A6BEDB617D0DEB929112EA7731911555E0BD6`
- `LivingToTell_0.1.18_x64_zh-CN.msi`
  - SHA256: `19159AFBDDF7355217E5CD62730A429555F6EB414AAEB6BFBEB8F955CE608362`

## 0.1.17 - AI Profile State Race Fix (2026-06-28)

### Fixed

- Fixed an AI profile state race where an older `/api/settings/ai/profiles` response could overwrite newly imported local profiles with an empty list.
- AI Tools now ignores stale AI profile refresh responses, so Settings -> AI Tools -> Manage Config -> AI Tools keeps imported model comparison profiles visible.

### Verification

- `npm run test:e2e -- e2e/settings-actions.e2e.ts --workers=1`
- `npm test -- --run`
- `npm run build`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.17_x64-setup.exe`
  - SHA256: `6A4CCEA6EDEFADCF18BE2B1C6A831DD0BA03299FF6281E762C8635A41E67D5C7`
- `LivingToTell_0.1.17_x64_zh-CN.msi`
  - SHA256: `0023FA511DBBAA3496E6C7BD5A50830028F78C34E6E7C733E65AB0DC3672C46F`

## 0.1.16 - AI Profile Workflow Polish (2026-06-28)

### Changed

- Settings no longer scans local AI configurations automatically when opening the page. Local OpenCode, Codex/OpenAI, and Gemini discovery now runs only when the user clicks the scan action.
- AI profile creation and editing now open in a modal dialog with an explicit cancel path instead of expanding an inline form at the bottom of the settings page.
- Discovered local AI profile candidates can be removed one by one or cleared from the current scan results without touching local auth/config files.
- AI Tools now refresh saved AI profiles when the page regains focus or visibility, reducing the need to press Refresh after changing profiles in Settings.
- The AI profile refresh notice is now scoped to the model comparison area and auto-clears instead of staying in the global task notice region.

### Fixed

- Fixed profile updates dropping `source_key`, which could make future local imports create duplicate profiles instead of updating the existing imported profile.
- Fixed OpenCode local credential checks so a temporary `opencode auth list` failure is not shown as hard unavailable when the known local auth file exists and real `opencode run` requests still work.
- Kept Gemini local discovery honest: unavailable Gemini configurations remain marked unavailable and are not reported as working.

### Verification

- Real local OpenCode probe with `opencode/deepseek-v4-flash-free`: success, `transport=opencode_cli`, `cost=0`.
- Real local Codex/OpenAI probe from `~/.codex/config.toml`: success, `transport=openai_responses`.
- Real local Gemini probe: unavailable; the app reports the failure as a diagnostic instead of presenting fake success.
- `D:\anaconda\envs\writer\python.exe -m pytest tests\services\ai\test_opencode_cli_provider.py tests\services\ai\test_preflight.py tests\test_tauri_mvp_api.py::test_tauri_ai_profiles_crud_and_validation tests\test_tauri_mvp_api.py::test_tauri_ai_profiles_discover_and_import_local -q`
- `npm test -- --run`
- `npm run test:e2e -- --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.16_x64-setup.exe`
  - SHA256: `94649DE2A466D32DE287DB2F71180990B06D95E31E9FE2515F805C0583F11B88`
- `LivingToTell_0.1.16_x64_zh-CN.msi`
  - SHA256: `FA13E700542BDE741E3B1DBE6020EA0630D4E3E9443289A8A8448CFD304521F2`

## 0.1.15 - AI Profile Discovery And Comparison Polish (2026-06-28)

### Added

- Added local AI profile discovery for OpenCode, Codex/OpenAI, and Gemini local configuration sources.
- Added one-click import/update for discovered local AI profiles without storing raw API keys.
- Added AI Tools profile refresh so newly saved profiles can be picked up before running a comparison.

### Changed

- AI profile cards now preserve a `source_key` so repeated local imports update existing profiles instead of creating duplicates.
- Settings now labels discovered local configs as importable rather than remotely verified; real provider availability remains checked by the explicit live test request.
- The AI profile setup surface is more compact, with discovered profiles, import/update actions, and manual editing in one place.

### Fixed

- Settings writes now explicitly commit key/value changes so profile saves persist across new SQLite connections and app restarts.
- Added regression coverage for profile persistence across connections and local profile import/update behavior.

### Verification

- Real local OpenCode probe with `opencode/deepseek-v4-flash-free`: success, `transport=opencode_cli`, `cost=0`.
- Real local Codex/OpenAI probe from `~/.codex/config.toml`: success, `transport=openai_responses`.
- Real local Gemini probe from `~/.gemini/.env` with `https://elysia.h-e.top`: remote rejected the request; the app surfaces a Chinese diagnostic instead of raw HTML/403.
- `D:\anaconda\envs\writer\python.exe -m pytest -q`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.15_x64-setup.exe`
  - SHA256: `1F1481F331AD11967DDDD7C00DEC359F32785CAB1EC5A27E7272940C384E3584`
- `LivingToTell_0.1.15_x64_zh-CN.msi`
  - SHA256: `D42DF58B95AD827AF4FAA62BC1ABAC22EF0B1D14CB9DF0163795FFDF690387FE`

## 0.1.14 - AI Model Comparison And Workflow Rollback (2026-06-27)

### Added

- Added AI provider profiles in Settings, stored as local JSON settings without raw API keys.
- Added AI Tools multi-model comparison for up to three selected profiles, including per-result size, paragraph, latency, token, and cost statistics when available.
- Added OpenAI-compatible `chat_completions` wire support for profile-based providers such as DeepSeek-style endpoints while keeping the existing global default behavior intact.

### Removed

- Removed the article-side AI revision workbench from the article context pane.
- Removed AI card combination generation from the AI Cards page.

### Changed

- AI Tools now require selecting a winning model result before copy, replace, or insert actions use generated text.
- Single-model AI Tool runs now use the same compare-result path as multi-model runs so result handling stays consistent.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest -q`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.14_x64-setup.exe`
  - SHA256: `8A36A48B123C88C526E01CA933378D046681AE877FC690D67B4B15E08CDFABCA`
- `LivingToTell_0.1.14_x64_zh-CN.msi`
  - SHA256: `24C4024641FC6239DB42429207CBCBEA29B4344E6C73BBC924878CCB1185EE16`

## 0.1.13 - Revision Workbench And App Workflow Upgrade (2026-06-27)

### Added

- Added an in-article AI revision workbench with selected-text, current-paragraph, and full-article scopes.
- Added AI revision tasks for polish, compress, expand, restrained rewrite, and logic checking, with explicit preview before write-back.
- Added automatic article history snapshots before AI revision workbench write-back.
- Added manual AI context selection in the article revision workbench for article notes, AI cards, and reference passages.
- Added collection outline progress summaries with total outline items, status counts, linked article count, target word total, and current linked-article word count.
- Added collection outline filters by item type, status, and unlinked items.
- Added Markdown export for the currently filtered collection outline.
- Added global Ctrl+K search across articles, collections, reference passages, motifs, and AI cards while keeping existing quick commands.
- Expanded the backup page into an Export & Backup center with data paths, backup/checkpoint paths, open-directory actions, and current article/collection export shortcuts.
- Added AI card combination generation for manually selected style, character, and scene cards, with preview-only generation and explicit actions to copy, save as article, save as note, or save as card.

### Changed

- The backup navigation label now reflects the broader Export & Backup workflow.
- AI card combination generation and article revision use the shared AI task API path instead of a private provider branch.
- Collection outline export and filtering remain frontend-only and do not mutate user outline data.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest -q`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.13_x64-setup.exe`
  - SHA256: `6C2CBB7B89539EC8663066CDD1D2CA1891A3B591B33F716642A6AAF228470AFC`
- `LivingToTell_0.1.13_x64_zh-CN.msi`
  - SHA256: `5AA95D4ADA786B72CF9E346D7E2855E74F1CA6083A126110EAA2C98DB8A53BC0`

## 0.1.12 - Version History And Collection Outline (2026-06-26)

### Added

- Added article version history in the article context pane.
- Added manual checkpoints with labels, article title snapshots, tag snapshots, word counts, and character counts.
- Added automatic AI-before-apply snapshots so AI write-back actions preserve the previous manuscript body before updating an article.
- Added pre-restore snapshots so restoring an old body still leaves a rollback point for the current body.
- Added a paragraph-level comparison view for saved versions, with restore, clone-as-new, copy, and delete actions.
- Added a collection-level outline tab for long-form projects.
- Added outline items for part, chapter, scene, and note planning inside each collection.
- Added outline status, summary, point of view, timeline, setting, tags, target word count, linked article, reorder, and delete support.
- Added create-linked-article and link-existing-article flows from outline items.
- Added backend capabilities for `article_versions` and `collection_outline`.

### Changed

- Collections now support both manuscript article ordering and project planning in the same collection surface, matching the model that a collection can be a novel, essay group, diary group, or other long-form container.
- AI apply actions now use the shared article version API before mutating article content.
- Existing article versions remain compatible; new metadata columns are added through the SQLite migration path.

### Verification

- `D:\anaconda\envs\writer\python.exe -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

### Release artifacts

- `LivingToTell_0.1.12_x64-setup.exe`
  - SHA256: `8D5F15D102D12437EDEE06BF977E08FB864411E1BB7FDCD70EC1826B301D1E57`
- `LivingToTell_0.1.12_x64_zh-CN.msi`
  - SHA256: `0925169817F26B46986DBA8922621BF719FB548B85B1436417FFBFB51C6214C1`

## 0.1.11 - Update Buttons And Article Warning Fix (2026-06-26)

### Fixed

- Fixed the update notice actions so `下载安装包` and `查看发布页` actually open the system browser in the installed app.
- Fixed the article page falsely showing “这篇文章已不存在，已刷新文章列表。” when a side-panel request briefly returned `404` even though the article itself still existed.
- Fixed article-side note and collection actions so a disproved article `404` no longer escalates into a misleading missing-article warning.

### Changed

- Public update checks are now ready for a real `0.1.10 -> 0.1.11` upgrade path, and the next test release can still be exercised against a newer version.

### Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

### Release artifacts

- `LivingToTell_0.1.11_x64-setup.exe`
  - SHA256: `49D5FEC047A95CD4BC272A0AD36FBA295139C6E094C43F04E3307B5FE5365790`
- `LivingToTell_0.1.11_x64_zh-CN.msi`
  - SHA256: `C98A4B0BD52A6BA61DD7F0BD732208E3A8BB27BDE4E61EAFEF4CF4B24773B625`

## 0.1.10 - Article Not-Found False Alarm Fix (2026-06-26)

### Fixed

- Fixed the article page falsely showing “这篇文章已不存在，已刷新文章列表。” when side-panel requests briefly returned `404` even though the current article still existed.
- Fixed article-side `404` handling to verify the article itself before escalating the failure into a global “article missing” notice.
- Fixed article note / collection actions so a disproved article `404` no longer turns into a misleading missing-article warning.

### Changed

- Update-notice testing now continues to work from `0.1.9` to `0.1.10`, so the current public build can verify the new update-check flow against a real newer release.

### Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

### Release artifacts

- `LivingToTell_0.1.10_x64-setup.exe`
  - SHA256: `FC55CF8DAE97190224669D4852EEAA095CE6BAD837FA034E6B463CF346A2C01C`
- `LivingToTell_0.1.10_x64_zh-CN.msi`
  - SHA256: `1B0E81E6F5EB657B002F2A5B399FFF6CA9804F3FDD6FC08E3A6A77BE657B41C3`

## 0.1.9 - Update Notice And Release Flow Update (2026-06-25)

### Added

- Added a GitHub Release update-check endpoint that reports the current app version, the latest published version, release notes, and the preferred installer download.
- Added an app-shell update banner that appears after startup when a newer public release is available.
- Added a dedicated About and Updates section in Settings with manual update checks, release notes, and direct download/open-release actions.

### Changed

- Public update handling now tells users when a newer version exists instead of leaving them to check releases manually.
- Update checking is silent when used as a background startup task and only surfaces an error copy when the user explicitly checks for updates.
- The public release flow still uses installers, but the app now opens the correct installer or release page automatically.

### Fixed

- Fixed the release-check UX so users are no longer left guessing whether a newer build is available.
- Fixed the user-facing copy around updates so it clearly explains that writing data remains safe and the installer is the actual update path.

### Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

### Release artifacts

- `LivingToTell_0.1.9_x64-setup.exe`
  - SHA256: `C412C5610CE44BF57976018049EBD949899F1CCF8CA664037C328CCB3F65D5BC`
- `LivingToTell_0.1.9_x64_zh-CN.msi`
  - SHA256: `EDF3B001407AF8343F09427E013ECD856D8C19B842FCF9B0C8D00EF373710910`

## 0.1.8 - Layout And AI Card Quality Update (2026-06-25)

### Added

- Added reusable resizable pane controls for dense windowed layouts.
- Added persistent pane widths for Articles, AI Workspace, AI Cards, Reference Library, Collections, and Motif Star Map surfaces.
- Added a shared right-click context menu for destructive actions that already had a visible delete button.
- Added right-click delete entry points for articles, article notes, AI cards, AI task presets, reference passages, collections, collection articles, motifs, motif excerpts, backups, and checkpoints.
- Added persisted AI Card tags with a database migration for existing local databases.

### Changed

- Improved windowed-mode behavior so side panes can be adjusted instead of forcing fixed widths that can obstruct content.
- Tightened context menu styling for a calmer desktop-tool feel.
- Removed public AI Card sample restore controls.
- Stopped AI Card list/search requests from automatically re-seeding built-in sample cards.
- Deprecated the old AI Card preset generation endpoint; it now returns a clear `410` response instead of recreating samples.

### Fixed

- Fixed AI Card tags disappearing after save by storing them in `ai_cards.tags_text`.
- Fixed AI Card tag search so saved tags participate in card search.
- Fixed the product behavior where built-in AI Card samples could reappear after users deleted them.
- Fixed rigid windowed layouts across the main writing and knowledge-management surfaces.

### Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

### Release artifacts

- `LivingToTell_0.1.8_x64-setup.exe`
  - SHA256: `2DB5EC63E7FE936F58E1ECC4586D03D173F5A74E83E470B34B8FF027103EE102`
- `LivingToTell_0.1.8_x64_zh-CN.msi`
  - SHA256: `E9387AE7A42CD0A1AB1F9427BD794D1CAAE7250E1892EB4388DA791A60671578`

## 0.1.7 - Living to Tell Major Preview (2026-06-20)

### Added

- Added the public brand **Living to Tell / 活着为了讲述**.
- Added copy-only migration from the old Writer data directory to `%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3`.
- Added safe demo-data screenshot capture so public screenshots do not include private writing, account paths, or local credential files.
- Added migration tests for the new app data path.
- Added Data and Storage settings that show the current data directory, SQLite database, backup folder, checkpoint folder, and custom-directory status.
- Added copy-based data-directory migration so users can switch storage locations without deleting the old folder.
- Added a light Tauri startup splash window so cold starts show progress instead of a blank window.
- Added article-scoped AI chat with standing instructions, copy actions, and save-reply-as-article-note actions.
- Added fixed-template AI Cards for style, character, and scene cards.
- Added AI-assisted card draft generation with preview-before-save behavior.
- Added manual scene-module search and attachment in the AI workspace.
- Added a real AI provider test request in Settings, separate from the local credential/configuration check.
- Added OpenCode local-auth support through the local `opencode auth login` session.
- Added live OpenCode model fetching in Settings. Current OpenCode models include `opencode/big-pickle`, `opencode/deepseek-v4-flash-free`, `opencode/mimo-v2.5-free`, `opencode/nemotron-3-ultra-free`, and `opencode/north-mini-code-free`.
- Added first-run welcome checklist entries for creating articles, saving references, configuring AI, opening article chat, and reading data/backup notes.
- Added the Motif Star Map for saving selected article/reference text into motifs, exploring co-occurrence, and jumping back to source anchors.
- Added motif excerpt deduplication and repair for position drift after article edits.

### Changed

- Updated the Windows app display name, window title, installer name, Tauri identifier, package metadata, README, user guides, TODO, and public release copy.
- Updated release assets to use English filenames: `LivingToTell_0.1.7_x64-setup.exe` and `LivingToTell_0.1.7_x64_zh-CN.msi`.
- Renamed the packaged backend sidecar to `living-to-tell-backend`.
- Kept old Writer data and preferences as compatibility sources; no old user data is deleted.
- Public AI chat UI now focuses on article context instead of exposing unfinished global or collection chat entry points.
- AI card types now focus on `style`, `character`, and `scene`; the old public `setting` card type is removed.
- Gemini configurations that use `sk-...` proxy keys with a custom base URL now automatically use the gateway-compatible `/v1/chat/completions` transport while staying configured as Gemini.
- OpenCode requests run through the same AI provider path as polish, chat, and AI Card generation, and report provider/model/transport/cost diagnostics.
- Reference-library line statistics now use non-empty paragraph counts where appropriate.
- Article list filtering now supports single-tag filtering combined with keyword search.
- The motif attach flow now uses right-click selection instead of opening automatically after a left-click selection.

### Fixed

- Removed the bad tracked `app-icon.png` file that contained HTML instead of image bytes.
- Updated installer process cleanup so upgrades can close both old Writer processes and new Living to Tell processes before copying files.
- Hid the installer/uninstaller app-data deletion option so uninstalling does not offer a dangerous one-click path to writing data.
- Fixed old backend sidecar leftovers by tightening process cleanup and adding backend capability/version checks.
- Replaced raw `Not Found` and `Failed to fetch` surfaces with user-facing backend connection/version messages.
- Sanitized AI provider HTML errors so 403 pages and raw proxy responses are not shown in the UI.
- Fixed Gemini proxy 403 failures caused by routing custom-base `sk-...` keys through Gemini-native endpoints.
- Fixed article position restore by using a reliable outer-scroll writing surface and separate read/edit position records.
- Fixed article epigraph saving so leading full-width indentation in the first body paragraph is preserved.
- Fixed context tag switching in the reference library.
- Fixed backend processes lingering after app exit.
- Fixed motif star map density controls, local graph label overlap, duplicate bottom index, and English `Motif not found` errors.
- Fixed motif excerpt deletion semantics so removing from one motif does not delete the same excerpt from other motifs.
- Fixed motif lookup after source-position drift so the same sentence reopens existing motif chips and historical duplicate anchors merge automatically.
- Fixed AI settings and AI card generation to report provider/model/transport diagnostics without exposing API keys.

### Verification

- `python -m pytest`
- `npm test -- --run`
- `npm run test:e2e`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- Real OpenCode probe through the app settings API with `opencode/deepseek-v4-flash-free`.
- Real gated Gemini probe with local configuration: `WRITER_RUN_LIVE_AI_TEST=1 python -m pytest tests\services\ai\test_gemini_provider.py::test_live_gemini_config_can_answer_minimal_probe -q`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

### Release artifacts

- `LivingToTell_0.1.7_x64-setup.exe`
  - SHA256: `FF6A5E37F45E0CACD07E6E41EB3AF54A1B1CC4BB803029944269DC8C1F20E78F`
- `LivingToTell_0.1.7_x64_zh-CN.msi`
  - SHA256: `BD1DB35B44477C8BF81DA4ED021D8F2EAAA78EC4F471FC5038A61C7D0EF1A4F5`

## 0.1.6 - Public Preview Final Fixes (2026-06-16)

### Added

- Added public screenshot assets for article writing, focus mode, collections, reference library, AI, and settings.
- Added a public-facing README structure with screenshots, features, download, quick start, AI setup, privacy, development, and roadmap sections.
- Added repeatable screenshot capture script at `tauri-mvp/scripts/capture-screenshots.cjs`.
- Added release notes for `tauri-v0.1.6`.
- Added article notes in the article context pane for reminders, fragments, and next-step ideas.
- Added focused controls for polish, rewrite, expand, and continue AI tools.
- Added per-tool AI writing presets.
- Added manual article-note and reference attachments for AI tool context.
- Added explicit AI writeback actions: replace, insert, copy, and return to the source article.

### Changed

- Changed GitHub Actions workflows to manual-only `workflow_dispatch` triggers.
- Public preview now forces light mode and hides dark mode UI entry points until the full dark theme is polished.
- Updated version metadata to `0.1.6`.
- Clarified that preview releases are built locally and uploaded manually instead of using automatic GitHub Actions builds.
- AI tool results now default to review-first behavior instead of automatic manuscript changes.
- Public TODO and README roadmap now reflect completed article notes, focused AI tools, and safe writeback.

### Fixed

- Fixed the Tauri close confirmation event by switching from the custom-protocol-like event name to `writer-confirm-close`.
- Fixed the close preference prompt so `ask`, `tray`, and `exit` paths are reachable from the window close button.
- Improved the tray-unavailable fallback so the prompt shows a clear message and lets the user confirm direct exit.
- Fixed the Windows title-bar close button so it no longer depends on the web UI receiving a close event.
- Fixed article AI writeback so selected body ranges can be replaced or appended without rewriting the whole article.

### Verification

- `python -m pytest`
- `python -m pytest tests\test_tauri_mvp_api.py -q`
- `npm test`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe python`

## 0.1.5 - Public Polish and AI Settings (2026-06-16)

### Added

- Added a cleaner focus mode for articles that hides surrounding panels and keeps only the writing area.
- Added a real "Start Writing" action on empty date pages, creating a new article for the selected date.
- Added Reference Library copy actions for passage text and full source citation.
- Added backend-backed AI settings for OpenAI-compatible providers, Codex local auth, Gemini API, local Gemini config, and Gemini CLI / OAuth.
- Added AI credential status and config validation without saving raw API keys.

### Changed

- Removed implementation-oriented epigraph helper copy from the public article UI.
- Removed unavailable Claude provider choices from the public settings UI.
- Updated public documentation for focus mode, reference copying, AI settings, and date writing actions.

### Verification

- `python -m pytest`
- `npm test`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`

## 0.1.4 - Writing and AI MVP Completion (2026-06-16)

### Added

- Added full daily quote display with a link from Dates to the matching Reference Library passage.
- Added Reference Library organization by source book or usage type, with persisted group mode and deep-link selection.
- Added article epigraph editing: detected opening epigraphs appear in a separate editing area while staying stored as plain text.
- Added single-article export for TXT, Markdown, and DOCX.
- Added AI Tool / Chat tabs. Chat supports one ongoing conversation for global, each article, and each collection.
- Added article and collection shortcuts into scoped AI Chat.
- Added AI Card filtering by type, source, keyword, and sort order.
- Added first-run close behavior choices: ask, minimize to tray, or exit directly.

### Fixed

- Moved focus-mode exit control to the top-right safe area so it no longer overlaps article titles.
- Preserved existing Writer SQLite data access in the Tauri backend while expanding article, collection, reference, and AI endpoints.
- Prevented article/collection AI chat from creating empty-scope conversations.

### Verification

- `python -m pytest tests\test_tauri_mvp_api.py`
- `npm run build`
- `cargo check --manifest-path tauri-mvp\frontend\src-tauri\Cargo.toml`

## 0.1.3 - Packaged API Fix (2026-06-15)

### Fixed

- Fixed the packaged Python sidecar returning `404 Not Found` for article, collection, library, AI, backup, and settings-related API routes.
- Fixed the release package so Tauri reads the existing Qt Writer database instead of showing an empty app surface.

### Verification

- Direct sidecar smoke: `/api/articles` returned existing articles from `%APPDATA%\Writer\Writer\writer.sqlite3`.
- Direct sidecar smoke: `/api/library/references` returned existing reference passages from the same database.

## 0.1.2 - UI and Localization Polish (2026-06-15)

### Fixed

- Fixed article find/replace so previous/next navigation selects the matching text in the editor instead of acting like a placeholder control.
- Removed remaining visible English from key Chinese-mode screens: AI, dates, library, backup, settings, command palette, quick capture, and find/replace.
- Reworked several buttons and empty states so actions are either wired, clearly disabled with an explanation, or removed.

### Changed

- Simplified the AI workspace copy and result actions for the current Tauri MVP surface.
- Updated public-facing documentation to describe articles, article collections, AI Cards, reference library, backup, and settings without legacy Work terminology.

### Verification

- `npm run build`
- `python -m pytest`

## 0.1.1 - Stabilization Pass (2026-06-14)

### Fixed

- Fixed AI Card API crashes caused by mismatched repository methods and fields.
- Fixed built-in AI Card samples so they are seeded as normal editable cards without duplicating on every launch.
- Replaced legacy Work-based collection endpoints in the Tauri UI flow with article-based collection endpoints.
- Fixed collection creation, article add/remove/reorder, entry membership lookup, and collection export endpoints.
- Fixed release sidecar port discovery: Tauri now reads `WRITER_PORT=...` from the backend and exposes the correct API base URL to the frontend.
- Removed static `localhost:8000` usage from active frontend API clients.

### Changed

- Rebuilt the Collections page as an article reading/order workspace with shelf, article cards, preview, export, and batch add.
- Added article right-context membership display and "add to collection" action.
- Changed the article right context pane from a draggable-width panel into a persisted show/hide panel.
- Improved Chinese localization for navigation, article context, collections, AI Cards, empty states, and action labels.
- Added visible error/notice states to AI Cards instead of silent console failures.

### Verification

- `python -m pytest tests\storage\test_article_collections.py tests\services\test_article_collection_export.py tests\test_tauri_mvp_api.py`
- `npm run build`
- `cargo check`

## 0.1.0 - Initial MVP (2026-06-13)

- Tauri shell with Vue frontend and FastAPI backend sidecar.
- Articles, Dates, Collections, AI, Library, AI Cards, Backup, and Settings surfaces.
- Shared Writer SQLite data layer.
