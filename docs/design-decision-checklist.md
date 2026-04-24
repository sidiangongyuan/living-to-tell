# Writer Design Decision Checklist v0.1

## 1. Purpose

This document is the short checklist for the planning conversations before implementation starts.

Each round should settle a small number of decisions. The goal is to prevent open-ended discussion and leave another agent with a concrete build target.

## 2. Decision Rounds

### Round 1: Writing Flow

Status:

- confirmed

Confirmed decisions:

- app opens to recent fragments list plus right-side editor
- app auto-creates a blank fragment when there is no active entry
- content is treated as separate fragments rather than one continuous notebook

Originally needed to confirm:

- what the home screen opens to by default
- whether the editor auto-creates a new fragment or requires clicking `New`
- whether fragments are shown as a timeline, list, or card stack
- whether the app should feel more like one continuous notebook or many separate entries

Proposed default:

- open to a recent fragments list plus editor
- auto-create a blank fragment when there is no active entry
- use a simple chronological list on the left and editor on the right
- treat content as separate fragments, not one endless notebook

### Round 2: Rewrite Interaction

Status:

- confirmed

Confirmed decisions:

- rewrite acts on selected text when possible, otherwise on the current fragment
- comparison uses side-by-side display
- generated text stays separate until explicit accept
- one generated candidate is enough for MVP

Originally needed to confirm:

- whether rewrite acts on selected text or full entry by default
- whether comparison is side-by-side, cards, or inline history
- whether the generated version replaces current text only after explicit accept
- whether one rewrite result is enough or whether multiple candidates are needed

Proposed default:

- act on selected text when possible, otherwise current fragment
- show original and generated text side by side
- keep generated result separate until explicit accept
- generate one candidate in MVP

### Round 3: Reference Library

Status:

- confirmed

Confirmed decisions:

- references are mainly added by direct paste
- source title is required
- source author is optional
- tags are freeform
- references should eventually be attachable from the editor through a lightweight picker

Originally needed to confirm:

- whether references are mainly pasted manually
- whether source title and author are required or optional
- whether tags are freeform or preset
- whether references can be attached from the editor without leaving the page

Proposed default:

- paste manually first
- source fields optional but encouraged
- tags freeform
- attach references through a lightweight picker from the editor

### Round 4: AI Settings and Chat

Status:

- confirmed

Confirmed decisions:

- first usable release ships rewrite actions first, not free-form AI chat
- settings stay simple in v1
- Codex config import should be included if implementation cost stays reasonable
- usage logs remain internal in the first version

Originally needed to confirm:

- whether AI chat is part of MVP 1 or a follow-up milestone
- whether settings are simple mode only or advanced mode plus raw config
- whether Codex config import is exposed in the first UI pass
- whether token usage or request logs should be visible to the user

Proposed default:

- ship rewrite first, chat second
- keep settings simple in v1
- include Codex config import in settings if implementation cost stays low
- keep usage logs internal, not user-facing, in the first version

### Round 5: Project and Export

Status:

- confirmed

Confirmed decisions:

- MVP includes projects plus lightweight chapter grouping
- export defaults to accepted content only

Originally needed to confirm:

- whether projects are needed in the first usable release or can wait
- whether chapters are real entities in MVP or just ordered groups
- whether export should include original plus AI versions or accepted version only

Proposed default:

- projects belong in MVP if implementation remains lightweight
- chapters are simple ordered groups, not advanced boards
- export accepted content only by default

## 3. Recommendation for Next Conversation

Planning rounds needed for MVP are complete.

That gives enough clarity for another agent to build:

- the project model
- the export behavior
- the final MVP boundary

## 4. Draft Basic Design Proposal

If no stronger preference emerges beyond already confirmed choices, use this as the initial basic design:

- main window split into left navigation and right editor
- left side shows recent fragments, search, and quick filters
- right side shows the current fragment editor
- top bar contains minimal actions such as new fragment, rewrite, references, and settings
- rewrite opens a comparison dialog instead of replacing text immediately
- references are primarily pasted into a dedicated library and later selected through a compact picker
- AI chat is deferred until the rewrite flow proves useful

## 4. Planning Outcome

The MVP now has enough product and interaction clarity for implementation to begin.

Remaining uncertainty is refinement-level, not blocker-level.
