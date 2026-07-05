# Living to Tell Preview 0.1.34

## Highlights

- Added Motif Invocation inside the article right context pane, bringing the Motif Writing Lens back into the main drafting workflow.
- Existing motif definitions, core tensions, writing functions, scene triggers, and related sentences can now be selected while writing an article.
- Added explicit actions for selected motif material: copy, insert into the article body, save as the current article's note, or open the motif in the Motif Star Map.
- Kept graph semantics unchanged. This feature does not automatically create motifs, excerpts, semantic edges, or AI-generated links.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Windows Assets

- `LivingToTell_0.1.34_x64-setup.exe`
  - SHA256: `FDDDF2B8093D0420F0B3E46888469CC661C979614334A512198085C030075654`
- `LivingToTell_0.1.34_x64_zh-CN.msi`
  - SHA256: `B3C119F0F5B8C7D0B280AC7F1DE5DDBC7337150A5B49063640055F2A493A49F3`
