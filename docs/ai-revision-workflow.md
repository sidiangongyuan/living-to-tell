# AI Revision Workflow Plan

[中文](ai-revision-workflow.zh-CN.md) · English

This plan captures the next UX pass for Writer's AI-assisted editing flow. It is
product-facing: the goal is to make AI suggestions easy to compare, safe to
apply, and clearly different across task types.

## Problems to solve

1. The fragment context pane has a **Polish** action that starts immediately,
   while the AI Workspace also has a **Polish** tool with settings. The
   difference is unclear.
2. After an AI task completes in the AI Workspace, the result is shown alone.
   Users must switch context to see the original text.
3. When only a selection is targeted, the UI should make it obvious that only
   that selection was sent and only that range will be affected.
4. Applying AI should not feel like losing the author's original words. Writer
   already saves snapshots, but the original version should also be visible in
   the review flow.
5. Polish, expand, continue, summarize, outline, and diagnostics currently share
   too much UI state and do not feel task-specific enough.

## Product principles

- **Preview before write-back**: every destructive AI result must be reviewed
  before it touches a live fragment or work section.
- **Original beside suggestion**: rewrite-style tasks should show the source and
  generated text side by side, similar to a Markdown preview / diff workflow.
- **Selection is a first-class target**: selected text should be displayed as the
  source when a selection is active; long selections can be collapsed or opened
  in a larger compare view.
- **Task settings do not leak**: changing from Polish to Expand or Continue
  should not silently reuse unrelated parameters.
- **Plain text remains safe**: until Writer has a rich tracked-changes editor,
  original preservation should rely on compare views, linked variants, and
  snapshots rather than fragile inline markup inside the main body.

## Target UX

### 1. Fragment context pane actions

Replace the current immediate **Polish** button behavior with a routing action:

- Label: **AI Polish...** / **AI 润色...**
- Behavior:
  - Open the AI Workspace.
  - Bind the current fragment.
  - If text is selected, default target to **Selection**.
  - Select the **Polish** task.
  - Keep settings visible before the user runs the task.
- Optional later shortcut: a separate **Quick Polish** command can exist only if
  it has a visible default preset and a clear confirmation path.

The **Include in Work** action can remain a separate curation action.

### 2. AI result compare layout

For rewrite-style tasks, replace the single result box with a compare region:

| Left | Right |
| --- | --- |
| Original source, read-only | AI result, editable before apply |

Rules:

- For target **Selection**, the left side shows only the selected text.
- For target **Fragment** or **Work Section**, the left side shows that full
  source body.
- For **Continue**, the left side is the context ending; the right side is only
  the new continuation.
- For report-style tasks, keep a report viewer instead of a rewrite compare
  pane.
- Both panes should scroll independently at first; synchronized scrolling can be
  added later.

### 3. Context pane preview for selections

The right context pane is narrow, so it should not become the main diff viewer.
Use it for compact state only:

- Show target kind: **Selected text**, **Whole fragment**, **Work section**, etc.
- Show selected character count.
- If the selected text is short, show a small excerpt.
- If it is long, show the first lines plus an **Open compare** / **Open AI
  Workspace** action.

The full side-by-side comparison should live in the AI Workspace or a compare
dialog, not inside the metadata pane.

### 4. Applying while preserving the original

Recommended staged behavior:

#### P0: no schema change

- Keep the default output as **Preview only**.
- Continue saving snapshots before destructive apply.
- Make the compare view always visible before apply.
- Add explicit apply options:
  - **Replace selected text** / **Replace fragment**
  - **Save AI result as new fragment**
  - **Copy result**
- Make the destructive apply button text specific, e.g. **Replace selection**
  instead of the generic **Apply**.

#### P1: linked AI variant

- Save AI output as a linked variant/card for the original fragment.
- Show variant metadata: task, provider, model, date, target range, and original
  excerpt.
