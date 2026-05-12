# Writer User Guide

Writer is a local-first desktop writing app for collecting fragments, developing long-form work, managing reference material, and using AI assistance only when you choose to send text to a provider.

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
3. Create a new fragment for today's writing.
4. Write normally; Writer autosaves fragments.
5. Use tags to make fragments easier to recover later.
6. Use the daily reference card as a prompt. It is selected from your existing reference library.

## 4. Quick capture flow

Use quick capture for fast notes that should not interrupt the main writing context.

- Default quick-capture hotkey: Ctrl+Alt+Backquote.
- Default main-window hotkey: `Ctrl+Alt+M`.
- Close-to-tray is enabled by default when supported.

A good quick-capture habit is to write first, organize later. Add tags or move the note into a longer work after the idea is safe.

## 5. Fragments

Fragments are the core unit of Writer.

Typical uses:

- a sentence
- a paragraph
- a scene seed
- a character note
- a memory or observation
- a style experiment

Recommended workflow:

1. Capture the fragment quickly.
2. Add tags when they are useful.
3. Search or filter fragments when building a larger work.
4. Save strong passages into the reference library when they should guide future writing.

## 6. Works and collections

Use **Works** for longer pieces and **Collections** for ordered groups of works.

Suggested process:

1. Create a work for a story, essay, chapter, or draft.
2. Add sections if the piece needs structure.
3. Include fragments when they become useful.
4. Save manual snapshots before major revisions.
5. Export as TXT, Markdown, or DOCX.
6. Add related works to a collection when preparing a set or manuscript.

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

1. Select the scope: fragment, selection, work, collection, reference material, or pasted text.
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

Before exporting, review the work title, section order, and any collection order.

## 10. Backup and privacy checklist

Before publishing screenshots, bug reports, logs, or exported examples:

- Use demo writing, not private writing.
- Do not include real API keys or OAuth tokens.
- Do not include account emails or cloud project IDs.
- Do not include local database files.
- Do not include local machine paths unless they are generic examples.

For security policy details, see [../SECURITY.md](../SECURITY.md).
