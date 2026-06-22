# Living to Tell User Guide

Living to Tell is a local-first desktop writing app for writing articles, arranging collections, managing reference material, and using AI assistance only when you choose to send text to a provider.

## 1. Install and start

1. Download the latest Windows installer from the GitHub Releases page.
2. Run `LivingToTell_0.1.7_x64-setup.exe`.
3. Open **活着为了讲述** from the Start menu or desktop shortcut.

By default, the app stores its SQLite database at `%APPDATA%\LivingToTell\LivingToTell\living-to-tell.sqlite3`.

The Windows installer usually places app files under `%LOCALAPPDATA%\活着为了讲述`. App files and writing data are intentionally separate.

Uninstalling the app does not delete the writing database, backups, or checkpoints. Use **Settings → Data and Storage** to open the current data folder, open backups, or migrate the data directory to another local folder. Migration copies data and keeps the old folder intact.

If an old Writer database exists at `%APPDATA%\Writer\Writer\writer.sqlite3`, first launch copies it into the new location. The old database is kept unchanged.

## 2. Recommended first-run setup

1. Open **Settings**.
2. Choose a language.
3. Review close-button behavior: ask every time, minimize to tray, or exit directly.
4. If you use AI, configure one provider:
   - `env:OPENAI_API_KEY` for OpenAI-compatible providers.
   - `env:GEMINI_API_KEY` or local Gemini configuration for Gemini.
   - Gemini CLI / OAuth if you already use Gemini CLI locally.
   - OpenCode if you already ran `opencode auth login` locally. Settings can fetch live OpenCode models such as `opencode/deepseek-v4-flash-free`, `opencode/mimo-v2.5-free`, `opencode/nemotron-3-ultra-free`, `opencode/north-mini-code-free`, and `opencode/big-pickle`.
5. Use **Check Local Config** to confirm the credential source exists, then use **Send Real Test Request** to verify the provider, model, base URL, key, and transport with a short sample request.
6. Before using AI with private writing, still run your first real task on non-sensitive sample text.

## 3. Daily writing flow

1. Open **Dates** from the left rail.
2. Use the calendar to select a day.
3. Click **Start Writing** on an empty day, or open an existing article for that date.
4. Write normally; the app autosaves articles.
5. Use tags to make articles easier to recover later.
6. Use the daily reference card as a prompt. It is selected from your existing reference library.

## 4. Articles

Articles are the core writing unit.

Typical uses:

- a short piece grown from a sentence
- a complete scene
- an essay or short story
- a character note
- a memory or observation
- a style experiment

Recommended workflow:

1. Capture the article draft quickly.
2. Add tags when they are useful.
3. Keep temporary reminders in article notes.
4. Search or filter articles when you need to recover them.
5. Save strong passages into the reference library when they should guide future writing.

## 5. Collections

Use **Collections** for ordered groups of articles. A collection stores membership and order; removing an article from a collection does not delete the article itself.

Suggested process:

1. Write one or more articles.
2. Create a collection.
3. Add articles to the collection.
4. Reorder them and use the preview pane to check reading flow.
5. Export as TXT, Markdown, or DOCX.

## 6. Reference library

The reference library stores material you want to reuse or consult later.

Useful categories include:

- style examples
- imagery
- techniques
- characters
- settings
- source excerpts

The daily reference card on the Dates page is drawn from this same library. There is no separate quote database.

## 7. AI workspace

The AI workspace is designed as an optional assistant, not an automatic editor.

Recommended safety workflow:

1. Select the scope: article, selection, collection, reference material, or pasted text.
2. Choose a task such as polish, rewrite, expand, continue, summarize, outline, or title generation.
3. Review the prompt context before sending sensitive content.
4. Review the output before applying it.
5. Use replace, insert, or copy explicitly. AI output is not written back automatically.

AI providers receive the text you send. Do not send content that you are not comfortable sharing with the configured provider.

### AI Cards and Scene Modules

AI Cards store reusable writing context. They are meant to capture structure and guidance, not long source excerpts.

- **Style cards** capture prose texture, sentence rhythm, narrative distance, imagery preferences, and constraints.
- **Character cards** capture the character core, desire, fear, action pattern, voice, and relationship tension.
- **Scene cards** capture the scene prototype, trigger conditions, core conflict, key actions, emotional curve, narrative function, scene DNA, and replaceable elements.

New cards can insert a fixed template. You can also paste material into **Card Generator AI** to generate a draft, then review and save it as a new card or apply it to the current card.

In the AI workspace, scene modules are searched and selected manually. Scene cards are not sent to a provider unless you explicitly check them for the current task.

## 8. Export

Living to Tell can export finished work as:

- TXT
- Markdown
- DOCX

Before exporting, review article titles, epigraphs, collection notes, and article order inside the collection.

## 9. Backup and privacy checklist

Before publishing screenshots, bug reports, logs, or exported examples:

- Use demo writing, not private writing.
- Do not include real API keys or OAuth tokens.
- Do not include account emails or cloud project IDs.
- Do not include local database files.
- Do not include real local machine paths unless they are generic examples.

For security policy details, see [../SECURITY.md](../SECURITY.md).
