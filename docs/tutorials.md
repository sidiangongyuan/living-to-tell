# Living to Tell GIF Tutorials

These GIFs are generated from a clean Playwright demo profile. They do not contain private writing, local usernames, account emails, API keys, or a real database. They show the core workflow; for detailed instructions, see the [official user guide](user-guide.md).

## 1. Sample Project: Understand the Full Workflow First

![Sample project tutorial](../tauri-mvp/docs/assets/tutorials/01-sample-project.gif)

Goal: use a disposable sample project to understand how articles, collections, references, notes, and AI Cards connect.

Steps:

1. Open **Dates** and review the welcome checklist.
2. Click **创建示例项目**.
3. Click **打开作品集** to inspect the full demo project.
4. Return to Dates and click **删除示例** when done.

Expected result: the sample project can be created, opened, and removed. Removal only deletes IDs recorded by the sample marker.

Safety note: sample content is never created automatically and is never deleted by title or tag matching.

## 2. Article Writing: Draft, Notes, Versions, Focus

![Article writing tutorial](../tauri-mvp/docs/assets/tutorials/02-article-writing.gif)

Goal: write from the Articles surface and create restore points before major edits.

Steps:

1. Open or create an article.
2. Write in the main editor; autosave handles normal drafting.
3. Use article notes for reminders and next-step ideas.
4. Open **Version History** and click **Save Current Version**.
5. Use focus mode when you want only the writing surface.

Expected result: body text, notes, and versions stay separate; focus mode removes surrounding panels.

Safety note: versions are meaningful checkpoints, not a record of every autosave.

## 3. Collection Planning: From Reading Order to Project Board

![Collection planning tutorial](../tauri-mvp/docs/assets/tutorials/03-collection-planning.gif)

Goal: organize multiple articles into a project and plan longer work with outline and board views.

Steps:

1. Open **Collections** and review article order plus preview.
2. Switch to **Outline** and edit parts, chapters, scenes, or notes.
3. Switch to **Planning Board** to scan idea, draft, revision, done, and parked items.
4. Select an outline item and edit summary, point of view, timeline, target words, and linked article.

Expected result: Collections become both a manuscript order and a long-form planning surface.

Safety note: removing an article from a collection does not delete the article.

## 4. References and Motifs: From Excerpt to Star Map

![Reference and motif tutorial](../tauri-mvp/docs/assets/tutorials/04-reference-motif.gif)

Goal: save reusable reference material and connect recurring images, symbols, and source excerpts in the motif map.

Steps:

1. Save content, source title, author, usage, and personal notes in **Reference Library**.
2. Select text in an article or reference and right-click **加入意象星图**.
3. Open **Motif Star Map** to inspect node sizes, colors, and links.
4. Open motif details to review source excerpts and return to the original text.

Expected result: references preserve source context; motifs preserve recurring creative relationships.

Safety note: one excerpt can belong to several motifs. Removing it from one motif does not remove it everywhere.

## 5. AI and AI Cards: Real Tests, Model Comparison, Structured Context

![AI and AI Cards tutorial](../tauri-mvp/docs/assets/tutorials/05-ai-cards.gif)

Goal: verify AI connectivity, compare multiple models, and keep reusable style/character/scene context in AI Cards.

Steps:

1. In **Settings → AI**, distinguish **Check Local Config** from **Send Real Test Request**.
2. Open **AI Workspace** and paste text.
3. Select up to three provider profiles and run one task.
4. Compare output length, paragraph changes, latency, tokens, and cost when available.
5. Open **AI Cards** to maintain style, character, and scene modules.

Expected result: AI output stays in preview until you choose a winning result and explicitly copy, replace, or insert.

Safety note: local config existence does not prove remote model availability. A real test request does.

## 6. Export and Backup: Restore Points First

![Export and backup tutorial](../tauri-mvp/docs/assets/tutorials/06-export-backup.gif)

Goal: confirm that you can recover before major edits, exports, or upgrades.

Steps:

1. Open **Export & Backup** and review the safety summary.
2. Click **Create Checkpoint** and give it a readable name and note.
3. Review the combined restore-point list of checkpoints and automatic backups.
4. Select a restore point and click **Restore Selected** only when needed.
5. Use shortcut exports for the recently opened article or collection.

Expected result: restore points, data paths, and export shortcuts are visible in one place.

Safety note: restore first creates a backup of the current database. Export files and database backups serve different purposes.

## Regenerate GIFs

From the repository root:

```powershell
node .\tauri-mvp\scripts\record-tutorials.cjs
```

The script starts or reuses the Vite dev server on `127.0.0.1:1420`, mocks all backend API responses, captures step frames, and composes GIFs with Python Pillow. Intermediate frames are deleted.
