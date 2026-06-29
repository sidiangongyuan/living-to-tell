# Living to Tell Preview 0.1.26

This patch focuses on motif AI enrichment reliability and the motif archive/detail reading experience.

## Fixed

- Motif AI enrichment now handles `opencode/deepseek-v4-flash-free` responses that contain a complete short-card template but are not strict JSON.
- The enrichment API still prefers strict JSON, but can now recover from fenced JSON, balanced JSON embedded in prose, conservative trailing commas, and complete template-text responses.
- Random non-template text still fails with a clear Chinese message; this is not a fake-success fallback.

## Changed

- The motif detail pane is wider by default and more readable for long philosophical or conceptual motif names.
- The local star map is more compact, with related-node chips so relationship names remain readable inside the right pane.
- Motif tags, aliases, and notes now use larger single-column editing fields, reducing clipped text and cramped scrollbars.
- Public download links and installer names now point to `0.1.26`.

## Verification

- Real OpenCode smoke test with `opencode/deepseek-v4-flash-free`: create isolated test motif → generate AI enrichment draft → save note → verify required headings → delete motif → confirm cleanup.
- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py -q`
- `npm test -- --run`
- `npm run test:e2e -- e2e/motifs-flow.e2e.ts --workers=1`
- `npm run test:e2e -- --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Assets

- `LivingToTell_0.1.26_x64-setup.exe`
  - SHA256: `1A290FDB2E53E6067D1E983C2531BAA65D44A53A6B9E09C01BC875BFF9EE93ED`
- `LivingToTell_0.1.26_x64_zh-CN.msi`
  - SHA256: `A3F83674FACFAE3D79906A8E6A1CD05478A7D9A804A1950F105C9258FDB96442`
