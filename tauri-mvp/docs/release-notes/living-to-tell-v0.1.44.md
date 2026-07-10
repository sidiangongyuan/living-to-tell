# Living to Tell Preview 0.1.44

This release is a workflow and visual polish pass centered on Collections, while also tightening the article context pane and Reference Library.

## What changed

- Collections now use a compact project header, searchable shelf, inline progress summary, and focused actions. The manuscript and board begin much higher in the window.
- Selecting a structure node opens a readable planning card first. Use `Edit Details` only when changing fields; newly created nodes still open directly in edit mode.
- Structure creation now has one smart top-level action and a secondary type menu. Collection deletion moved into the more-actions menu.
- The article context pane now prioritizes collection navigation and writing notes. Empty motif anchors remain collapsed, while linked anchors automatically open.
- Reference Library passages now open in reading mode. Source metadata, personal notes, citation copy, and motif-anchor counts remain visible without presenting every field as a form.
- Collection and reference layouts were checked at the desktop minimum window size and adjusted to remain readable without horizontal page overflow.

## Author-journey verification

A real local-backend test now creates a disposable novel sample and verifies:

- opening an article and returning to its collection;
- locating the linked draft and opening it again from the manuscript node;
- reviewing the planning board;
- reading and editing a reference, then copying a complete citation;
- opening an AI Card and copying it as a prompt;
- rendering Collections and Reference Library at `1024 × 768`.

The disposable sample is removed after the test and does not touch normal user content.

## Installers

- `LivingToTell_0.1.44_x64-setup.exe`
- `LivingToTell_0.1.44_x64_zh-CN.msi`
