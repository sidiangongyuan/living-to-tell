# Living to Tell Preview 0.1.40

This update tightens the Collections workspace after the first Collection Agent release. It focuses on clearer structure language, safer Agent entry points, and a smoother window layout.

## Highlights

- The Collections tutorial is now more concrete and step-by-step. It walks through adding existing articles, creating structure nodes, adding child nodes below chapters, understanding fields, using the board, exporting, and discovering the Agent tab.
- Collection structure terms are clearer by project type:
  - Novel: Part -> Chapter -> Scene.
  - Essay collection: Section -> Group -> Essay.
  - Nonfiction: Part -> Chapter -> Section.
  - Notes are planning-only and do not represent manuscript text by themselves.
- `POV` is now labeled as `Point of View / Narrator (POV)` / `视角 / 叙述者 (POV)`, with help text explaining that it records who sees or narrates that unit.
- Collection Agent now has an `Initialize Agent` quick task. Typing `/init` opens the same confirmation flow, so it will not send a provider request until you confirm.
- The Agent prompt footer no longer has the confusing task-mode dropdown. Dedicated jobs live in the quick-task cards; normal input sends as regular Agent chat.
- Collections adapts better in non-fullscreen windows, with narrower panes, responsive board columns, a denser Agent grid, and closeable dialogs.

## Fixes

- Opening a collection from an article link now gives the linked article a short locate highlight instead of a sticky selection.
- Selecting another structure node now immediately moves the visible selection highlight and detail panel to that node.

## Safety Notes

- This release does not change collection, outline, article, or Agent memory storage schemas.
- `/init` and quick tasks still require confirmation before calling the selected AI provider.
- Agent output still uses preview/confirm proposals and does not automatically edit manuscript text.

## Assets

- `LivingToTell_0.1.40_x64-setup.exe`
- `LivingToTell_0.1.40_x64_zh-CN.msi`
