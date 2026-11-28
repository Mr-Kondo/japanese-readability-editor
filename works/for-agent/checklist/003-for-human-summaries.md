Completed: 15 summaries, 3 indexes, and the README are written and committed; lint, links, audit, and both stage-3 reviews are done.
Next: `advisor` checks the integrated diff, then PR, CI, merge, and cleanup.
Open: Seven of ten Mermaid diagrams were checked by eye only; whether the summaries are easier for people to read is not measured.

# Issue #225: Japanese Summaries in works/for-human

Models in use: coordinator and decisions Sonnet 5.5 (Claude Code); drafting Haiku 5.5 subagents; consistency and link checks `audit` (Haiku 5.5); final check `advisor` (Opus 5.5); external reviewers Codex and Antigravity.

Approval condition: the user approves this checklist, and every item below is confirmed.

## Scope

Create the Japanese summaries that `works/README.md` promises under `works/for-human/`.
The sources are the English documents under `works/for-agent/`, which stay unchanged.
Follow `~/.claude/docs/works-document-structure.md`: order is point, purpose, approach; diagrams and tables first; Mermaid preferred; no long prose.

- One summary per source document, with the same relative path and file name (1:1 mirror). 15 files:
  - `design-document/` 10 files: `001-knowledge-index/` (`pilot-plan-adr.md`, `conclude-pilot-adr.md`), `002-installer/remove-install-py-adr.md`, `003-structure-rules/` (`opq-analysis-adr.md`, `opq-reeval-adr.md`, `section-single-message-adr.md`), `004-human-review-tooling/` (`design-survey-document.md`, `integration-document.md`), `005-readability-principles/design-principles-document.md`, `006-fiction-mode/design-references-document.md`.
  - `requirement-definition-document/` 2 files: `001-evaluation-tool-selection.md`, `002-human-evaluation-methods.md`.
  - `implementation-plan/` 3 files: `001-next-improvement-plan.md`, `002-public-document-corpus.md`, `003-concretization-example-plan.md`.
- `index.md` in each of those three folders (Japanese), plus an update of `for-human/README.md`.
  - `design-document/index.md`: numbered folders (number, name, content) and the ADR table (date, `status`, decision), each linking to its summary.
    Provenance hashes and frozen-evidence notes stay in the `for-agent` index; the Japanese index links to it.
  - The other two list number, name, and content, with links to the summaries.
- Each summary starts with a link to its `for-agent` source and a one-line note that `for-agent` wins on conflict.
  Links to other documents inside a summary point to the `for-human` summary, never to a local absolute path.
- `checklist/` has no `for-human` counterpart. `requirements-document/` is not created.
- No English versions of `for-human/` files. Source documents under `for-agent/` (`design-document/`, `requirement-definition-document/`, `implementation-plan/` and their `index.md` files) are not edited.
  The only `for-agent/` files that change are this checklist and `checklist/index.md`.
  A mismatch found in a source document is recorded in the work log and raised with the user; it is not silently fixed.
- Size guide: at most about 40 lines per summary, at least one diagram or table each.

## Rule check at start

- Required skills: `karpathy-guidelines`, `ponytail`, `superpowers` are all listed as available in this session.
- Start questions: the design basis is already fixed by `works/`; the cycle is the minimal update for a documentation change.
- Review policy: `both` (from `works/README.md`). Random assignment for this Issue: overview = Codex, detail = Antigravity.
  Fallback if one is unavailable: GitHub Copilot takes over that mode, and the swap is recorded.
- TDD (stage 2) and effect verification (stage 4): not applicable, because this is documentation with no behavior and no effect metric.
  Substitute checks are the tool run and the consistency check below. Whether the summaries are easier to read for people is not measured here.

## Roles

