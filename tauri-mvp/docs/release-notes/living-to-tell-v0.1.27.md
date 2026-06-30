# Living to Tell Preview 0.1.27

This update turns motif details into readable concept archives and lets AI enrichment suggest source-backed reference sentences that the user can explicitly import.

## Added

- Motifs now support a structured concept archive stored as `profile_json`. Existing databases migrate automatically and existing notes remain compatible.
- The motif detail pane now has readable sections for definition, core tension, writing functions, scene triggers, character signals, imagery translations, examples, misuse warnings, exercises, and source hints.
- AI enrichment can return external reference sentence candidates. Only candidates with text, author, and source title can be imported.

## Changed

- Tags and aliases are chip-first: click a chip to remove it from the local draft, then save the motif to persist the change.
- Detailed profile editing now happens in drawers instead of a long raw note field.
- AI enrichment drafts return structured profile data while retaining a legacy note representation for compatibility.
- AI-suggested related concepts still do not create graph edges. Graph relationships remain based on real article/reference excerpts.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\storage\test_database_migration.py tests\storage\test_motif_repository.py tests\test_tauri_mvp_api.py -q`
- `npm test -- --run`
- `npm run test:e2e -- e2e/motifs-flow.e2e.ts --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Assets

- `LivingToTell_0.1.27_x64-setup.exe`
  - SHA256: `011BABA3E38F97E667C28E50030674C2EF71882447364C4BD214805A1DBE6E4B`
- `LivingToTell_0.1.27_x64_zh-CN.msi`
  - SHA256: `2C994D35362103DB6EEFE30EDAF99AF8E35CBF6DF723809711E4F294D8CE64EC`
