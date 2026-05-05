# M10B Release Notes

M10B is a Gemini/OAuth reliability release for the AI workspace. It keeps
the M10A workspace shape, but makes local Gemini OAuth practical for daily
writing use.

## Highlights

- **Gemini CLI / OAuth without the CLI prompt layer**
  Writer now reuses the user's saved Gemini CLI OAuth refresh token, then
  calls Gemini Code Assist directly. This avoids the `gemini --prompt` coding
  agent behavior that can inspect the project instead of following writing
  instructions.

- **Model switching in Settings**
  The AI settings dialog now includes model presets. Gemini CLI / OAuth can
  switch between `gemini-cli-default`, Gemini 3 preview text models, and
  Gemini 2.5 text models; custom model text is still supported.

- **Gemini proxy persistence**
  The Gemini CLI / OAuth provider has a dedicated proxy field. Writer stores
  the proxy URL and uses it for both OAuth token refresh and Code Assist API
  calls, so packaged GUI launches do not depend on terminal environment
  variables.

- **Gemini tier / quota visibility**
  Settings can query the Gemini Code Assist tier, backing project, paid tier,
  and any itemized credits the service returns. Some tiers report as included
  / not itemized rather than a numeric quota.

- **Live AI context estimate**
  The AI workspace context estimate now updates when a scope is bound, when
  the target changes, and when pasted text changes. It counts the active
  target text plus manual attachments instead of staying at zero.

## Validation notes

- Direct Gemini Code Assist OAuth call verified with a configured local HTTP
  proxy.
- `gemini-3.1-pro-preview`, `gemini-3-flash-preview`,
  `gemini-3.1-flash-lite-preview`, and `gemini-2.5-flash` verified
  end-to-end through `GeminiCliProvider` with `pong` responses, actual model
  metadata, and token usage.
- Settings quota check verified against the active account and project.
- Focused tests for Gemini OAuth, Settings, and AI workspace: `64 passed`.

## Packaging note

This alpha ships as the portable bundle in `dist/Writer/`, the versioned zip
`dist/Writer-0.2.0-alpha.6-portable.zip`, and the compatibility alias
`dist/Writer-portable.zip`.