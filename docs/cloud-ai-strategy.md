# Writer Cloud AI Strategy v0.1

## 1. Decision Summary

For MVP, the recommended cloud AI approach is:

- use a cloud model API rather than local inference
- start with one direct provider, not multiple providers at once
- design the app around an internal provider adapter so the external provider can be replaced later
- prefer an OpenAI-compatible request shape for the first client implementation
- default to one quality-first model for all rewrite tasks in MVP

## 2. Recommended First Implementation

### Product-Level Recommendation

Use a single quality-first cloud provider in v1, with OpenAI as the default first provider.

Reasoning:

- the interaction style is closest to the chat-AI experience the user already understands
- SDKs and Python integration are mature
- the API pattern is a practical baseline for later adapters
- model quality is strong enough to validate prose polishing before optimizing cost
- a large part of the broader ecosystem is compatible with similar request patterns

This does not mean the app should be permanently tied to one provider. It only means the first shipped version should avoid premature multi-provider complexity.

### Why Not Multi-Provider on Day One

- it adds settings complexity to a minimal journal product
- output comparison becomes harder because differences may come from provider variance rather than prompt quality
- error handling, rate limits, and request normalization all get more complex
- the first product question is whether the writing workflow works, not whether five providers can be toggled

## 3. Practical Provider Strategy

### Phase 1: One Provider, One Main Model

Use one main model for:

- polish
- expand
- continue
- summarize
- rewrite with references

Recommended default posture:

- quality first
- cost acceptable for personal use
- predictable behavior

### Phase 2: Add a Second Provider Only for a Clear Reason

Add another provider only if one of these becomes true:

- prose quality becomes the main concern
- cost becomes materially noticeable
- latency is poor for the user's region
- privacy or account availability requires a fallback

Recommended future sequence:

- first fallback: another premium writing-capable provider for A/B comparison
- second fallback: a cheaper OpenAI-compatible provider for low-stakes tasks
- later option: local model adapter for privacy-sensitive usage

## 4. API Shape Recommendation

The application should not depend directly on any provider SDK across the whole codebase.

Instead, the app should define its own internal interface and keep provider-specific logic in one place.

Suggested internal request model:

```python
class RewriteRequest:
    action: str
    text: str
    references: list[dict]
    rewrite_strength: str
    tone_hint: str | None
    preserve_voice: bool
    max_output_chars: int
```

Suggested internal response model:

```python
class RewriteResponse:
    content: str
    model: str
    provider: str
    input_tokens: int | None
    output_tokens: int | None
    finish_reason: str | None
```

Required provider adapter methods:

- `polish_text`
- `expand_text`
- `continue_text`
- `summarize_text`
- `rewrite_with_references`

## 5. Prompting Policy for This Product

The product is not trying to generate showy literary text. The default prompting stance should be conservative.

Core prompt rules:

- preserve the user's original meaning
- preserve emotional tone and first-person perspective when present
- lightly improve rhythm, clarity, and imagery
- avoid sounding overwritten
- treat imported references as tonal inspiration, not material to imitate or copy

Default rewrite strength for MVP:

- `light`

Optional strengths to reserve for later:

- `medium`
- `strong`

## 6. Privacy Boundaries

Because the app is personal writing software, the cloud boundary should be narrow and explicit.

Recommended rules:

- send only the currently selected text or current entry segment
- send only the specific references chosen for the rewrite
- do not upload the entire local notebook database by default
- show a small note in the UI that this action sends text to a cloud model
- require explicit user action for every AI request

## 7. Cost Strategy

### Cost Principle

For this product, the first priority is writing quality, not squeezing every token cost from day one.

For personal use, cloud cost is likely manageable if requests are kept bounded. The main cost risk comes from repeatedly rewriting long passages with many references.

### Recommended Request Limits

- selected text per request: keep within about 1500 Chinese characters in MVP
- attached references: at most 3 passages
- total reference length: keep within about 1200 Chinese characters
- polish output cap: about 1200 Chinese characters
- expand or continue output cap: about 1800 Chinese characters

These limits can be relaxed later if needed.

### Practical Budget Expectation

For a single personal user, a quality-first cloud model usually lands in a manageable monthly range if usage is modest.

Typical personal usage pattern:

- a few rewrite actions per day
- short to medium fragments
- occasional reference passages

Under that pattern, the monthly spend is more likely to be a small recurring tool cost than a major infrastructure issue.

### Cost Controls to Build Into the App

- store provider and model used for each rewrite result
- log token usage when the provider returns it
- cap the amount of reference text included automatically
- keep the default action on selected text, not the full manuscript
- allow the user to disable AI temporarily

## 8. Replacement Strategy

The replacement strategy matters more than the first provider name.

Design rules:

- keep all provider-specific code inside `services/ai/providers/`
- keep prompt templates separate from transport code
- normalize output into one internal response model
- store provider and model metadata with every generated version
- do not scatter provider-specific conditionals through UI or storage layers

Recommended implementation order:

1. internal AI service interface
2. OpenAI provider adapter
3. prompt builder module
4. usage logging and settings storage
5. optional second provider adapter later

## 9. MVP Recommendation in One Sentence

Use one high-quality cloud provider through a replaceable internal adapter, start with OpenAI as the default integration target, and keep requests small, explicit, and focused on light prose polishing.

See [codex-style-integration.md](D:/python_proj/writer/docs/codex-style-integration.md) for the recommended way to provide a Codex-like "configure once, then chat" experience inside the desktop app.

## 10. What Another Agent Should Implement First

The implementation agent should prioritize:

1. a settings screen for API key and model name
2. one provider adapter with a simple rewrite call
3. one prompt builder for `light` polish
4. rewrite result persistence with provider metadata
5. usage logging for debugging and future cost tracking
