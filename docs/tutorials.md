# Living to Tell GIF Tutorials

These GIFs are generated from a clean Playwright demo profile. They do not contain private writing, local usernames, account emails, API keys, or a real database. They show the core workflow; for detailed instructions, see the [official user guide](user-guide.md).

Four complex workspaces also have in-app spotlight tours: Collections, AI Edit, Collection Agent, and Motif Star Map. A first visit shows only a small invitation; no tour creates data or sends an AI request. Restart any tour from **Settings → Interface & Tutorials**.

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

## 3. Collection Planning: From Manuscript Structure to Board

![Collection planning tutorial](../tauri-mvp/docs/assets/tutorials/03-collection-planning.gif)

Goal: organize multiple articles into one book project with a single structure tree and board.

Steps:

1. Open **Collections** and create or open a manuscript project.
2. If the interactive tutorial appears, use **Next** to walk through Manuscript Structure, Project Type, Unplanned Articles, Linked Article, Board, and Export; restart it later from Settings if needed.
3. In **Manuscript**, add top-level nodes such as parts, chapters, sections, essays, or scenes.
4. Select a chapter or group, then click **New Child**, or place **Unplanned Articles** under the selected node.
5. Select a structure node and edit title, type, parent, status, summary, target words, and linked article.
6. Switch to **Board** to scan idea, draft, revision, done, and parked items across the same tree.
7. Switch to **Export** to export the manuscript, or export a separate planning file for your own review.

Expected result: Collections use one clear manuscript structure tree; articles not yet in the tree stay in Unplanned Articles.

Safety note: removing an article from a collection does not delete the article. Linked Article only connects a structure node to a draft; it does not copy or move text. Once the tree has linked draft nodes, unplanned articles are not included automatically in manuscript export.

## 4. References and Motifs: From Excerpt to Star Map

![Reference and motif tutorial](../tauri-mvp/docs/assets/tutorials/04-reference-motif.gif)

Goal: save reusable reference material and connect recurring images, symbols, and source excerpts in the motif map.

Steps:

1. Save content, source title, author, usage, and personal notes in **Reference Library**.
2. Search highlighted title, author, tag, note, or passage matches; use Arrow Up/Down and Enter when navigating without the mouse.
3. Select text in an article or reference and right-click **加入意象星图**.
4. Open **Motif Star Map** and use zoom, pan, Fit, Center, density, and node focus.
5. Add an author-confirmed relationship manually, or open **Discover Links** to review unchecked AI candidates for existing motifs and name-only new concepts.
6. Open motif details to review source anchors and return to the original text.

Expected result: references preserve readable source context; motifs combine real co-occurrence and author-confirmed formal relationships without inventing AI edges.

Safety note: one excerpt can belong to several motifs. AI candidates do not enter the graph until selected and applied; new concepts start as empty nodes and are never enriched automatically.

## 5. AI Profiles and Article Editing Context

![AI profiles and article editing tutorial](../tauri-mvp/docs/assets/tutorials/05-ai-settings-edit.gif)

Goal: configure one reliable default profile, deliberately choose reference specimens, AI Cards, and current-article notes, then compare edits across explicitly selected models.

Steps:

1. In **Settings → AI**, review profile health, choose one default, and open the three-step profile wizard.
2. Run local checks first; send a minimal real test only for profiles you explicitly select.
3. Open **AI Edit** from an article or selection and choose Polish, Rewrite, Expand, or Continue.
4. In **Reference Context**, open each large picker as needed: Reference Specimens, AI Cards, and Article Notes. Search, preview, stage choices, then confirm them; nothing is attached merely because it was viewed.
5. Select one or more profiles. Every selected model receives the same frozen article and context snapshot.
6. Read the first successful result immediately, inspect the recorded context names, switch to the paragraph difference, and open the write-back preview. More selected models can mean longer waits and higher provider cost.
7. Open the article-side **AI Chat** drawer for discussion without leaving the draft.

Expected result: AI Edit uses the selected article, exact selected profiles, and only confirmed context. Output stays in preview until you explicitly copy or apply it, and article chat remains separate from write-back.

Safety note: local config existence does not prove remote model availability. Real tests can use tokens and cost money. Reconnection checks status without resending the provider request; switching articles clears note selections so they cannot leak into another draft.

## 6. Collection Agent: Conversation, Memory, and Proposals

![Collection Agent tutorial](../tauri-mvp/docs/assets/tutorials/06-collection-agent.gif)

Goal: use one collection-bound Agent as a long-running editorial workspace without turning every conversation into manuscript data.

Steps:

1. Open **Collections → Agent** and use the session list and Prompt index to return to earlier questions quickly.
2. Type `@` or choose **Reference** to attach only the structure node, article, AI Card, motif, or reference needed for the next turn.
3. Open the work panel to inspect what the next turn can read, the Project Bible, local drafts, and pending proposals.
4. Choose Discuss, Plan, Draft, or Review. Quick tasks such as **Diagnose Collection** open a model/context confirmation first; only **Confirm Run** sends a request.
5. Apply, defer, or reject proposals one by one. Only an applied memory update or a manual Project Bible save changes long-term canon.

Expected result: conversations remain searchable and sessions remain separate, while confirmed canon is shared across the collection.

Safety note: ordinary chat, rejected proposals, and unapplied drafts never become memory automatically. Leaving the tab reconnects to job state without resending the provider request.

## 7. Export and Backup: Restore Points First

![Export and backup tutorial](../tauri-mvp/docs/assets/tutorials/07-export-backup.gif)

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
