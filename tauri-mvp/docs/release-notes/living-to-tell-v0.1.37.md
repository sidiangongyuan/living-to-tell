# Living to Tell Preview 0.1.37

## What changed

- Reworked Collections into one clear **Manuscript Structure** tree instead of separate article-order and outline surfaces.
- Added project types: General, Novel, Essay Collection, and Nonfiction. The structure labels adapt to the selected project type.
- Structure nodes can now have parents and children. A chapter can link one article directly and also contain multiple child nodes, each with its own linked article.
- Added **Unplanned Articles** for articles that belong to the collection but have not yet been placed in the manuscript tree.
- Export now prefers the manuscript tree when linked structure nodes exist. Collections with no linked structure nodes still fall back to the old article-list export.
- Updated the Collections tutorial, user guide, README copy, and Tauri README around the book-project workflow.

## Data safety

- Existing collections, articles, outline nodes, and article links are preserved.
- A safe migration adds `project_type` to collections with the default value `general`.
- Linking an article to a structure node does not copy, move, or delete article text.
- Removing an article from a collection still does not delete the original article.
- Unplanned articles are not silently included in structure export once the manuscript tree has linked article nodes.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\storage\test_motif_repository.py tests\storage\test_collection_outline_repository.py tests\storage\test_article_collections.py tests\services\test_article_collection_export.py -q`
- `npm test -- --run`
- `npm run test:e2e -- --project=msedge --workers=1`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Artifacts

- `LivingToTell_0.1.37_x64-setup.exe`
  - SHA256: `3F2F7FB281B22C664F9AC90D1D24CB65B08C4567A6E2D6D49FB7BBAE6264176E`
- `LivingToTell_0.1.37_x64_zh-CN.msi`
  - SHA256: `D100A356548A585EA2C5814ACC4A1908CDA1AE30E9C68002B66DCB9AA9FAA926`