- Let users reopen the original-vs-AI compare view from version history or the
  fragment context pane.

#### P2: tracked changes / rich review mode

- Add a review renderer that can show deleted original text in muted
  strikethrough and AI additions in a highlight color.
- Keep the live editor plain-text-safe unless / until a rich text editing model
  is introduced.
- Do not store provider-specific HTML as the canonical fragment body.

### 5. Task-specific designs

Each task should have its own parameter state and defaults.

| Task | Primary source | Key controls | Default output | Review style |
| --- | --- | --- | --- | --- |
| Polish | selection / fragment | intensity, style hint, preserve voice / meaning | preview | side-by-side rewrite |
| Expand | selection / fragment | target length or ratio, expansion focus, preserve facts | preview or save as fragment | side-by-side rewrite |
| Continue | fragment ending / selected ending | continuation length, direction, constraints | insert after selection / append later | context + new continuation |
| Style transfer | selection / fragment | style profile, strength, voice preservation | preview | side-by-side rewrite |
| Summarize | fragment / work / collection | summary length, bullet vs paragraph | report / save as fragment | source + summary |
| Outline | fragment / work | outline depth, format | report / save as fragment | source + outline |
| Title | fragment / work | title count, tone | report / copy | candidate list |
| Structure diagnose | fragment / work | severity filter later | report only | issue cards |
| Consistency check | work / collection | scope and reference attachments | report only | issue cards + citations |
| Library Q&A | attachments | question and citations | report only | answer + citations |

Switching tasks should restore that task's last local settings or reset to its
own defaults. It should not carry a Polish style/intensity into Continue unless
the user explicitly chooses to reuse it.

## Implementation phases

### Phase 1 — clarify and compare

- Route the context-pane **Polish** action to AI Workspace instead of running the
  legacy immediate rewrite flow.
- Add a side-by-side source/result compare region for AI Workspace rewrite tasks.
- Preserve target selection metadata in the result UI.
- Rename generic **Apply** labels to specific destructive actions.
- Store task-specific parameter state in memory while the panel is open.

### Phase 2 — variants and reopenable comparisons

- Add a linked AI variant model or reuse AI cards for accepted/generated results.
- Let users save a result as a linked variant without replacing original text.
- Add an entry point from version history / fragment context to reopen the
  compare view.

### Phase 3 — visual diff / tracked changes

- Add a rendered diff view with muted strikethrough deletions and colored
  additions.
- Consider a richer editor only after the storage and export implications are
  clear.

## Acceptance criteria for Phase 1

- Clicking **AI Polish...** from the fragment context pane never starts a request
  immediately; it opens AI Workspace with editable settings.
- If text was selected before entering AI Workspace, the target defaults to
  **Selection** and the source compare pane contains exactly that selection.
- After a rewrite-style task succeeds, original and AI result are visible at the
  same time.
- The AI result pane remains editable before write-back.
- Destructive write-back buttons name the exact action: replace selection,
  replace fragment, or replace section.
- Switching from Polish to Expand or Continue does not silently reuse irrelevant
  Polish settings.
- Existing safeguards still pass: snapshots/version history before destructive
  write-back, tests green, no credentials or private data committed.

## Likely code touch points

- `src/writer/ui/main_window.py` — context-pane action routing and AI scope
  binding.
- `src/writer/ui/widgets/context_pane.py` — action labels and compact selection
  metadata.
- `src/writer/ui/panels/ai_workspace_panel.py` — task selection API,
  task-specific parameter state, compare UI, apply labels.
- `src/writer/ui/services/ai_apply.py` — apply outcome labels and any future
  variant save helper.
- `src/writer/ui/dialogs/rewrite_compare_dialog.py` — reusable compare concepts
  for legacy and workspace flows.
- `src/writer/ui/i18n.py` — English / Chinese labels for new actions and states.
- `tests/` — UI tests for routing, selection targets, compare rendering, and
  task-specific parameter isolation.