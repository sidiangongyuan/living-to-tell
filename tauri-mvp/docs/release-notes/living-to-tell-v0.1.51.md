# Living to Tell Preview 0.1.51

0.1.51 makes Collections behave like a real manuscript instead of a loose set of planning cards.

## A coherent manuscript structure

- General projects use Group → Chapter → Article.
- Novels use Part → Chapter → Scene.
- Essay Collections use Section → Chapter → Article.
- Nonfiction projects use Part → Chapter → Subsection.
- A chapter can directly link one draft while it is a leaf. When you need several drafts below it, the new split flow moves that draft to the first child and turns the chapter into a container.
- Parts and notes do not link drafts, and content leaves do not contain children.
- The same article can appear only once in one collection manuscript.

## Titles that follow the writing

- Once a structure node links an article, its visible title follows the article's current title.
- Renaming an article updates the manuscript tree, chapter content list, board, planning export, manuscript export, and Collection Agent context.
- Unlinked nodes keep their own planning titles.

## A board you can move

- Drag any structure card to Idea, Draft, Revision, Done, or Parked.
- Only the dragged card changes status; children and manuscript order stay where they are.
- A status menu remains available as a keyboard-friendly alternative.
- Chapter cards summarize descendant drafts and completion progress.

## Existing projects

- An unlinked legacy content node that already has children is safely normalized into a chapter when its position is unambiguous.
- Ambiguous or duplicate legacy arrangements are never silently detached or deleted. Collections show a local cleanup prompt instead.
- Tutorials and manuals now explain chapter containers, leaf chapters, article-title following, safe splitting, and board dragging.

## Verification

- Python: `914 passed, 1 skipped` (the skipped test is an explicitly gated live Gemini quota test).
- Frontend unit tests: `87 passed`.
- Microsoft Edge browser workflows: `79 passed`.
- Production frontend build and locked Cargo check passed.
- The packaged sidecar reported version `0.1.51` and both new collection capabilities from an isolated temporary database.

## Windows assets

- `LivingToTell_0.1.51_x64-setup.exe`
- `LivingToTell_0.1.51_x64_zh-CN.msi`

Preview installers remain unsigned. Download them only from this repository's GitHub Release page and verify the published GitHub SHA256 digest.
