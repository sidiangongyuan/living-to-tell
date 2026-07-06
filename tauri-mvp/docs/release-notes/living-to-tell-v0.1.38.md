# Living to Tell Preview 0.1.38

This update adds a collection-bound Agent for long-form writing projects. The Agent is designed as a manuscript editor and continuity assistant, not as an automatic prose writer.

## What's New

- Added an **Agent** tab inside Collections.
- Added per-collection project memory with sections for project core, characters, timeline, world, style, foreshadowing, decisions, and open questions.
- Added explicit context references for structure nodes, articles, AI Cards, motifs, and reference passages.
- Added background Agent runs with visible stages and reconnectable status.
- Added reviewable proposals for memory updates, manuscript-structure changes, and article notes.

## Safety Model

- The Agent does not automatically modify article text.
- Generated changes are stored as proposals first.
- The author must explicitly apply each proposal before it writes to memory, structure, or article notes.
- Cancellation stops local waiting, but it cannot guarantee that an already-sent provider request stops remotely.

## Installers

- `LivingToTell_0.1.38_x64-setup.exe`
- `LivingToTell_0.1.38_x64_zh-CN.msi`
