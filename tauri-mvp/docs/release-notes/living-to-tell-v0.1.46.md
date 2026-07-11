# Living to Tell Preview 0.1.46

0.1.46 makes the Collection Agent steadier while moving between books and gives the conversation room to breathe.

## Reliable Collection Switching

- Rapidly switching between collections no longer lets a late article, outline, or Agent request overwrite the current page.
- A delayed 404 from the previous collection is ignored instead of appearing as `Collection not found` in the newly selected collection.
- Agent polling and proposal actions also verify their collection before updating the interface.
- Concurrent backend requests now serialize their SQLite operations and explicit transactions. This removes the low-level SQLite misuse error that could appear when a stale sidebar read overlapped article cleanup.

## Project Bible Apply Fix

- Memory proposals now use the eight fixed Project Bible section IDs explicitly in the model prompt.
- Common model-created English and Chinese aliases are normalized before a proposal is shown or applied.
- Previously saved proposals such as `project_core_philosophy` or `项目核心哲学基调` can be applied to `project_core`.
- A genuinely unrecognized section produces a readable Chinese explanation and is never written to an arbitrary memory section.

## A Roomier Agent Workspace

- The left session index and right workspace panel now collapse independently.
- The old `资料` button is now **工作栏 / Workspace**. It opens Context, Drafts, open proposals, and the Project Bible.
- At ordinary desktop widths the right workspace opens as a drawer instead of shrinking the conversation.
- The central conversation and composer use a wider readable measure.

## Real Provider Check

An isolated smoke test used the locally saved `Deepseek-v4-pro` profile through OpenAI Chat Completions. The run succeeded, produced a `project_core` memory proposal, and applied it successfully without reading or modifying the author's real collections.

## Installers

- `LivingToTell_0.1.46_x64-setup.exe`
- `LivingToTell_0.1.46_x64_zh-CN.msi`

The Windows preview remains unsigned. Download installers only from this repository's GitHub Release page.
