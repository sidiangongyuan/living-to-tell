# Living to Tell Preview 0.1.36

## What changed

- Added a guided Collections tutorial with spotlight highlighting and Previous / Next / Skip / Finish controls.
- The tutorial covers the actual collection workflow: Article Order, Outline, outline item Type and Title fields, Linked Article, Planning Board, and Export.
- Renamed the Collections `Manuscript` tab to `Article Order` / `文章顺序`.
- Added clearer helper copy for Article Order, Outline, Planning Board, outline item Title, Type, and Linked Article fields.
- Added a Settings entry to restart the Collections tutorial after it has been dismissed.

## Data safety

- This update does not create collections, articles, outline items, sample projects, or database records automatically.
- The tutorial dismissed state is stored only in frontend `localStorage`.
- Linked Article remains a relationship between an outline card and a real article; it does not copy, move, or delete article text.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Artifacts

- `LivingToTell_0.1.36_x64-setup.exe`
  - SHA256: `5E21EA0DE137E5219B7C4176B7D17AB3A0EA4B011AEFB6DD43B8AFF03376E409`
- `LivingToTell_0.1.36_x64_zh-CN.msi`
  - SHA256: `1A0A9977A323E78C761DA8E530BF08626F646871501558CE523D769ACB5D068C`
