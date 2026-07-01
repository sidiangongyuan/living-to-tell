# Living to Tell Official User Guide

Living to Tell is a local-first desktop writing studio for articles, collections, references, motifs, and AI assistance that only runs when you choose to send text. This guide is task-oriented: each section explains when to use the feature, the steps to follow, safety notes, and common mistakes.

For visual walkthroughs, see the [GIF tutorials](tutorials.md).

## 1. Install, Data, and Safety Boundaries

Use this to confirm where the app lives, where your writing lives, and what upgrades or uninstalls affect.

Steps:

1. Download the latest Windows preview from [GitHub Releases](https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.30).
2. Run the recommended installer: `LivingToTell_0.1.30_x64-setup.exe`. The MSI asset is `LivingToTell_0.1.30_x64_zh-CN.msi`.
3. Open **活着为了讲述** from the Start menu or desktop shortcut.
4. Open **Settings → Data and Storage** to review the active SQLite database, backup folder, and checkpoint folder.
5. Before major edits, open **Export & Backup** and create a backup or named checkpoint.

Safety notes:

- The writing database is stored at `%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3` by default.
- App files are usually installed under `%LOCALAPPDATA%\活着为了讲述`; this is separate from the writing database.
- Uninstalling the app does not delete articles, backups, or checkpoints.
- Data-directory migration copies data and keeps the previous folder intact.
- If old Writer data exists at `%APPDATA%\Writer\Writer\writer.sqlite3`, first launch copies it into the new location and keeps the old database unchanged.

Common mistakes:

- **Windows warns about an unsigned app**: preview builds are unsigned. Only run installers downloaded from this repository's Release page.
- **Will an update erase data?** Normal updates do not remove the writing database. Create a checkpoint before upgrading anyway.
- **Should I manually copy the database?** You can, but app-managed backups and checkpoints are clearer and easier to restore.

## 2. First Run and Sample Project

Use this to understand the full workflow without mixing demo material into your real writing.

Steps:

1. Open **Dates**.
2. Review the welcome checklist: first article, first reference, AI setup, backup location, and article chat.
3. Click **创建示例项目** if you want a disposable local walkthrough.
4. Click **打开作品集** to inspect sample articles, collection outline, reference material, article note, and scene AI Card.
5. Return to Dates and click **删除示例** when you are done.

Safety notes:

- The sample project is never created automatically.
- Removing the sample project deletes only exact IDs recorded by the sample marker.
- User-created content with the same title or tag is not removed.

Common mistakes:

- **The checklist disappeared**: open **Settings** and show the welcome checklist again.
- **Can I keep the sample project?** Yes. It is normal local content until you remove it.

## 3. Article Writing

Use Articles for essays, short stories, scenes, character notes, observations, style practice, and long drafts.

Steps:

1. Start from **Dates → Start Writing**, or open **Articles** directly.
2. Select an article from the list; the main editor is on the right.
3. Write normally. Articles autosave.
4. Add tags when they help future search.
5. Use article notes for temporary reminders, next-step ideas, or removed fragments.
6. Open **Version History** and click **Save Current Version** before major edits.
7. Use focus mode when you want only the writing surface.

Safety notes:

- Article notes do not enter the manuscript, export, or article search.
- Version history stores meaningful checkpoints: manual saves, before AI write-back, and before restore.
- AI output is never applied automatically. You must choose replace, insert, or copy.

Common mistakes:

- **Will first-paragraph indentation be lost?** Current saving preserves leading full-width spaces in the body.
- **I saw a Not Found while switching articles**: stale requests are ignored; if the current article is truly missing, the app refreshes the list and shows Chinese copy.
- **Writing near the bottom feels cramped**: the editor keeps bottom breathing room for long-form drafting.

## 4. Collections and Long-Form Outlines

Use Collections to arrange articles into a reading order or plan a longer project with parts, chapters, scenes, and notes.

Steps:

1. Open **Collections**.
2. Create a collection with a title and description.
3. Add existing articles.
4. Reorder articles and use the preview pane to check reading flow.
5. Switch to **Outline** and add parts, chapters, scenes, or notes.
6. Track status, summary, point of view, timeline, setting, tags, and target word count.
7. Switch to **Planning Board** to scan idea, draft, revision, done, and parked items.
8. Create an article from an outline item, or link an existing article.
9. Export the collection as Markdown, TXT, or DOCX.

Safety notes:

- A collection stores membership and order; it does not copy the article body.
- Removing an article from a collection does not delete the article.
- The outline enhancement uses existing collection outline fields and does not require a schema migration.

Common mistakes:

