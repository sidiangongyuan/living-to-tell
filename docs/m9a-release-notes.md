# M9A Release Notes

M9A keeps the fragment → work → collection model from M8, but upgrades the
shell so the app reads like a single writing workspace instead of a stack of
separate panels.

## Highlights

- **Modern shell layout**
  The main window is now organized as a four-column workspace:
  navigation rail, list column, main work area, and a collapsible context
  pane.

- **Theme system**
  Writer now supports `light`, `dark`, and `follow system` theme modes.
  Theme choice is applied before widgets are created, so the packaged app
  opens with the correct palette on first paint.

- **Reachable empty states**
  Empty and unselected states are now intentional UI surfaces rather than
  placeholder labels. Fragments, Works, and Collections each expose guided
  CTAs when there is nothing selected or nothing created yet.

- **Welcome screen without fake fragments**
  A truly empty library now shows a welcome state instead of silently creating
  a blank fragment behind the editor.

- **Fragment to work closure**
  The Works empty-state action now completes the real include flow: if a
  current fragment exists but no work exists yet, Writer bootstraps a work and
  immediately opens the include dialog against a valid target.

- **Archived-only library behavior**
  The welcome screen appears only when the fragment repository is truly empty.
  If entries still exist but are archived or filtered out, the normal fragment
  workspace stays visible so recovery controls remain reachable.

- **Theme consolidation**
  Previously scattered hard-coded greys and ad-hoc styles were pulled into a
  centralized theme/QSS system, including meta labels, status labels,
  no-results states, and theme-aware tag chips.

## Workflow in this release

- Capture freely in Fragments
- Select a fragment and include it into a Work
- Organize Works and Collections from the same shell
- Switch theme mode without restarting

## Scope limits in M9A

- This is still a desktop, widget-based writing tool; no rich text editor or
  formatting toolbar was added in this milestone
- The context pane is intentionally lightweight and focused on metadata plus
  a few action shortcuts
- M9A is a shell/UX release, not a data-model rewrite

## Validation notes

- Focused UI regressions were added for welcome-state reachability,
  archived-only startup behavior, empty-state CTA wiring, and theme behavior
- The packaged Windows bundle was rebuilt and smoke-tested successfully
- The packaged app was verified to initialize its SQLite database on startup

## Packaging note

The Windows portable bundle in `dist/Writer/` and `dist/Writer-portable.zip`
includes the M9A shell, theme system, and related UI assets.