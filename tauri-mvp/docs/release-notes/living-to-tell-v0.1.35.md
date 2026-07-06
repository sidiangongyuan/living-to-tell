# Living to Tell Preview 0.1.35

## What changed

- Removed the article-side Motif Invocation panel and its copy, insert, and save-as-note material actions.
- Removed the Motif Star Map Writing Lens and the `/api/motifs/writing-index` chain.
- Added a lightweight article-side motif anchor list: the right context pane now shows only motif names and anchor counts for the current article.
- Added source-anchor grouping in motif details. A motif can jump back to the original article or reference source; if a source has several anchors, the app asks which one to locate.
- Kept motif graph semantics unchanged: graph links still come only from real excerpt/source co-occurrence.

## Data safety

- This update does not delete motif data, excerpts, concept archives, AI enrichment drafts, reference candidates, articles, or references.
- The removed invocation/index features were product UI/API paths only. Existing user-created motif anchors remain intact.
- AI enrichment remains review-first and still writes only after explicit confirmation.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Artifacts

- `LivingToTell_0.1.35_x64-setup.exe`
  - SHA256: `E0EAF08814A9CD181907213B85A78299DB3E1903A68994C0494D35CB578703D9`
- `LivingToTell_0.1.35_x64_zh-CN.msi`
  - SHA256: `2EDA2AE6E7A6D84C761773CB5132DA61E2B6273B4F661958A2BBD60336B460EE`
