# Living to Tell Preview 0.1.30

This update makes AI setup less obscure. You no longer need to manually create Windows environment variables before testing a relay key: Settings can save a pasted API key to the current user's local environment and then use that generated `env:LTT_AI_...` source across normal AI tools, AI Cards, motif enrichment, and multi-model comparison.

## Added

- Settings now has a **Save local API key** flow for the global AI config and each AI profile. It writes the key to the current Windows user environment and stores only the generated `env:LTT_AI_...` credential source in app settings.
- Added `deepseek-v4-pro` and `glm-5.2` to the OpenAI-compatible model preset list after real relay tests against `https://elysiver.h-e.top/`.

## Changed

- Custom saved local credential sources remain visible in the Settings dropdown, so `env:LTT_AI_...` selections do not disappear just because they are not built-in presets.
- OpenAI-compatible relay configuration now accepts origin-style base URLs such as `https://elysiver.h-e.top/`; the provider normalizes them to `/v1` before calling the OpenAI SDK.
- AI settings wording now distinguishes two cases clearly: app settings store credential sources, while explicitly saved local keys live in user environment variables.

## Verification

- Real relay smoke tests:
  - `glm-5.2` through `https://elysiver.h-e.top/v1/chat/completions`: success.
  - `deepseek-v4-pro` through `https://elysiver.h-e.top/v1/chat/completions`: success.
- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py -q`
- `D:\anaconda\envs\writer\python.exe -m pytest tests\services\ai\test_preflight.py tests\services\ai\test_openai_provider.py tests\services\ai\test_gemini_provider.py -q`
- `npm test -- --run`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Assets

- `LivingToTell_0.1.30_x64-setup.exe`
  - SHA256: `CF00E16F78E39AC6BB20B1FBDFC6B1CAB97963654B4D04BFCD84A2C3CB5727E9`
- `LivingToTell_0.1.30_x64_zh-CN.msi`
  - SHA256: `35256E5C948FF63DE3A6696EBDA2575393663F193EDB64C1F37132E1CEF0B442`
