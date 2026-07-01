# Living to Tell Preview 0.1.31

This update packages the AI profile key-isolation fix. It is intended for users
who keep multiple OpenAI-compatible relay profiles, such as `glm-5.2` and
`deepseek-v4-pro`, with different API keys.

## Fixed

- AI profiles now keep separate locally saved credential sources even when they
  share the same provider type.
- Editing an existing profile and saving a new local key reuses that profile's
  existing `env:LTT_AI_...` source instead of producing a new drifting source.
- Settings keeps saved `env:LTT_AI_...` credential sources visible after the
  user temporarily switches to `env:OPENAI_API_KEY`, `codex`, or another source.

## Verified

- `glm-5.2` relay profile: real request succeeded through Chat Completions.
- `deepseek-v4-pro` relay profile: real request succeeded through Chat Completions.
- AI Tools multi-model comparison succeeded with both profiles enabled together.
- The repository was scanned so no `sk-...` key-shaped secrets are included in
  source, tests, or documentation.

## Checks

- `D:\anaconda\envs\writer\python.exe -m pytest tests\test_tauri_mvp_api.py tests\services\ai -q`
- `npm test -- --run`
- `npm run build`
- `cargo check --manifest-path D:\python_proj\writer\tauri-mvp\frontend\src-tauri\Cargo.toml`
- `.\tauri-mvp\build-release.ps1 -PythonExe D:\anaconda\envs\writer\python.exe`

## Release artifacts

- `LivingToTell_0.1.31_x64-setup.exe`
  - SHA256: `A966050500808490F9FE42B15FCD7EA25AC6E88B16BBC1F6120FA19EEEE4C0AA`
- `LivingToTell_0.1.31_x64_zh-CN.msi`
  - SHA256: `AB7C25E9EB14A6E9E1A2D6B9DCE171BFFD215431B6670644D8BA813B51B19E9F`