| Role                     | Who                     | Work                                                                                             |
| ------------------------ | ----------------------- | ------------------------------------------------------------------------------------------------ |
| Coordinator and decision | Sonnet 5.5 (this agent) | Scope, summary template, handling review findings, integration, lint run and fixes               |
| Repository search        | `search` (Haiku 5.5)    | Layout survey (done)                                                                             |
| Drafting                 | Haiku 5.5 subagents     | Pilot, then three batches with disjoint files: design, requirements, plans; then indexes, README |
| Consistency check        | `audit` (Haiku 5.5)     | Read-only: links, numbers, dates and adoption results against `for-agent`, per committed branch  |
| Overview review          | Codex                   | Drift from purpose, excess structure, step order                                                 |
| Detail review            | Antigravity             | Facts, numbers, adoption decisions and links against `for-agent`                                 |
| Final check              | `advisor` (Opus 5.5)    | Integrated diff before the PR                                                                    |

Drafting is delegated only after approval. Haiku does not decide content scope or answer spec-level review findings.
`audit` cannot edit files and runs in a disposable worktree, so the writer commits first and passes the branch name; `audit` reads that commit.
Formatting and fixes are done by the writer on the work branch. A fix made after `audit` is re-checked for the changed lines.

## Acceptance (Issue #225)