- **Is this ready for novel-length projects?** It is a V1 long-form planning surface: structure, status, target words, and linked articles. Richer publishing options can come later.
- **Can I outline before writing articles?** Yes. Outline items can stay unlinked until you create or attach articles.

## 5. Reference Library and Motif Star Map

Use References for reusable passages, source details, usage notes, and personal reading notes. Use Motifs to connect selected text to recurring images, symbols, or ideas.

Steps:

1. Open **Reference Library**.
2. Create a reference with content, source title, author, usage kind, and personal note.
3. Jump from the daily reference card back to the matching reference.
4. Select text in an article or reference, right-click, and choose **加入意象星图**.
5. Search existing motifs or create new ones, then save the excerpt.
6. Open **Motif Star Map** to inspect node size, color, and co-occurrence links.
7. Click **AI Enrich** in the motif detail pane to turn concepts such as mythic pattern, slave morality, or das Man into compact writing cards. Review the draft before appending or overwriting the note.
8. Removing an excerpt from a motif only unlinks the current motif; the same excerpt remains under other motifs.

Safety notes:

- References keep source context; motifs capture recurring image/idea relationships.
- The same source and selection reuses one excerpt instead of creating duplicates.
- If article edits shift the selection, the app resolves by text and context and merges duplicates within the same source.
- AI Enrich does not create related nodes or semantic edges automatically. Suggested relations are prompts for your review; star-map links still come from real excerpt co-occurrence.

Common mistakes:

- **Can one sentence belong to several motifs?** Yes. One excerpt can link to multiple motifs.
- **Will removing it from one motif delete it everywhere?** No. The default action unlinks only the current motif.

## 6. AI, AI Cards, and Multi-Model Comparison

Use AI for polish, rewrite, expand, continue, summarize, title generation, structure diagnosis, and reusable style/character/scene context.

Steps:

1. Open **Settings → AI** and choose OpenAI-compatible, Gemini, Gemini CLI, or OpenCode.
2. Click **Check Local Config** to verify local credential sources.
3. Click **Send Real Test Request** to verify the provider, model, base URL, key, and transport with a real minimal request.
4. For multi-model comparison, create or import GPT, Gemini, DeepSeek, or OpenCode profiles.
5. Open **AI Workspace**, choose the task, scope, and input text.
6. Select up to three profiles and run the same task.
7. Compare output length, paragraph changes, latency, tokens, and cost when available.
8. Pick a winning result before copying, replacing, or inserting.
9. Open **AI Cards** to create style, character, or scene cards. Use Card Generator AI for drafts, then review before saving.

Safety notes:

- AI providers receive only the text you explicitly send.
- Local config checks are not remote availability proof. Only a successful real test request proves the model works.
- Scene modules are searched and selected manually; unselected cards are not sent to AI.
- AI Cards should store structure and guidance, not long source excerpts.

Common mistakes:

- **Does OpenCode require saving a key in the app?** No. The app uses the local CLI session from `opencode auth login`.
- **Why did Gemini proxy keys produce 403 before?** `sk-...` gateway keys with custom base URLs now use a compatible chat completions transport.
- **Can AI overwrite my article automatically?** No. Write-back is always explicit.

## 7. Export & Backup Center

Use this before major edits, when exporting finished work, or when confirming the active data path.

Steps:

1. Open **Export & Backup**.
2. Review the safety summary: latest restore-point age, backup count, checkpoint count, and total size.
3. Click **Create Checkpoint** before major edits and give it a readable name.
4. Use **Create Backup** for a quick automatic backup.
5. Select a backup or checkpoint from the restore-point list.
6. Click **Restore Selected** only when needed. The app backs up the current database before restoring.
7. Use **Data Location** to copy or open database, backup, and checkpoint folders.
8. Use export shortcuts for the recently opened article or collection.

Safety notes:

- Restore uses only app-managed backups and checkpoints.
- The app creates a current-database backup before restore.
- Copying or opening paths does not modify data.

Common mistakes:

- **How often should I back up?** Daily or every 3 days for heavy writing; weekly is acceptable for lighter use.
- **Export vs backup?** Export produces human-readable TXT/Markdown/DOCX. Backup produces a SQLite restore point for the app.

## 8. Public Screenshots, Feedback, and Privacy

Before sharing screenshots, bug reports, logs, or exported samples:

- Use demo writing, not private writing.
- Do not include real API keys, OAuth tokens, account emails, or cloud project IDs.
- Do not include local database files.
- Avoid real local machine paths; use generic examples when needed.
- For bug reports, include the page, action sequence, visible error copy, and whether you had just switched articles or upgraded.

For security policy details, see [../SECURITY.md](../SECURITY.md).
