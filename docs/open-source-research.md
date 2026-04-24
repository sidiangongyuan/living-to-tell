# Writer Open-Source Research v0.1

## 1. Conclusion

There are relevant open-source projects worth learning from.

The best references are not perfect matches, but together they validate the main direction for Writer:

- local-first data storage
- minimal writing-first UX
- AI as optional assistance
- explicit version comparison instead of silent overwrite
- provider-config-driven AI integration

The strongest conclusion is not that we should copy any one project.

The strongest conclusion is that Writer should borrow a small set of proven patterns while keeping the MVP much smaller than the larger writing platforms.

## 2. Most Relevant Repositories

### Freenote

Repository:

- `celerforge/freenote`

Why it matters:

- directly positioned as an AI journal app
- emphasizes local storage and privacy
- keeps the interface distraction-free
- combines journal writing with AI-assisted search and summarization

Useful ideas to borrow:

- writing-first homepage
- local-first storage message in product positioning
- AI as a supporting layer rather than the whole product
- simple settings flow where AI works only after key setup

What not to copy:

- web-first stack direction
- broad note-taking ambition beyond the current writing product scope

### Manuscript

Repository:

- `DoktorDaveJoos/manuscript`

Why it matters:

- closest philosophical match on one key idea: AI should polish craft without replacing the author's voice
- demonstrates version history, diff views, and accept or reject revision workflows
- stores data locally and uses bring-your-own-key AI
- treats AI as an optional layer over a strong offline writing tool

Useful ideas to borrow:

- side-by-side comparison of original versus revised text
- explicit accept flow instead of automatic replacement
- usage and cost metadata per AI operation
- clear framing that AI is a tool, not the main creative engine

What not to copy:

- enormous feature scope around plots, story bible, analytics, publishing, and multi-provider routing
- full novel-platform complexity in MVP

### Obsidian Text Generator Plugin

Repository:

- `nhaouari/obsidian-textgenerator-plugin`

Why it matters:

- mature AI-writing integration with strong provider configurability
- uses templates and prompt flexibility rather than one hard-coded workflow
- validated by real usage and a much larger install base than niche journaling repos

Useful ideas to borrow:

- configurable provider model and endpoint settings
- prompt templates for different actions such as polish, summarize, continue
- AI actions attached to the writing surface rather than detached from it

What not to copy:

- multi-provider complexity on day one
- plugin-level power-user customization that would overload a minimal journal product

### manasCore

Repository:

- `Skywalker1080/manasCore`

Why it matters:

- directly about journaling with local-first design
- documents architecture decisions and tradeoffs clearly
- uses SQLite plus vector search for retrieval-backed AI features
- separates immediate writing from slower background AI processing

Useful ideas to borrow:

- immediate local save before any AI processing
- background or deferred enrichment for metadata later
- SQLite as the default persistence choice
- future path for retrieval over past entries if chat or memory features grow later

What not to copy:

- local model and hybrid routing complexity in MVP
- retrieval-heavy chat system before the rewrite flow proves useful

### Journl

Repository:

- `atomly/journl`

Why it matters:

- focused on turning writing into structured reflection
- separates editor, AI logic, and workflow layers clearly
- useful as a product reference even though the stack is not a fit for this project

Useful ideas to borrow:

- keep AI workflow logic separate from editor rendering logic
- make architecture entry points obvious for future contributors
- treat journaling and AI workflow as distinct but connected concerns

What not to copy:

- web SaaS architecture
- monorepo and backend overhead for a single-user Windows desktop app

## 3. Recommended Borrowed Patterns

Writer should explicitly borrow these patterns:

1. `Freenote`: distraction-light writing surface with local-first positioning
2. `Manuscript`: side-by-side revision comparison and explicit acceptance of AI edits
3. `Obsidian Text Generator`: provider-config-driven AI actions and prompt templates
4. `manasCore`: save-first architecture and a future path for retrieval features without adding them now

## 4. Recommended Technology Takeaways

These findings strengthen the current technical direction rather than replacing it.

### Keep

- Python + PySide6 for the desktop client
- SQLite for local persistence
- direct provider API integration with configurable base URL and model
- local storage of AI history, versions, and metadata

### Adopt as Design Rules

- save user writing locally before any AI request
- never overwrite original text automatically
- keep AI configuration explicit and editable
- keep chat optional and secondary to writing workflows
- store provider and model metadata with generated outputs

### Defer

- vector search
- local model fallback
- multi-provider switching UI
- RAG over the whole notebook
- analytics dashboards and complex publishing workflows

## 5. Concrete Product Implications

Based on this research, the current product plan should lean into these choices:

- main surface is editor-first, not chat-first
- first AI action is text rewrite, not general assistant chat
- result handling should be review-based, not inline automatic replacement
- settings should support provider configuration and Codex-style import
- future architecture should leave room for retrieval, but MVP should not depend on it

## 6. Scope Guardrail

The biggest risk revealed by the open-source landscape is overbuilding.

Projects like Manuscript show how quickly writing software expands into:

- structure boards
- dashboards
- character systems
- publishing pipelines
- heavy AI analysis

Those are useful signals for Phase 2 and beyond, but they should not distort the MVP.

## 7. Final Recommendation

Yes, there are open-source projects worth borrowing from.

The right move is:

- borrow workflow ideas from Freenote and Manuscript
- borrow configuration ideas from Obsidian Text Generator
- borrow architectural restraint from manasCore
- keep Writer's own implementation small, local-first, and rewrite-centered
