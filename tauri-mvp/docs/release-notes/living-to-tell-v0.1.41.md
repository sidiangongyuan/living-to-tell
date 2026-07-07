# Living to Tell Preview 0.1.41

This update makes the Collection Agent feel less like a form and more like a usable writing workbench.

## Highlights

- Type `/` in the Collection Agent prompt to open a command menu. You can choose `/init`, `/health`, `/continuity`, `/next`, `/memory`, or `/clear` without memorizing the commands.
- The slash menu supports keyboard selection: `ArrowUp` / `ArrowDown` moves, `Enter` or `Tab` confirms, and `Escape` closes it.
- Quick tasks are now displayed as a compact horizontal command strip instead of tall cards with awkward wrapped labels.
- The prompt area now has simpler guidance: ordinary text is regular chat, `/` opens Agent commands, and `@` adds explicit context references.
- Agent-side action buttons were tightened so short labels such as `保存记忆` do not stack vertically in narrower layouts.

## Safety Notes

- Slash commands do not bypass confirmation. Provider-facing quick tasks still open the confirmation area before sending a request.
- `/clear` still opens the clear confirmation and preserves project memory, writing data, and pending proposals.
- This release does not change the Collection Agent database schema or memory semantics.

## Assets

- `LivingToTell_0.1.41_x64-setup.exe`
- `LivingToTell_0.1.41_x64_zh-CN.msi`
