# Writer Product Requirements v0.2

## 1. Product Positioning

Writer is a Windows-first personal writing assistant for daily reflections and fragment-based prose writing.

Its purpose is not public publishing or collaborative writing. The core goal is to help the user record thoughts whenever they arise, gradually accumulate them, and eventually shape them into a loosely structured prose collection, with prose as the primary long-form target.

The product should preserve the user's original thoughts while improving expression quality through AI-assisted polishing, expansion, and style guidance.

## 2. Target User

- Primary user: the author themself
- Usage mode: single-user, personal desktop software
- Writing background: non-professional literary writer
- Core need: convert rough thoughts into stronger prose without losing authenticity

## 3. Core Problems

The current problems to solve are:

- Thoughts appear daily but remain fragmented
- Raw writing often lacks rhythm, imagery, or structure
- Good phrases from books or quotations are hard to reuse as style references
- Long-term accumulation does not naturally become a coherent manuscript

## 4. Product Goals

### 4.1 Primary Goals

- Lower the friction of writing whenever an idea appears
- Preserve original thoughts and emotional truth
- Let AI polish and deepen the text rather than replace the author
- Let the user build a reusable library of stylistic references
- Gradually transform scattered entries into organized long-form writing

### 4.2 Non-Goals for MVP

- Multi-user collaboration
- Community publishing or social features
- Complex typesetting for print publication
- Mobile support
- Fully autonomous novel generation without user input

## 5. Core Usage Scenarios

### Scenario A: Daily Capture

The user opens the software and quickly writes a short reflection, fragment, memory, or idea without needing to fit it into a rigid daily template.

### Scenario B: AI Polishing

The user selects a paragraph and asks the system to lightly polish it while keeping the original meaning and voice.

### Scenario C: Style Guidance

The user imports reference sentences or passages from favorite works, tags them, and later asks the AI to borrow tone, rhythm, atmosphere, or sentence texture during rewriting.

### Scenario D: Long-Term Accumulation

After weeks or months, the user reviews entries by date, theme, or project and starts combining them into a chapter, section, or loose manuscript.

## 6. MVP Functional Requirements

### 6.1 Writing Workspace

- Create, edit, and delete entries or fragments at any time
- Support title, date, tags, and freeform body text
- Auto-save local drafts
- Keep the original text when AI-generated alternatives are produced
- Allow the user to compare original and rewritten versions
- Keep the writing flow minimal and distraction-light

### 6.2 AI Writing Assistance

- Polish text without changing the core meaning
- Expand a fragment into a fuller paragraph
- Continue writing from an unfinished idea
- Summarize a long entry into a theme or keyword set
- Rewrite in a selected tone or style direction
- Default to light literary polishing in MVP, with room to add stronger presets later

### 6.3 Reference Library

- Import quotes, passages, or sentence fragments manually
- Record source information such as book name, author, and notes
- Add custom tags like loneliness, summer, childhood, restraint, surreal
- Search and filter reference materials
- Select one or more references as style inspiration during rewriting

### 6.4 Manuscript Accumulation

- Group entries into a writing project
- Mark entries as candidate material for a future manuscript
- Create lightweight chapter or section containers
- Move selected entries into a chapter draft workspace

### 6.5 Export and Backup

- Export selected content to Markdown and TXT
- Allow manual backup of local data
- Keep data portable enough for future migration

## 7. Experience Principles

- The app should feel like a writing companion, not an automated content factory
- Every AI rewrite should remain editable and reversible
- The original text should always be visible or recoverable
- Style inspiration should guide tone, not copy source material
- The interface should prioritize calm, low-friction writing over feature density
- The visual style should lean toward a minimal journal rather than a complex writing studio

## 8. Suggested MVP Acceptance Criteria

- A user can create a daily entry and reopen it later with content intact
- A user can select an entry and generate at least one polished rewrite
- A user can save reference passages and retrieve them by tag or keyword
- A user can apply selected reference material during rewriting
- A user can collect multiple entries into a draft project
- A user can export a project or selected entry to Markdown or TXT

## 9. Phase 2 Candidate Features

- Timeline view for emotional or thematic development
- Better manuscript planning with cards or boards
- Character, place, and motif tracking
- AI-generated structural suggestions for combining fragments
- Similarity search for related passages
- DOCX export
- Local model support for privacy-sensitive writing
- Voice input or dictated journal capture

## 10. Product Risks

- Over-polishing may erase the user's authentic voice
- Style transfer may become imitation if constraints are unclear
- Long-term accumulation may become cluttered without strong organization tools
- AI output quality depends heavily on prompt design and reference retrieval quality

## 11. Confirmed Scope Decisions

- Platform priority is Windows desktop only
- The product is primarily for personal use
- First AI implementation can use cloud APIs
- The core writing unit is a flexible entry or fragment written whenever inspiration appears
- The primary long-form direction is a prose collection
- The default rewrite style is light literary polishing, not aggressive style transfer
- The interface should feel like a minimal journal

## 12. Working Assumptions in This Draft

- Platform priority is Windows desktop only
- The product is primarily for personal use
- MVP should prefer fast implementation over architectural overreach
- AI capability may start with a remote API and evolve later
