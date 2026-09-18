# Living to Tell Preview 0.1.56

0.1.56 adds streaming support for OpenAI-compatible chat completions to prevent proxy timeouts on long reasoning models (such as DeepSeek V4 Pro) and adds dynamic Windows registry fallback for environment credentials.

## What's New

- **Streaming Chat Completions**: OpenAI-compatible relay requests now stream token chunks progressively, keeping connections alive through Cloudflare, reverse proxies, and local VPN/tunnels. This completely resolves Cloudflare Error 524 timeouts on models generating extensive reasoning chains.
- **Extended Provider Timeout**: Default OpenAI provider timeout increased from 120s to 300s (5 minutes), aligning with frontend long-running AI task timeouts.
- **Dynamic Windows Registry Credential Fallback**: `resolve_env_var` dynamically reads API keys from `HKEY_CURRENT_USER\Environment` on Windows even if the backend process started before desktop environment broadcast, eliminating restart requirements when saving new keys.
- **DeepSeek V4 Pro & Flash Support**: Full support for DeepSeek V4 Pro and Flash models via OpenAI-compatible relay endpoints for both AI Cards and Motif Concept Enrichment.

## Downloads

- `LivingToTell_0.1.56_x64-setup.exe`
- `LivingToTell_0.1.56_x64_zh-CN.msi`

The Windows preview is unsigned, so SmartScreen may show a warning. Download installers only from this repository's GitHub Release.
