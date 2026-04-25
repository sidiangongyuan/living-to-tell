# M10A Release Notes

M10A adds a dedicated AI workspace on top of the M9A shell, so AI is no
longer limited to the older one-shot rewrite flow.

## Highlights

- **AI Workspace mode**
  Writer now exposes AI as a top-level workspace mode with its own screen in
  the navigation rail.

- **Tools and Chat tabs**
  The new workspace splits AI into two complementary surfaces: structured
  tool tasks for deterministic output shapes, and a free-form chat tab for
  scoped discussion.

- **Scope-bound threads**
  Chat threads are bound to the current fragment, work, collection, or a
  global scope, so follow-up messages stay attached to the writing object the
  user is actually discussing.

- **Structured task catalog**
  The Tools tab now supports polish, expand, continue, style transfer,
  summarize, outline, title suggestions, structure diagnosis, consistency
  check, and library Q&A.

- **Safe write-back paths**
  AI output can be previewed, written back into a fragment or section, or
  saved as a new fragment. Destructive section writes take a snapshot first.

- **Source-backed library Q&A**
  Library Q&A can answer against attached material and surface citations in
  the result area instead of dumping raw JSON back to the user.

## Workflow in this release

- Select a fragment, work section, work, or collection
- Enter the AI workspace from the navigation rail
- Run a structured task or start a scoped chat thread
- Preview the result, then apply it safely or save it as a new fragment

## Scope limits in M10A

- AI cards and saved task templates are wired at the schema and repository
  layer, but their dedicated UI management surface is intentionally deferred
- Only library Q&A may auto-attach search results; every other task keeps
  manual context control by default
- This is still a desktop widget release; streaming and richer review flows
  remain future work

## Validation notes

- Final audit closed the two last M10A workflow tails: stale fragment scope
  stealing AI binding from Works mode, and structured result rendering using
  the currently selected task instead of the originating request task
- Focused AI workspace UI regressions: `21 passed`
- Full test suite after the close-out fixes: `439 passed`
- The Windows portable bundle was rebuilt for this alpha release

## Packaging note

This alpha ships as the portable bundle in `dist/Writer/`, the versioned zip
`dist/Writer-0.2.0-alpha.5-portable.zip`, and the compatibility alias
`dist/Writer-portable.zip`.