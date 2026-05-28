# Writer UI Design Refresh

This document captures the design direction for the alpha UI polish pass.
It borrows practical ideas from frontend design skills, but keeps the output
grounded in Writer's PySide6 desktop constraints.

## Direction

Writer should feel like a quiet literary writing desk, not a dense admin tool.
The interface should make long reading, revision, collecting passages, and
careful AI-assisted rewriting feel calm and deliberate.

## Principles

- **Text first**: the center writing surface has priority over sidebars,
  metadata, and controls.
- **Literary but restrained**: use serif type for titles, quotes, source names,
  and writing notes; keep controls simple and low-noise.
- **Clear action hierarchy**: one primary action per cluster; secondary actions
  should be lighter and grouped by intent.
- **No accidental changes**: wheel scrolling must not silently change combo
  boxes, spin boxes, AI target, model tier, or reference filters.
- **No clipped text**: Chinese labels, excerpts, notes, and AI previews need
  enough height and wrapping. Prefer flexible layouts over hard pixel caps.
- **Theme integrity**: light and dark modes must use semantic theme tokens; no
  stray warm-white blocks in dark mode.
- **State clarity**: current item, selected item, completed item, and active
  AI target should look different.

## Current Priority

1. Replace hard-coded preview and note colors with semantic theme tokens.
2. Fix toolbar button semantics so labels, tooltips, and behavior match.
3. Give AI text previews and instructions enough readable space.
4. Reuse no-wheel controls across AI, reference library, and specimen picker.
5. Reduce scrollbar and border noise without hiding affordances.
6. Keep reference/specimen cards book-like while avoiding fixed-height clipping.

## Manual Acceptance Checklist

- Test light, dark, and system theme; no hard-coded light panels should appear
  in dark mode.
- Test Windows scaling at 100%, 125%, and 150%; no text overlap, cropped
  buttons, or half-visible rows.
- Scroll over every combo box and spin box; values should not change unless the
  control has explicit focus.
- Open long AI selections, long continuation notes, long reference excerpts,
  and long specimen previews; all text must remain readable and scrollable.
- Resize the main window from narrow to maximized; the editor should stay the
  visual priority and side panels should not crush it.
- Verify Focus Mode enters and exits cleanly, restoring rail, toolbar, context
  pane, and fragment list visibility.
- Verify the specimen picker clearly distinguishes preview/current state from
  final selected state.

