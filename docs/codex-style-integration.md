# Writer Codex-Style Integration Options v0.1

## 1. Feasibility

Yes, this is feasible.

Based on the local Codex configuration that was inspected, the current Codex setup is not using a mysterious private runtime. It is configured around a custom provider with an OpenAI-style identity, a custom base URL, and the `responses` wire API.

That means the writer app can support a Codex-like setup flow:

- user sets provider config
- user selects model
- user enters a chat panel or rewrite action
- the app sends requests directly to the same class of remote API

The important conclusion is this:

The best solution is usually not to embed the Codex application itself. The better solution is to adopt a compatible config model and call the provider API directly inside the app.

## 2. What Was Confirmed From the Local Codex Config

The inspected config shows these useful facts:

- provider mode is `custom`
- provider name is `OpenAI`
- transport shape is `responses`
- the endpoint is a configurable `base_url`
- the main model is configurable

This is exactly the kind of setup that can be mirrored in the writer app.

## 3. Three Integration Approaches

### Option A: Direct API Integration With Codex-Style Config

This is the recommended option.

How it works:

- the writer app has its own AI settings screen
- the app stores a provider profile with fields such as provider name, base URL, model, API mode, and API key source
- the app sends requests directly to the configured endpoint using a Python client
- the app stores chat history and rewrite history in its own SQLite database

Why this is the best fit:

- closest to the Codex mental model of "configure once, then talk"
- keeps the product independent from Codex internals
- lets the app support both free chat and rewrite actions with one backend
- easiest to control UX, data flow, and privacy boundaries
- easiest to evolve later into multi-provider support if needed

Tradeoffs:

- you need to implement chat session persistence yourself
- you need to implement streaming and response parsing in the app

Recommended use in this project:

- one AI chat panel for free conversation
- one rewrite service for selected text
- one provider profile in settings

### Option B: Wrap the Local Codex CLI as a Subprocess

This is possible, but it is not the recommended architecture.

How it works:

- the app launches the local `codex` command
- the app passes prompt text through stdin or command arguments
- the app captures stdout and displays it in the UI

Advantages:

- fast for a rough prototype
- may reuse the existing Codex config with minimal new settings

Problems:

- fragile output parsing
- harder multi-turn state management
- tighter coupling to CLI behavior changes
- weaker control over latency, streaming, and errors
- not ideal for a polished desktop app

Recommended use in this project:

- only for a short-lived prototype if the goal is to test the idea in one or two days

### Option C: Local Bridge Service

This is a medium-term option, not the first choice for MVP.

How it works:

- run a small local HTTP service on the machine
- the service reads provider config
- the desktop app talks only to the local service
- the service forwards requests to the cloud provider

Advantages:

- clean separation between UI and AI backend
- easier future reuse across multiple apps
- easier future support for multiple providers

Problems:

- extra moving part
- more setup for a single-user personal tool
- unnecessary early complexity unless there will be multiple client apps

Recommended use in this project:

- only if the user later wants both desktop and other tools to share the same AI backend

## 4. Recommended Solution for This Product

Choose Option A.

More specifically:

- do not integrate the Codex runtime itself
- do implement a Codex-style configuration model
- do support importing or manually mirroring the important fields from the local Codex config
- do call the configured provider endpoint directly from the writer app

This gives the user the experience they actually want:

- configure once
- open the app
- chat directly
- invoke rewrite actions directly on writing fragments

## 5. Best Practical Design

### 5.1 User Experience

The app should have two AI entry points:

- `AI Chat`: a simple side panel or dialog for free conversation
- `Polish With AI`: action on selected text or current fragment

These two entry points should share the same provider config and the same underlying AI client.

### 5.2 Configuration Model

Recommended app config fields:

```toml
provider = "custom"
provider_name = "OpenAI"
base_url = "https://your-endpoint/v1"
wire_api = "responses"
model = "gpt-5.4"
api_key_source = "env:WRITER_API_KEY"
reasoning_effort = "medium"
```

Optional convenience field:

```toml
import_from_codex = "C:/Users/12941/.codex/config.toml"
```

Recommended behavior:

- the app can offer an `Import Codex Config` button
- import should copy safe settings such as base URL, model, and API mode
- API key should still be entered explicitly or sourced from an environment variable or Windows credential store

### 5.3 Credential Handling

For v1, use one of these:

- environment variable
- Windows credential storage
- encrypted local settings as an interim fallback

Do not depend on parsing Codex auth storage in the first version.

Reason:

- it creates tighter coupling to another tool's private auth behavior
- it is less stable than owning your own credential flow

### 5.4 Session Design

The writer app should not depend on provider-side chat history.

Store conversations locally in SQLite:

- `chat_sessions`
- `chat_messages`
- `rewrite_tasks`
- `entry_versions`

This gives the app full control over:

- chat continuity
- local search
- privacy boundaries
- future provider replacement

## 6. Minimal Technical Shape

### 6.1 Core Interface

```python
class AiConfig:
    provider_name: str
    base_url: str
    wire_api: str
    model: str
    api_key: str


class ChatTurn:
    role: str
    content: str


class AiProvider:
    def chat(self, turns: list[ChatTurn]) -> str:
        ...

    def rewrite(self, text: str, instruction: str, references: list[str]) -> str:
        ...
```

### 6.2 Recommended Call Pattern

If the endpoint is OpenAI-compatible and uses the `responses` API shape, the writer app can use a client pattern like this:

```python
from openai import OpenAI


client = OpenAI(base_url=config.base_url, api_key=config.api_key)

response = client.responses.create(
    model=config.model,
    input=[
        {
            "role": "system",
            "content": "You are a restrained prose polishing assistant.",
        },
        {
            "role": "user",
            "content": user_text,
        },
    ],
)

output_text = response.output_text
```

The exact SDK call can be adjusted later, but this is the right architectural direction.

## 7. Implementation Plan

### Step 1

Build a single provider adapter that supports:

- base URL
- model
- API key
- `responses` transport

### Step 2

Add a settings page with:

- base URL
- model
- API key input or environment variable binding
- `Import Codex Config` action

### Step 3

Add a simple `AI Chat` panel:

- message list
- input box
- send button
- local history persistence

### Step 4

Add writing-specific actions using the same backend:

- polish selected text
- expand fragment
- continue fragment

### Step 5

Add safe request limits:

- max selected text length
- max references attached
- basic token or size logging

## 8. What Not To Do

- do not build around shelling out to Codex unless it is just a throwaway prototype
- do not couple the app to Codex auth internals in v1
- do not upload the whole notebook to the model by default
- do not add complicated multi-provider routing on day one
- do not make chat the only AI surface; rewrite actions should share the same backend

## 9. Final Recommendation

For this writer app, the most robust solution is to build a native AI chat and rewrite layer inside the app, while using a Codex-like config format and optionally importing key values from the existing local Codex config.

That gives you the convenience of Codex-style setup without the fragility of embedding the Codex tool itself.
