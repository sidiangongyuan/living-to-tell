# AI Setup Troubleshooting

Living to Tell treats each provider connection as an independent AI profile. One profile is the default for single-model features; AI Edit sends exactly the profiles selected for that run.

## Start with the profile workflow

1. Open **Settings → AI**.
2. Create a profile with the three-step wizard or use **Scan Local Configs**.
3. Run **Check All Locally**. This checks whether the referenced key or CLI login exists without contacting the model.
4. Select the profiles you want to verify and send a minimal real test. This can use tokens and incur provider cost.
5. Read the saved health state: **Untested**, **Passed**, **Failed**, or **Configuration changed; retest required**.

A local check is not proof that the endpoint, account, model, or billing group is usable. Only a successful real test proves that exact provider/model/transport combination.

## Access methods

| Method | What Living to Tell uses | What to verify |
| --- | --- | --- |
| OpenAI API | An API key and the official endpoint | Key validity, model access, account billing, and the selected model name. |
| OpenAI-compatible relay | A profile-specific key, base URL, model, and transport | The relay's documented URL, model name, account group, and whether it expects Chat Completions or Responses. |
| Codex | The existing local Codex login | Codex is signed in and can make a small request locally. Living to Tell does not provide an in-app ChatGPT OAuth flow. |
| Gemini API | A Gemini API key or compatible relay profile | Key/project access, model availability, endpoint, and relay transport requirements. |
| Gemini CLI | The existing local Gemini CLI login | `gemini` is installed, signed in, and available to the desktop process. |
| OpenCode | The existing local `opencode auth login` session | OpenCode is installed, authenticated, and the selected model is available. |

## Diagnostic messages

| Visible diagnosis | Meaning | Action |
| --- | --- | --- |
| API Key is not configured | The profile points to an empty or missing credential source. | Edit the profile and save a key locally, or correct the credential source. |
| Local login not found | Codex, Gemini CLI, or OpenCode has no usable local session. | Sign in with that tool, then rerun the local check and real test. |
| Login check timed out | The local CLI did not answer in time. | Confirm the CLI works in a terminal and is not waiting for an interactive prompt. |
| 401 | The endpoint rejected authentication. | Verify the profile-specific key and base URL. Do not replace it with another profile's key. |
| 403 | The account is authenticated but lacks permission for the model or provider group. | Check model access, relay account group, region, quota, or billing permissions. Changing transport does not fix an account-permission denial. |
| 404 | The base URL, API path, or model name is not recognized. | Compare the profile with the provider's current documentation; do not append the same `/v1` segment twice. |
| 429 | The provider is rate-limiting the account or quota is exhausted. | Wait or review quota. Living to Tell does not automatically resend the request. |
| Timeout | The request may have been sent but no response arrived before the local wait ended. | Check the provider dashboard before retrying. A remote request may still finish or incur cost. |
| HTML or gateway page | A proxy returned a website/error page instead of an AI API response. | Check the base URL, proxy health, authentication gateway, and required API path. |

Public error messages are sanitized. Raw HTML, traceback text, secret values, and local credential paths are not shown in the interface.

## Transport and relay checks

OpenAI-compatible services commonly expose either **Chat Completions** or **Responses**. The setup wizard selects a sensible default and keeps this choice under Advanced settings. Preserve a working transport when migrating an older configuration; do not guess based only on the model name.

If authentication succeeds but the provider reports a group such as `model-name-shared` is forbidden, the request reached the relay. That is an account-permission problem, not evidence that Living to Tell should switch to another profile's credential.

## Long tasks and cost safety

- Leaving AI Edit does not stop the current task. Return to the page to query its status.
- Reconnection never creates a new task or resends the provider request.
- OpenAI-compatible calls stop local waiting after 120 seconds by default and disable the SDK's hidden automatic retries. Advanced users can set `WRITER_OPENAI_TIMEOUT_SECONDS`; changing it does not guarantee that a remote request stops generating or billing.
- Local cancellation stops waiting for and adopting later results, but cannot guarantee that a request already sent to the provider stops generating or billing.
- One failed model does not block successful results from other selected profiles.
- If the article changes after a run starts, positional write-back is blocked. Copy the result or rerun against the current text.

## Profile deletion

Deleting a profile keeps its local key by default. A profile-specific `LTT_AI_*` key can be deleted only when no other profile references it. If the profile is the default or is used by a Collection Agent, choose a replacement first.

When reporting a problem, include the profile's provider, model, transport, health time, and sanitized diagnosis. Never post API keys, database files, private writing, raw relay pages, or local credential paths.
