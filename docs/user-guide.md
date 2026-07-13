# Living to Tell Official User Guide

Living to Tell is a local-first desktop writing studio for articles, collections, references, motifs, and AI assistance that only runs when you choose to send text. This guide is task-oriented: each section explains when to use the feature, the steps to follow, safety notes, and common mistakes.

For visual walkthroughs, see the [GIF tutorials](tutorials.md).

## 1. Install, Data, and Safety Boundaries

Use this to confirm where the app lives, where your writing lives, and what upgrades or uninstalls affect.

Steps:

1. Download the latest Windows preview from [GitHub Releases](https://github.com/sidiangongyuan/living-to-tell/releases/tag/living-to-tell-v0.1.49).
2. Run the recommended installer: `LivingToTell_0.1.49_x64-setup.exe`. The MSI asset is `LivingToTell_0.1.49_x64_zh-CN.msi`.
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
4. Click **打开作品集** to inspect sample articles, collection manuscript structure, reference material, article note, and scene AI Card.
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

## 4. Collections and Manuscript Structure

Use Collections to organize multiple articles into a book project. Collections now have one main line: **Manuscript Structure**. It controls hierarchy, order, planning status, linked drafts, and export.

Steps:

1. Open **Collections**.
2. The first visit shows a small tutorial invitation. Choose **Start Tutorial** to begin spotlight steps, **Later** to postpone, or **Do Not Show Again** to dismiss it. Restart Collections or any other workspace tour from **Settings > Interface & Tutorials > Tutorial Center**.
3. Create a collection with a title, description, and project type: General, Novel, Essay Collection, or Nonfiction. Use **Edit Info** when you later need to change the title or description.
4. In **Manuscript**, add top-level nodes such as parts, chapters, sections, essays, or scenes. Labels change by project type.
5. To put several articles under one chapter, select that chapter and click **New Child**, or place **Unplanned Articles** under the selected node.
6. One structure node directly links one article; use multiple child nodes for multiple articles.
7. Selecting a node opens its reading view first. Use **Edit Details** only when you need to change status, summary, point of view, timeline, setting, tags, or target word count.
8. Switch to **Board** to scan idea, draft, revision, done, and parked items across the same tree.
9. Create an article from a structure node, or link an existing article.
10. Export the collection as Markdown, TXT, or DOCX. Export prefers the manuscript tree.

Safety notes:

- A collection stores relationships, structure, and export order; it does not copy the article body.
- Removing an article from a collection does not delete the article.
- In an article's right context pane, use **Collections > Open** to return to its collection and locate that draft.
- Unplanned Articles belong to the collection but are not in the manuscript tree. Once the collection has linked structure nodes, unplanned articles are not included in manuscript export automatically.
- Title names the structure node; Type describes its role; Parent places it in the tree; Linked Article creates a relationship only and does not copy or move article text.
- Project type changes terminology only: novels use part / chapter / scene, essay collections use section / group / essay, and nonfiction uses part / chapter / section.

Common mistakes:

- **How do I put several articles under one chapter?** A chapter can link one article directly and also contain child nodes. Select the chapter, then create children or place unplanned articles below it.
- **Can I plan before writing articles?** Yes. Structure nodes can stay unlinked until you create or attach articles.

### Co-create with the Collection Agent

The Agent is bound to the current collection. It can explore a novel from zero, discuss alternatives, turn decisions into structure, write scene candidates, and review continuity. It never treats a conversation as canon and never writes a draft into the manuscript by itself.

The **Sessions** button controls the left session and prompt index. **Workspace** opens Context, Drafts, open proposals, and the Project Bible on the right; it is not an import-data command. Both panels collapse, and at ordinary desktop widths Workspace opens as a drawer instead of squeezing the conversation.

1. Open the collection's **Agent** tab and create a named session for a concrete line of work, such as `First-act discovery` or `Protagonist arc`.
2. Choose **Discuss**, **Plan**, **Draft**, or **Review**. The selected AI profile applies to the next run; the collection default is managed in **Workspace > Context**.
3. Type naturally. Use `@` only when the Agent needs a specific article, structure node, AI Card, motif, or reference passage. The Context panel shows what the next run can read.
4. In Draft mode, fill only the useful scene constraints: target scene, point of view, tense, approximate length, required beats, and things to avoid.
5. Generated prose is saved in the local Draft Library. Edit it there, request a variant, or leave the page and return later.
6. Apply a draft by creating a new article, appending to an existing article, or replacing one explicit, unique selection. Existing-article write-back checks for text drift and creates a version snapshot first.
7. Keep confirmed book facts in the **Project Bible**. Normal chat, session summaries, rejected proposals, and unapplied drafts do not enter long-term memory.
8. A complete author-style evidence cycle starts from your chapter draft and ends when you mark the revised chapter complete. After three new cycles the app offers, but never runs automatically, an Author Portrait update proposal.

When a model proposes a Project Bible update, common English and Chinese section names are normalized to the fixed schema. An unrecognized section is never written silently; a failed apply shows a readable message, and rejecting a proposal does not change memory.

Leaving the Agent tab does not cancel an active run. Returning reconnects to the stored run state without resending the provider request. **Interrupt** stops local waiting; a provider request already sent may still finish or incur cost.

## 5. Reference Library and Motif Star Map

Use References for reusable passages, source details, usage notes, and personal reading notes. Use Motifs to connect selected text to recurring images, symbols, or ideas.

Steps:

1. Open **Reference Library**.
2. Create a reference with content, source title, author, usage kind, and personal note. Existing references open in reading mode; click **Edit** to reveal editable fields.
3. Search across title, author, tags, notes, and passage text. Matching text is highlighted; outside the editor, use Arrow Up/Down to move, Enter to open, and Escape to leave edit mode.
4. Jump from the daily reference card back to the matching reference.
5. Select text in an article or reference, right-click, and choose **加入意象星图**.
6. Search existing motifs or create new ones, then save the excerpt.
7. Open **Motif Star Map**. Scroll to zoom, drag the canvas to pan, use Fit or Center, change display density, and click a node to focus its one-hop neighborhood.
8. In **Confirmed Relationships**, manually connect two existing motifs as Echo, Contrast, Transformation, Contains, or General Association. One pair stores one editable formal relationship.
9. Choose **Discover Links** when you want AI suggestions. The AI sees only the current motif archive and a lightweight index of up to 200 motifs. Existing-link and new-concept candidates start unchecked; only selected candidates are applied. New concepts become name-only empty nodes marked for enrichment.
10. Click **AI Enrich** in the motif detail pane to create a compact concept profile. Review the draft before saving; enrichment and discovery candidates never write automatically.
11. Removing an excerpt from a motif only unlinks the current motif; the same excerpt remains under other motifs.

Safety notes:

- References keep source context; motifs capture recurring image/idea relationships.
- The same source and selection reuses one excerpt instead of creating duplicates.
- If article edits shift the selection, the app resolves by text and context and merges duplicates within the same source.
- Formal relationships are author-confirmed and appear alongside real excerpt co-occurrence. AI candidates are not stored until selected and applied, and confirmed relationships are never labeled as AI edges.
- If co-occurrence and a formal relationship exist for the same pair, the map draws one merged edge. Removing either source preserves the edge while the other still exists.

Common mistakes:

- **Can one sentence belong to several motifs?** Yes. One excerpt can link to multiple motifs.
- **Will removing it from one motif delete it everywhere?** No. The default action unlinks only the current motif.

## 6. AI Edit, Article Chat, and AI Cards

Use **AI Edit** for polish, rewrite, expand, and continue on one real article or explicit selection. Use the article-side chat drawer for discussion, and AI Cards for reusable style, character, and scene guidance. Collection-level discussion and drafting stay in the Collection Agent.

Steps:

1. Open **Settings → AI**. Create a profile with the three-step wizard or scan local Codex, Gemini, or OpenCode configuration.
2. Choose one profile as the default. Single-model features use this profile unless the feature has an explicit temporary selector.
3. Run **Check All Locally** first. This checks local credential and login availability without contacting a model.
4. Select only the profiles you want to verify, then send a minimal real test. Real tests can use tokens and incur provider cost; each profile keeps its last health state and test time.
5. Open an article and choose **AI Edit**, or select text first and enter from the article toolbar. Direct entry to AI Edit asks you to choose an article; there is no arbitrary paste mode.
6. Choose Polish, Rewrite, Expand, or Continue.
7. Use the first-class **Reference Context** area to choose any combination of **Reference Specimens**, **AI Cards**, and **Article Notes**. Each source opens a large searchable picker with readable cards, full-content preview, staged multi-selection, and a fixed confirmation bar.
8. Reference specimens can be filtered by purpose; AI Cards by style, character, or scene; article notes by active or completed state, with pinned notes first. Changing articles clears note selections so notes cannot leak into the wrong draft, while specimens and cards stay selected for the current AI Edit page session.
9. **More Requirements** now contains only presets, additional instructions, and advanced task parameters. None of the three context sources is hidden there.
10. Select one or more profiles. Selecting a non-default profile replaces the sole default selection; the default returns only if you explicitly select it again.
11. Run the task and read the first successful result immediately. A failed model stays local to its status row and does not block other models. Leaving the page does not restart the task.
12. Switch between **Generated Result** and **Difference from Original**. The result records names and sizes from the frozen context snapshot without returning attachment bodies. Write-back always opens a preview, verifies that the article has not drifted, and creates an `AI_BEFORE_APPLY` version first.
13. In Articles, open **AI Chat** for discussion. Closing the drawer keeps the draft, thread, and in-flight reply. Copying or saving a reply remains explicit.
14. Open **AI Cards** to create style, character, or scene cards. Review generated card drafts before saving; choose cards directly from the AI Edit picker when they should guide a run.

Safety notes:

- AI providers receive the article/selection and optional context shown for the task you explicitly run.
- Local config checks are not remote availability proof. Only a successful real test request proves the model works.
- Multi-model requests contain exactly the selected profile IDs; the default profile is never injected silently.
- Reference specimens, AI Cards, and article notes are attached only after you confirm their pickers. Every model in that run receives the same frozen selection; attachment bodies are not echoed back in run metadata.
- Specimens guide writing method, style, structure, imagery, or rhetoric; they are not fact sources. The prompt forbids copying or near-copying sentences and importing specimen people, facts, plot, or named entities.
- Reconnection only checks task state. It never resends a provider request. Local cancellation cannot guarantee that a request already sent to a provider stops generating or billing.
- Article drift blocks positional write-back. Copy the result or rerun against the current article instead of forcing an unsafe replacement.
- Scene modules and other context are selected manually; unselected material is not sent to AI.
- AI Cards should store structure and guidance, not long source excerpts. Keep cards readable enough that you can reuse them as prompt context later.

Common mistakes:

- **Does OpenCode require saving a key in the app?** No. The app uses the local CLI session from `opencode auth login`.
- **Can I sign into ChatGPT inside the app?** No. Official OpenAI access uses an API key; local Codex access reuses an existing Codex login.
- **Why did a provider charge tokens after a timeout?** A provider can keep processing after the local wait ends. The app does not automatically resend on reconnect, which avoids duplicate billing.
- **Can AI overwrite my article automatically?** No. Write-back is always explicit.
- **Why is only part of an extremely long specimen sent?** One attachment has a 40,000-character send limit. AI Edit keeps purpose, tags, and the author note first, then includes as much specimen text as fits; the full saved specimen is never changed.

For actionable diagnostics by status code and access method, see [AI Setup Troubleshooting](ai-troubleshooting.md).

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
