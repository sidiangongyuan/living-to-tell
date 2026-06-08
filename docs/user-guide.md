# Writer User Guide

Writer is a local-first desktop writing app for writing articles, arranging collections, managing reference material, and using AI assistance only when you choose to send text to a provider.

## 1. Install and start

1. Download the latest Windows portable zip from the GitHub Releases page.
2. Unzip the archive.
3. Open the `Writer` folder.
4. Run `Writer.exe`.

The app stores its database in the platform user-data directory by default. Keep regular backups if you rely on Writer for daily work.

## 2. Recommended first-run setup

1. Open **Settings**.
2. Choose a language.
3. Review editor comfort options: font size, line height, paragraph spacing, content width, visual first-line indent, and typewriter mode.
4. If you use AI, configure one provider:
   - `env:OPENAI_API_KEY` for OpenAI-compatible providers.
   - `env:GEMINI_API_KEY` or local Gemini configuration for Gemini.
   - Gemini CLI / OAuth if you already use Gemini CLI locally.
5. Run one small AI test on non-sensitive sample text before using AI with private writing.

## 3. Daily writing flow

1. Open **Dates** from the left rail.
2. Use the calendar to select a day.
3. Create a new article for today's writing.
4. Write normally; Writer autosaves articles.
5. Use tags to make articles easier to recover later.
6. Use the daily reference card as a prompt. It is selected from your existing reference library.

## 4. Quick capture flow

Use quick capture for fast notes that should not interrupt the main writing context.

- Default quick-capture hotkey: Ctrl+Alt+Backquote.
- Default main-window hotkey: `Ctrl+Alt+M`.
- Close-to-tray is enabled by default when supported.

A good quick-capture habit is to write first, organize later. Add tags or develop the note into an article after the idea is safe.

## 5. Articles

Articles are the core unit of Writer.

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
3. Search or filter articles when you need to recover them.
4. Save strong passages into the reference library when they should guide future writing.

## 6. Collections

Use **Collections** for ordered groups of articles. A collection stores membership and order; removing an article from a collection does not delete the article itself.

Suggested process:

1. Write one or more articles.
2. Create a collection.
3. Add articles to the collection.
4. Reorder them and use the preview pane to check reading flow.
5. Export as TXT, Markdown, or DOCX.

## 7. Reference library

The reference library stores material you want to reuse or consult later.

Useful categories include:

- style examples
- imagery
- techniques
- characters
- settings
- source excerpts

The daily reference card on the Dates page is drawn from this same library. There is no separate quote database.

## 8. AI workspace

The AI workspace is designed as an optional assistant, not an automatic editor.

Recommended safety workflow:

1. Select the scope: article, selection, collection, reference material, or pasted text.
2. Choose a task such as polish, expand, continue, summarize, outline, or style transfer.
3. Review the prompt context before sending sensitive content.
4. Review the output before applying it.
5. Keep snapshots for major write-back operations.

AI providers receive the text you send. Do not send content that you are not comfortable sharing with the configured provider.

## 9. Export

Writer can export finished work as:

- TXT
- Markdown
- DOCX

Before exporting, review article titles, the collection note, and the article order inside the collection.

## 10. Backup and privacy checklist

Before publishing screenshots, bug reports, logs, or exported examples:

- Use demo writing, not private writing.
- Do not include real API keys or OAuth tokens.
- Do not include account emails or cloud project IDs.
- Do not include local database files.
- Do not include local machine paths unless they are generic examples.

For security policy details, see [../SECURITY.md](../SECURITY.md).
