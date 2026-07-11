# Living to Tell Preview 0.1.45

0.1.45 turns the Collection Agent into a real long-form coauthoring workspace while keeping the manuscript under the author's control.

## Collection Coauthor Agent

- Keep several named sessions for different lines of work inside one book project.
- Switch deliberately between **Discuss**, **Plan**, **Draft**, and **Review**.
- Start a novel from a vague idea, compare directions, plan scenes, write candidate prose, or inspect continuity.
- See what the next request can read: collection structure, confirmed Project Bible, visible session summary, recent turns, and explicit `@` references.
- Choose one AI profile for the next request without silently mixing in the default model.

## Drafts Stay Outside the Manuscript

- Scene prose is saved to a local Draft Library first.
- Edit the primary draft, request a variant, leave the page, and return later without losing it.
- Apply a draft only by creating an article, appending to an article, or replacing one explicit unique selection.
- Existing-article write-back checks that the body has not drifted and creates a version snapshot before changing text.

## Memory With Boundaries

- Conversations use a visible work summary plus recent turns; original messages remain stored locally.
- Only manual Project Bible saves or accepted memory proposals become book canon.
- Rejected proposals and unapplied drafts never become memory.
- Author Portrait learns only from completed author-draft-to-final-chapter cycles. After three new cycles, the app shows a local reminder instead of automatically spending tokens.

## Long-Task Behavior

- Leaving the Agent tab does not stop the backend run.
- Returning reconnects to stored state and never automatically resends the provider request.
- Interrupt stops local waiting. A request already sent to the provider may still finish or incur cost.
- If the app restarts during a run, that run is marked failed with a safe explanation rather than being submitted again.

## Installers

- `LivingToTell_0.1.45_x64-setup.exe`
- `LivingToTell_0.1.45_x64_zh-CN.msi`

The Windows preview remains unsigned. Download installers only from this repository's GitHub Release page.
