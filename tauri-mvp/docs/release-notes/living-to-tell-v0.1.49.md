# Living to Tell Preview 0.1.49

0.1.49 is a workflow-polish release. AI Edit now treats Reference Specimens, AI Cards, and Article Notes as equal author-selected context. Complex workspaces share one respectful tutorial system, the Reference Library is easier to read and navigate, and the Motif Star Map can hold author-confirmed concept relationships without pretending that AI suggestions are facts.

## Three deliberate AI context sources

- **Reference Specimens**, **AI Cards**, and current-article **Writing Notes** each have a large searchable picker with readable two-column cards, filters, full-content preview, staged multi-selection, and a fixed confirmation footer.
- More Requirements now contains presets, additional instructions, and advanced task parameters only. No reference source is hidden behind tiny checkboxes.
- Switching articles clears note selections so one article's reminders cannot be sent with another article. Specimens and cards remain selected only for the current AI Edit page session.
- Every explicitly selected model receives the same click-time attachment snapshot. Completed runs list attachment names and sizes without returning their text.
- Reference-specimen prompts still prohibit copying sentences or importing source people, facts, plot, and named entities.

## Tutorials that wait for the author

- Collections, AI Edit, Collection Agent, and Motif Star Map now share one tour system and three-state local preference: unseen, completed, or dismissed.
- A first visit shows only a small invitation. **Later** closes the invitation for the current visit, while **Do Not Show Again** persists the choice.
- Settings includes a tutorial center with status and restart controls for all four tours.
- Tours restore page state afterward and never create data, change drafts, or send AI requests.
- The public tutorial set has been re-recorded with synthetic content as seven flows: sample project, article writing, collection planning, references and motifs, AI profiles and editing context, Collection Agent, and export/backup.

## A calmer Reference Library

- Source title, author, purpose, tags, selected state, and passage text have a clearer visual hierarchy with less border noise.
- Reading mode uses a controlled line width, comfortable spacing, and stable actions; editing remains explicit.
- Search highlights title, author, tag, and passage matches while preserving an unsuccessful query until the author clears it.
- Arrow Up/Down changes selection, Enter opens the detail, and Escape leaves edit mode without taking normal keys from the passage editor.

## Author-confirmed motif relationships

- A motif pair can store one formal relationship: Echo, Contrast, Transformation, Contains, or General Association. Directed types preserve their source and target semantics.
- The D3 relationship map adds wheel zoom, panning, Fit, Center, density, selected-node focus, one-hop hover emphasis, direct labels, and a responsive details drawer.
- Real excerpt co-occurrence and formal relationships are merged into one visible edge. Removing either source keeps the edge while the other source still exists.
- **Discover Links** asks one selected AI profile to inspect the current motif archive plus at most 200 lightweight motif records. Article bodies are not sent by default.
- Existing-link and new-concept candidates start unchecked. Only applied candidates enter the database; new concepts are name-only empty nodes marked for later enrichment, and no follow-up AI call runs automatically.
- Candidate application is transactional, idempotent, and rechecks names and aliases to avoid duplicate concepts.

## Verification

- Python: `909 passed, 1 skipped` (the skipped case is the explicitly gated live Gemini quota test).
- Frontend: `25 files, 80 tests passed`.
- Mock browser suite: `78 passed` on Microsoft Edge.
- Isolated real-backend browser suite: `2 passed`.
- Production frontend build and locked Cargo check passed.
- Responsive and accessibility coverage includes 1024x768, 1400x900, and 1920x1080 in Chinese and English, with no serious or critical Axe findings.
- A real synthetic motif relationship discovery through `deepseek-v4-pro` and OpenAI Chat Completions succeeded in 40.350 seconds, returned 1 existing-motif candidate and 12 new-concept candidates, and left formal relationships unchanged before confirmation. GLM was not called or retried.

See the [0.1.49 quality report](../quality/0.1.49-quality-report.md) for packaging, installation, and publication evidence.

## Windows assets

- `LivingToTell_0.1.49_x64-setup.exe`
- `LivingToTell_0.1.49_x64_zh-CN.msi`

Preview installers remain unsigned. Download them only from this repository's GitHub Release page and verify the published GitHub SHA256 digest.
