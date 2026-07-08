# Living to Tell Preview 0.1.42

This release upgrades AI Cards from a simple editing form into a more useful writing artifact workspace.

## Highlights

- AI Cards are now reading-first. Open a card to see its title, type, tags, and structured sections before entering edit mode.
- Added **Copy as Prompt** so a style, character, or scene card can be pasted into AI tools, used as explicit context, or kept as reference material.
- Added card content and section copy actions for quicker reuse.
- Reworked the AI card builder into a clearer create / upgrade flow. Paste material or intent, choose the card type, preview the structured draft, then save or apply it only when you confirm.
- AI-generated card drafts can now include suggested tags, which are saved with new cards or merged into the current card when applying a draft.

## Safety Notes

- AI-generated drafts still do not write to the card library until you choose **Save as New Card** or **Overwrite Current Card**.
- Existing plain-text cards remain readable and editable; they can be upgraded into fixed templates when you choose.
- This release does not change the AI Cards database schema.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py -q -k "ai_card"`
- `npm run test:e2e -- --project=msedge --workers=1 --grep "AI Cards"`
- `npm run build`

## Assets

- `LivingToTell_0.1.42_x64-setup.exe`
- `LivingToTell_0.1.42_x64_zh-CN.msi`
