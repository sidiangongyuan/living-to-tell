# Writer Basic Design v0.1

## 1. Purpose

This document captures the currently confirmed basic design for the first usable version of Writer.

It is intended to reduce ambiguity for the implementing agent.

## 2. Confirmed Product Shape

- the app is a Windows desktop personal writing tool
- the interface should feel like a minimal journal
- the core writing unit is a fragment or short entry
- AI is optional assistance, not the center of the interface
- prose accumulation matters more than daily diary rituals

## 3. Main Window Layout

The main window should use a two-pane layout.

### Left Pane

- recent fragments list
- search entry
- lightweight filters such as tags or recent scope later

### Right Pane

- current fragment editor
- title input
- body editor
- small metadata area for tags and timestamps

### Top-Level Actions

Keep actions minimal and visible:

- new fragment
- rewrite with AI
- references
- projects
- settings

## 4. Default Start Behavior

Confirmed behavior:

- the app opens to `recent fragments list + right-side editor`
- if there is no active content, the app auto-creates a blank fragment so the user can write immediately

This choice is intended to reduce writing friction.

## 5. Writing Model

The app should treat content as separate fragments rather than one endless notebook.

That means:

- each fragment is an independent stored item
- fragments are shown chronologically in the recent list
- a fragment can later belong to a project
- a fragment may have multiple AI-generated versions

## 6. Rewrite Interaction

Confirmed default behavior:

- when text is selected, AI acts on the selected text
- when nothing is selected, AI acts on the current fragment
- AI results are shown in a side-by-side comparison view
- generated text does not replace the original automatically
- the user explicitly accepts the generated version before it becomes the active text

## 7. Version Handling

The app should keep the original text and the generated result separately.

Recommended first-pass behavior:

- store original fragment body
- store generated candidate as a new version record
- let the user accept the generated text fully or partially in a later iteration

For the first implementation, full-fragment acceptance is enough.

## 8. AI Chat Positioning

AI chat is not part of the first usable version.

Current recommendation:

- rewrite flow first
- AI chat second

Confirmed decision:

- first usable release focuses on writing-specific rewrite actions only
- free-form AI chat is deferred to a later milestone

## 9. Reference Library Basic Behavior

Confirmed first-pass behavior:

- references are mainly added by direct paste
- source title is required
- source author is optional
- tags remain freeform
- the editor should later support attaching references through a lightweight picker

## 10. AI Settings Shape

Confirmed first-pass settings scope:

- simple settings mode only
- base URL
- model
- API key
- import Codex config

Defer advanced settings such as reasoning effort and low-level request tuning.

## 11. Screens That Another Agent Can Safely Build Now

The implementing agent can already build these with low ambiguity:

- main shell window
- recent fragments list
- fragment editor
- new fragment flow
- rewrite trigger entry point
- side-by-side comparison dialog
- simple settings page
- reference library page shell

## 12. Remaining Design Areas

No current blocker remains for implementation planning.

Future refinements may still settle:

- finer details of reference attachment from the editor
- whether partial accept of rewrite results is worth supporting later

## 13. Project and Export Decisions

Confirmed first-pass behavior:

- the app includes projects in MVP
- projects can contain lightweight chapter or section groups
- export defaults to accepted content only
- Markdown and TXT are the first export formats