- [x] Summaries of the design documents are made, diagram and table centered (10 files).
- [x] Summaries of the requirements and plans are made (2 + 3 files).
- [x] `for-human/README.md` and the three `index.md` files are updated; the "not made yet" sentence is removed.
- [x] After the translation (Issue #224, merged), each summary is checked against `for-agent` for conflicts; the result is recorded.

## Steps

- [x] User approves this checklist (models and delegation included).
- [x] Stage-1 review of this plan: overview (Codex) and detail (Antigravity); findings handled or recorded (see work log).
- [x] Read the `001-knowledge-index` sources in full and finalize the summary template (heading order, source link, diagram rule).
- [x] Pilot: draft the 2 summaries of `001-knowledge-index` and its rows in the design index.
      Check that the index alone shows the purpose, the current conclusion, and the related summaries. Adjust the template, then delegate the rest.
- [x] Draft the remaining 13 summaries in three Haiku batches.
- [x] Write the three `index.md` files and update `for-human/README.md`.
- [x] Linting by the writer, with `node_modules` linked from the main checkout: Prettier, markdownlint-cli2, then textlint, in that order, via `sh tools/lint_md.sh`. The `for-agent` files are English, so textlint runs only on `for-human/`.
      No `--fix` for textlint. `ja-no-mixed-period` is off, so check missing sentence-final periods in paragraphs by eye. Record any finding left unfixed with the reason.
- [x] Validate every Mermaid block with the Mermaid validator tool of this session; if it is unavailable, check syntax by eye and record that as a limit.
- [x] Check every relative link resolves, including the link back to each source.
- [x] Commit, then `audit` checks consistency for all 15 summaries: numbers, dates, identifiers, and names match `for-agent`.
- [x] Coordinator checks all 6 ADR summaries: `status`, date, and the adoption result in the Decision column match the source (a record can be `accepted` and still "not adopted").
- [x] `git diff --name-only origin/main` lists only `works/for-human/**`, this checklist, and `checklist/index.md`. No `evals/` or source-document change.
- [x] Stage-3 review of the diff: overview (Codex) and detail (Antigravity); findings handled or recorded.
- [ ] `advisor` checks the integrated diff.

## Common completion

- [ ] Commit, push, open a PR that links Issue #225 (secrets and the private feedback address excluded).
- [ ] Required CI checks pass; merge by the repository's auto-merge rule.
- [ ] No release: only `works/` changes, no skill or tool change. Confirm this against `~/.claude/docs/ci-release.md` before merging.
- [ ] Delete the remote and local branch, remove the worktree, and report what was kept and why.
- [ ] Review records (target commit, stage, reviewer, mode, model if confirmed, findings, response, reason, unchecked items) are in this work log; a summary is posted to Issue #225. Skipped or unavailable reviews are recorded in the same places (none expected).

## Work log

New entries go at the top of this section.

- 2026-11-29 drafting and checks, target commit `32525ae` and later.
  - Pilot on `001-knowledge-index` passed: the design index row alone showed purpose, conclusion, and links. Template then fixed (body in desu/masu, bullets in dearu, no line starting with `#NNN`).
  - Drafting: 4 Haiku 5.5 subagents with disjoint files. Indexes and README written by the coordinator.
  - Lint (Prettier, markdownlint-cli2, textlint) on all `for-human` files: 0 findings after fixes. 53 relative links resolve. `git diff --name-only origin/main` shows only `for-human/`, this checklist, and `checklist/index.md`.
  - Mermaid: 3 of 10 diagrams validated with the validator tool (`valid: true`: the decision flow with diamonds, the conclusion branch with a `#` label, the survey flow with edge labels). The other 7 are plain flowcharts with quoted labels and were checked by eye only.
  - `audit` (Haiku 5.5), target `878e116`, read-only: 14 of 15 matched the sources; 1 sentence in `implementation-plan/001` overstated "no study exists". Also fixed: a proposal written as settled (`integration-document`), unlabeled condition order in `conclude-pilot-adr` (now stated as not given in the source), and dropped decisions or reasons in `remove-install-py-adr` and `opq-analysis-adr`.
    The reported incomplete design index was an older commit; the index was completed afterward. Not checked by `audit`: GitHub state of Issues #32 to #36, the raw data behind the pilot timings.
  - Coordinator check of the 6 ADRs: `status` and date match the sources, and the Decision column shows adopted, not adopted, or superseded as in the source index.
  - Stage-3 review, target commit `32525ae`.
    - Overview, Codex (requested `gpt-6.1-sol`, medium; actual model unconfirmed): this log was stale (accepted, updated now); two summaries carry too much operational detail (trimmed: the validator and tool-ID details in `implementation-plan/002`, three method details in `requirement-definition-document/002`; still above the 40-line guide at 62 and 51 lines). Not checked by Codex: Git diff, tool runs, rendering.
    - Detail, Antigravity (requested `gemini-4-hydrogen-medium`, medium; actual model unconfirmed; no shell): no factual finding. Two paragraphs in dearu style were changed to desu/masu. Not checked by Antigravity: the diff list, lint results, Mermaid tool results.

- 2026-11-29 stage-1 review, target commit `08dfa3c`.
  - Overview, Codex (requested `gpt-6.1-sol`, medium; actual model unconfirmed):
    - Added a pilot before the bulk draft, so the index is shown to carry purpose, conclusion, and links. Accepted.
    - Moved formatting and fixes to the writer; `audit` only reads committed work. Accepted.
    - Not checked by Codex: full source facts, the Issue text on GitHub, tool run results.
  - Detail, Antigravity (requested `gemini-4-hydrogen-medium`, medium; actual model unconfirmed; first run failed on a denied shell permission, rerun with a document bundle and read-only access):
    - File count was 14 and design 9; the correct count is 15 and design 10 (counted by folder). Accepted; file list added.
    - `audit` worktree wording: the worktree is disposable and sees only commits, so commit and pass the branch name. Accepted.
    - "No edits under `for-agent/`" conflicted with this checklist; limited to source documents and indexes, plus a `git diff --name-only` check. Accepted.
    - Mermaid and lint methods were vague; now stated with fallback and the by-eye period check. Accepted.
    - Index scope and link direction stated. Accepted. All 6 ADRs checked instead of a spot check. Accepted.
    - Not checked by Antigravity: `node_modules` state, a Mermaid CLI, full source text, the Issue text.
    - Coordinator note: `node_modules` is absent in this worktree and present in the main checkout; the writer links it.
- 2026-11-29: Checklist drafted. Random assignment: overview = Codex, detail = Antigravity. `gh` needs the sandbox disabled (TLS error); worktree created outside the sandbox.
