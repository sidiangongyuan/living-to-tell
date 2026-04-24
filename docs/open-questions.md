# Writer Open Questions v0.2

The following planning items have been clarified.

## 1. Confirmed Decisions

- AI deployment: cloud API first
- Writing pattern: write whenever an idea appears
- Long-form target: prose first
- Style strength: light literary polishing first
- Interface direction: minimal journal

## 2. Clarification on AI Modes

### Cloud AI

The app sends selected text to a remote model provider and receives a rewrite result back.

### Local Offline AI

The app runs against a model on the user's own machine or a self-hosted local service, without sending the text to a cloud provider.

For this project, cloud AI is the confirmed MVP choice.

## 3. Remaining Questions

There is no major blocker left for MVP implementation.

The remaining items are future-facing rather than launch-blocking.

### Export Priority

Which format should be treated as the main export target after Markdown and TXT?

- DOCX
- PDF
- no need yet

### Reference Library Input

First-pass decision:

- references are mainly added by direct paste
- source title should be required
- source author may be optional

### AI Chat Scope

First-pass decision:

- first usable release focuses on writing-specific rewrite actions only
- free-form AI chat moves to a later milestone

### Future Feature Reservation

Which future options should influence architecture early?

- local AI models
- voice dictation
- motif tracking
- calendar view

### Reserved Future Features

Which future options should influence architecture early?

- local AI models
- voice dictation
- chapter planning board
- motif tracking
- calendar view

