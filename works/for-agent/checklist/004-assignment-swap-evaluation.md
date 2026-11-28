Current: checklist approved by the user; plan, cases, runner written; stage-1 review done and its findings applied (see work log).
Next: re-check the fixed plan with the reviewers if needed, commit it, then generate the 72 outputs.
Open: no baseline exists for how often a rewrite swaps assignments; if the old version never swaps, the effect cannot be measured (see Decision rules).

# Issue #218: Evaluate a manual check for swapped per-topic assignments

Models in use: coordinator and decisions Sonnet 5.5 (Claude Code); case generation runs with `sonnet` through the existing runner pattern; run orchestration and counting Haiku 5.5 subagent; consistency check `audit` (Haiku 5.5); final check `advisor` (Opus 5.5); reviewers Codex and Antigravity.

Approval condition: the user approves this checklist, and every item below is confirmed.

## Scope

Decide whether to add one manual-check line, plus one self-made example, to the rules: "the set of per-topic assignments (who, which, when) is the same before and after the rewrite".
Evaluate old (main) against new (main plus that line) on the same input set, with the plan fixed before any run.

- In scope: the draft wording, `evals/assignment-swap.md` (plan, fixed before running), `evals/assignment-swap-run/` (cases, runner, outputs), `evals/assignment-swap-result.md`, and the adopt or decline record.
- If adopted: one line in `readability-rules.md` (near the guarantee-subject check at line 247 and the checklist at line 739), the matching `SKILL.md` phrase, one example, a guard test, and a version bump per `~/.claude/docs/skill-development.md`.
- Out of scope: porting the upstream detector (the Issue excludes it); any change to `compare_rewrite.py`. Whether a detector is worth building is a separate decision, noted in the result only.
- The four uncommitted changes in the working tree (`docs/feedback.md`, `change-report.md`, `feedback.md`, `tests/test_skill_guards.py`) and `.codex/`, `evals/gap-note2-run/o*.json` predate this work. They are not committed here.

## Rule check at start

- Required skills `karpathy-guidelines`, `ponytail`, `superpowers` are listed as available in this session.
- Start questions: the design basis is already fixed by `works/` and the Issue; the cycle is the targeted evaluation cycle used for #206 and #208 (`evals/gap-note.md`, `evals/gap-note2.md`).
- Review policy: `both` (from `works/README.md`). Random assignment for this Issue (drawn 2026-11-29): overview = Codex, detail = Antigravity. If one is unavailable, GitHub Copilot takes over that mode and the swap is recorded.
- TDD: the guard test for an adopted rule is written first and must fail before the rule is added. If declined, no rule changes, so TDD does not apply and the evaluation record is the evidence.
- Effect verification (stage 4) is the evaluation itself. Its effect is limited to the artificial inputs; real-use frequency stays unmeasured.

## Evaluation plan

The plan, counting rules and decision rules live only in `evals/assignment-swap.md` (frozen before the run). This checklist does not repeat them.

- Versions: old = main; new = old plus `evals/assignment-swap-run/candidate.diff` (rules section, checklist line, `SKILL.md` phrase, one example).
- 12 cases (S 6, R 3, C 3) x 3 runs x 2 versions = 72 `sonnet` calls, no separate cost cap.
- The swap judgment is a blind human reading of all 72 outputs; the runner counts only lost content, invented numbers and extra remarks.

## Roles

| Role                     | Who                     | Work                                                                                    |
| ------------------------ | ----------------------- | --------------------------------------------------------------------------------------- |
| Coordinator and decision | Sonnet 5.5 (this agent) | Plan, cases, decision rules, reading flagged outputs, adopt or decline, rule wording    |
| Repository search        | `search` (Haiku 5.5)    | Done: not needed beyond the greps already run                                           |
| Run                      | Haiku 5.5 subagent      | Run `--generate` and `--count`; it does not change cases or rules, and does not label  |
| Consistency check        | `audit` (Haiku 5.5)     | Read-only: counts, links, and the result file against the run records, per commit       |
| Overview review          | Codex                   | Drift from the Issue, excess structure, whether the plan can show an effect at all      |
| Detail review            | Antigravity             | Cases, regexes, counting, and the decision rules                                        |
| Final check              | `advisor` (Opus 5.5)    | Integrated diff before the PR                                                           |

Delegation happens only after approval. Haiku does not decide cases, counting, or the adopt or decline outcome.

## Acceptance (Issue #218)

- [ ] The evaluation plan was written before the run.
- [ ] Old and new versions were compared on the same evaluation set.
- [ ] The outcome is recorded with its reason (adopt: rule, example, test; decline: reason).
- [ ] The result states that the effect holds only for the artificial inputs.

## Steps

- [x] User approves this checklist (models, delegation, and the 72-call cost included).
- [x] Stage-1 review of this plan: overview (Codex) and detail (Antigravity); findings handled or recorded.
- [x] Write the new-version wording and the cases; freeze `evals/assignment-swap.md` and commit it before any generation (freeze = the commit).
- [ ] Prepare the old and new skill folders, then generate 72 outputs and count (Haiku subagent).
- [ ] Read every flagged output and a sample of the rest; apply the decision rules as written.
- [ ] Record the result in `evals/assignment-swap-result.md` and the Issue; update `evals/README.md` if it lists evaluations.
- [ ] If adopted: write the guard test first and confirm it fails, add rule, phrase and example, bump the version, and run `python3 -m unittest discover -s tests`.
- [ ] Lint (Prettier, markdownlint-cli2, textlint, in that order) on the changed Markdown.
- [ ] `audit` checks consistency; stage-3 review by both reviewers; `advisor` final check.
- [ ] `git diff --name-only origin/main` lists only files named in Scope.
- [ ] PR, auto-merge, release if the skill changed, then delete the work branch and temporary files and report what was kept.

## Work log

(newest first)

- 2026-11-29: Stage-1 review (overview Codex gpt-6.1-sol, detail Antigravity gemini-4-hydrogen-medium; raw output in `feedback/assignment-swap-stage1/`). Applied: `candidate.diff` was non-recursive and held only the `SKILL.md` change, so it was regenerated with all four files; blind ids were odd/even by version, so `blind.md` now uses b01-b72 with a stored map; content loss now blocks adoption in every group; unclear counts against the new version and more than 5 means no adoption; `REMARK` narrowed to assignment words; `must_keep` regexes for 林 and 川口駅 no longer match inside 小林 and 西川口駅; `score` validates labels; the checklist no longer repeats the plan. Not applied: none.

- 2026-11-29: Drafted. Issue #218 read; existing evaluation pattern (#206, #208) and the prior swap measurements in `docs/upstream/reviews/yomiyasu-v3.4.1.md` reused. The `gh` TLS failure inside the sandbox needed a retry outside it.
