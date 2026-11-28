Completed: Plan drafted; worktree `/Volumes/SSD/Programming/jre-wt-225` on branch `docs/issue-225-for-human-summaries`.
Next: User approval of this checklist, then stage-1 review (Codex = overview, Antigravity = detail), then drafting.
Open: Source files for `for-human/` are not yet read in full; no review has been requested.

# Issue #225: Japanese Summaries in works/for-human

Models in use: coordinator and decisions Sonnet 5.5 (Claude Code); drafting Haiku 5.5 subagents; mechanical checks `audit` (Haiku 5.5); final check `advisor` (Opus 5.5); external reviewers Codex and Antigravity.

Approval condition: the user approves this checklist, and every item below is confirmed.

## Scope

Create the Japanese summaries that `works/README.md` promises under `works/for-human/`.
The sources are the English documents under `works/for-agent/`, which stay unchanged.
Follow `~/.claude/docs/works-document-structure.md`: order is point, purpose, approach; diagrams and tables first; Mermaid preferred; no long prose.

- One summary per source document, with the same relative path and file name (1:1 mirror). 14 files:
  - `design-document/` 9 files (6 numbered folders, ADRs included).
  - `requirement-definition-document/` 2 files.
  - `implementation-plan/` 3 files.
- `index.md` in each of those three folders (Japanese, number / name / content), plus an update of `for-human/README.md`.
- Each summary starts with a link to its `for-agent` source and a one-line note that `for-agent` wins on conflict.
- `checklist/` has no `for-human` counterpart. `requirements-document/` is not created.
- No English versions of `for-human/` files and no edits under `for-agent/`.
  A mismatch found in `for-agent/` is recorded in the work log and raised with the user; it is not silently fixed.
- Size guide: at most about 40 lines per summary, at least one diagram or table each.

## Rule check at start

- Required skills: `karpathy-guidelines`, `ponytail`, `superpowers` are all listed as available in this session.
- Start questions: the design basis is already fixed by `works/`; the cycle is the minimal update for a documentation change.
- Review policy: `both` (from `works/README.md`). Random assignment for this Issue: overview = Codex, detail = Antigravity.
  Fallback if one is unavailable: GitHub Copilot takes over that mode, and the swap is recorded.
- TDD (stage 2) and effect verification (stage 4): not applicable, because this is documentation with no behavior and no effect metric.
  Substitute checks are the tool run and the consistency check below. Whether the summaries are easier to read for people is not measured here.

## Roles

| Role                     | Who                     | Work                                                                                 |
| ------------------------ | ----------------------- | ------------------------------------------------------------------------------------ |
| Coordinator and decision | Sonnet 5.5 (this agent) | Scope, summary template, handling review findings, integration                       |
| Repository search        | `search` (Haiku 5.5)    | Layout survey (done)                                                                 |
| Drafting                 | Haiku 5.5 subagents     | Three batches with disjoint files: design, requirements, plans; then indexes, README |
| Mechanical checks        | `audit` (Haiku 5.5)     | Prettier, markdownlint-cli2, textlint, links, Mermaid syntax, for-agent consistency  |
| Overview review          | Codex                   | Drift from purpose, excess structure, step order                                     |
| Detail review            | Antigravity             | Facts, numbers, adoption decisions and links against `for-agent`                     |
| Final check              | `advisor` (Opus 5.5)    | Integrated diff before the PR                                                        |

Drafting is delegated only after approval. Haiku does not decide content scope or answer spec-level review findings.
`audit` runs from a disposable worktree of the default branch, so commit before it runs.

## Acceptance (Issue #225)

- [ ] Summaries of the design documents are made, diagram and table centered (9 files).
- [ ] Summaries of the requirements and plans are made (2 + 3 files).
- [ ] `for-human/README.md` and the three `index.md` files are updated; the "not made yet" sentence is removed.
- [ ] After the translation (Issue #224, merged), each summary is checked against `for-agent` for conflicts; the result is recorded.

## Steps

- [ ] User approves this checklist (models and delegation included).
- [ ] Stage-1 review of this plan: overview (Codex) and detail (Antigravity); findings handled or recorded.
- [ ] Read each source in full and write the summary template (heading order, source link, diagram rule).
- [ ] Draft 14 summaries in three Haiku batches.
- [ ] Write the three `index.md` files and update `for-human/README.md`.
- [ ] Run Prettier, markdownlint-cli2 and textlint in that order; record any finding left unfixed with the reason.
- [ ] Validate every Mermaid block and every relative link, including the link back to each source.
- [ ] `audit` consistency check: numbers, dates, adoption results, and names match `for-agent` for each summary.
- [ ] Coordinator spot-checks the ADR summaries, where an adoption result could be flipped (the decision column of the ADR table: adopted, not adopted, or superseded).
- [ ] Stage-3 review of the diff: overview (Codex) and detail (Antigravity); findings handled or recorded.
- [ ] `advisor` checks the integrated diff.

## Common completion

- [ ] Commit, push, open a PR that links Issue #225 (secrets and the private feedback address excluded).
- [ ] Required CI checks pass; merge by the repository's auto-merge rule.
- [ ] No release: only `works/` changes, no skill or tool change. Confirm this against `~/.claude/docs/ci-release.md` before merging.
- [ ] Delete the remote and local branch, remove the worktree, and report what was kept and why.
- [ ] Record skipped or unavailable reviews in Issue #225 (none expected).

## Work log

New entries go at the top of this section.

- 2026-11-29: Checklist drafted. Random assignment: overview = Codex, detail = Antigravity. `gh` needs the sandbox disabled (TLS error); worktree created outside the sandbox.
