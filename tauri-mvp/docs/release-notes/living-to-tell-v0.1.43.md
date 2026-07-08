# Living to Tell Preview 0.1.43

This release simplifies AI Cards and makes AI card generation recoverable.

## Highlights

- The AI Cards page is quieter by default. The large AI builder no longer appears all at once; use **AI Create** or **Tidy Current Card** when you need it.
- Card reading is cleaner: card metadata, **Copy as Prompt**, **Edit Card**, and readable content sections stay on the main surface.
- AI Card generation now supports choosing an AI profile, including the default config or any enabled saved provider profile.
- AI Card generation now runs as a backend job. You can close the builder or leave the page while it continues in the current app session.
- A visible task bar shows the current stage, elapsed time, provider/model details, and actions to view, interrupt, or clear the task.
- Reconnecting only checks local job status. It does not resend the provider request, avoiding accidental duplicate token spend.

## Safety Notes

- Drafts still require explicit confirmation before writing to the card library.
- Interrupting stops local waiting and prevents adopting later results, but it cannot guarantee the remote provider stops generation or billing after the request has been sent.
- AI Card jobs are kept in backend process memory; they do not survive a full app restart.

## Verification

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py -q -k "ai_card or app_version"`
- `npm run test:e2e -- --project=msedge --workers=1 --grep "AI Cards"`
- `npm run build`

## Assets

- `LivingToTell_0.1.43_x64-setup.exe`
- `LivingToTell_0.1.43_x64_zh-CN.msi`
