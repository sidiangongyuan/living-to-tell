# Living to Tell Preview 0.1.54

0.1.54 repairs startup for existing installations upgraded from versions before `0.1.52`.

## What happened

The planning-priority update added `board_sort_order` to collection outlines. On an existing database, startup attempted to create the new index before adding that column. SQLite rejected the index with `no such column: board_sort_order`, so the first real data request failed even though the lightweight health endpoint responded.

## Fixed

- Existing databases now add and backfill `board_sort_order` before creating its index.
- Fresh installations reach the same final schema.
- The bounded sidecar-readiness wait from `0.1.53` remains in place for genuine cold starts.
- No article, collection, outline node, AI profile, or writing content is deleted or rewritten.

## Verification

- Reproduced the original 500 response using a read-only backup of an affected production database.
- Ran the final packaged backend against another copy of the same database: article and collection requests succeeded, the new column and index were present, `PRAGMA quick_check=ok`, and all 48 existing business-table row counts were unchanged.
- Python: `924 passed, 1 skipped`; the skipped test is the explicitly gated Gemini quota probe.
- Frontend unit tests: `98 passed`.

## Downloads

- `LivingToTell_0.1.54_x64-setup.exe`
- `LivingToTell_0.1.54_x64_zh-CN.msi`

The Windows preview is unsigned, so SmartScreen may show a warning. Download installers only from this repository's GitHub Release.
