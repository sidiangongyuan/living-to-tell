# M8 Release Notes

M8 moves Writer from a fragment-only capture tool toward a two-layer writing
workflow: fragments remain the raw material, while works and collections add a
path toward finished pieces and grouped exports.

## Highlights

- **Works**
  Create longer-form pieces with title, summary, tags, status, target word
  count, and ordered sections. Section types in this release are `body` and
  `heading`.

- **Collections**
  Group multiple works into an ordered collection. Collections support add /
  remove, drag-reorder, and export of the whole set with a simple generated
  table of contents.

- **Include Fragment Into Work**
  Send a fragment into a work through a review dialog. The dialog starts from
  the current fragment selection when one exists, otherwise the whole fragment
  body. Before confirming, the inserted text can be edited and placed at an
  explicit insertion point inside the target section preview.

- **Unified Search**
  Search fragments and works from one dialog, then jump directly to the target
  fragment or to the matching work section.

- **Work Version History**
  Works support manual snapshots, AI-accept snapshots, and restore-to-current
  from saved work versions.

- **Expanded Export**
  Single works and full collections can be exported as `txt`, `md`, or
  `docx`. Fragment and project export from earlier milestones remain available.

## Scope limits in M8

- Plain-text-first: no rich text or formatting toolbar
- No PDF typesetting or book front matter yet
- Work sections can be moved with up / down controls; collection items also
  support drag-reorder
- Fragment source tracing exists in the data model, but the fragment-side UI
  remains intentionally lightweight in this release

## Useful shortcuts

- `Ctrl+P` — command palette
- `Ctrl+Shift+F` — global search
- `Ctrl+Shift+I` — include current fragment into a work

## Packaging note

The Windows bundle now includes `python-docx` so work / collection DOCX export
is available from the packaged app as well as from source installs.