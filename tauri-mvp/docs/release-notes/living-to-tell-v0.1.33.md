# Living to Tell Preview 0.1.33

## Highlights

- Added the Motif Star Map Writing Lens: a read-only way to browse existing motifs by tags, writing functions, sources, and callable sentence snippets.
- Added `/api/motifs/writing-index` and the `motif_writing_index` capability so the frontend can build this view without pulling every motif's excerpts one by one.
- Kept the existing co-occurrence star map semantics unchanged: graph links still come only from real excerpt/source co-occurrence.
- Updated documentation to remove the stale "up to three models" wording for AI comparison. AI Tools can now compare one or more selected profiles; more selected models may increase wait time, token use, and provider cost.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Windows Assets

- `LivingToTell_0.1.33_x64-setup.exe`
  - SHA256: `D58CF805921EADD3ACEDAEE1EDADFEA4CEAB384C3EBA1B1119E9CF123636115E`
- `LivingToTell_0.1.33_x64_zh-CN.msi`
  - SHA256: `5FDEAD596C71D9B2A6FE52BC21095D6555B2DA67EDDFFEDD9826D6DA3D7E42EF`
