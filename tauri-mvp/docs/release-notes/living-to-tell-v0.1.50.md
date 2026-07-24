# Living to Tell Preview 0.1.50

0.1.50 is a focused correctness release for article selections sent to AI Edit.

## Exact selections, including articles with epigraphs

- Fixed AI Edit including text above the selected passage when the article has an epigraph.
- Selection coordinates are now translated from the visible body editor to the complete saved article before AI Edit opens.
- The selection is frozen before the asynchronous save, so focus and rendering changes cannot move it.
- A final text check prevents AI Edit from opening an incorrect range if the article changes during saving.
- Articles without epigraphs and full-article AI Edit continue to behave as before.

## Verification

- Unit tests cover plain articles, hidden epigraph prefixes, UTF-16 text, collapsed selections, and changed-body rejection.
- A Microsoft Edge browser regression selects text below an epigraph and confirms AI Edit previews exactly that text without the preceding paragraph.
- The full frontend test suite, browser suite, production build, and locked Cargo check were run before packaging.

## Windows assets

- `LivingToTell_0.1.50_x64-setup.exe`
- `LivingToTell_0.1.50_x64_zh-CN.msi`

Preview installers remain unsigned. Download them only from this repository's GitHub Release page and verify the published GitHub SHA256 digest.
