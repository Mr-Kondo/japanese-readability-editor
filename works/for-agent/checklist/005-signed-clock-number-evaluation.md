Completed: implementation, frozen comparisons and initial full tests pass.
Next: complete independent reviews, release v0.25.2, update this Mac and clean up.
Open: publication and delivery verification remain pending.

# Signed and Clock Number Evaluation Implementation Plan

> Execute the approved checklist with `superpowers:executing-plans`. Preserve the role assignments below.

**Goal:** Evaluate numeric comparison of triangle signs and Japanese AM/PM clock times.

**Architecture:** Keep extraction and canonical comparison in `compare_rewrite.py`. Reuse `NUMBER_RE`, `number_key`, and the existing comparison and test helpers. Keep displayed source text and line references intact.

**Tech Stack:** Python standard library and unittest; existing Markdown tooling.

**Spec:** [Issue #219](https://github.com/Mr-Kondo/japanese-readability-editor/issues/219).

## Roles and Approval

Use `/Users/masatomiwada/.codex/roles.yaml`, as requested by the user.

| Role          | Model and effort     | Responsibility                                                    |
| ------------- | -------------------- | ----------------------------------------------------------------- |
| main          | `gpt-6.1-sol`, high  | Design decisions, implementation, coordination, and integration   |
| search / grep | `gpt-6.1-terra`, low | Read-only discovery and references, in fresh contexts             |
| audit         | `gpt-6.1-terra`, low | Diff and tests in an isolated snapshot; remove its owned worktree |
| advisor       | `gpt-6.1-sol`, max   | Final integrated diff only; read-only, fresh context, no tools    |

If a configured model is unavailable, stop that role without silently substituting another model.
The user's role request governs model allocation.
Do not assign implementation to discovery or audit roles.
Follow the existing permission and cost limits.

Review policy is `both`, from `works/README.md`.
Assign overview and detail separately to Claude Code and Antigravity.
Randomize the assignment for each request.
Keep planning, Red tests, implementation, and effect-verification review records distinct.
Follow the documented fallback if an external reviewer is unavailable.
The advisor review is additional to these stage reviews.

- [x] User approves this checklist, boundaries, and models before implementation.
      Approval: 2026-11-29, 「進めてくれ」.

## Global Constraints

- Do not read or copy upstream implementation; use the Issue and local behavior as requirements.
- Preserve CLI arguments and output schema. Keep line references and analyzer selection.
- Preserve existing normalization outside the approved scope.
- Preserve all pre-existing local changes and untracked files; stage only this Issue's changes.
- Store local evidence in Git-ignored `feedback/issue-219/`.
- Update `feedback/index.md` when adding records.
- Add no dependencies or new parser framework.
- Do not change historical frozen evaluation records.
- Do not claim that synthetic checks measure frequency or reader benefit in real use.

## Proposed Behavior Boundaries

The user approved these evaluation boundaries on 2026-11-29. Adoption depends on the results.

1. Read adjacent `▲` and `△` before a number as negative signs. Match equivalent minus notation. Report a negative-to-positive change.
2. Apply `午前` and `午後` only to an adjacent valid hour ending in `時`. Exclude `時間`. Compare valid hours in 24-hour notation. Preserve minute and second comparison.
3. Read `午前0時` and `午前12時` as midnight. Read `午後0時` and `午後12時` as noon. Do not convert invalid qualified hours to valid times.
4. Preserve dates and ranges. Keep list markers and durations unchanged. Preserve protected code and URLs. Do not generalize rating rows containing `○△×`.
5. Adopt only evaluated behavior. If wider parsing is required, record why and request a design decision.

ASCII `-` and U+2212 `−` are signs.
An ASCII letter, digit, comma, decimal point, asterisk, kanji or katakana blocks this interpretation.
A minus directly after an extracted numeric item, or separated only by whitespace, is a range separator.
This includes unit-bearing ranges.
Hyphenated identifiers, dates and numeric ranges retain their prior behavior.
Japanese prose can precede a negative amount.
Adjacent triangles are interpreted as signs, including those intended as bullets.
Separated triangles remain markers.
Valid unqualified clock hours also normalize padding (`03時` equals `3時`).
This is required for transitive equivalence with both `午前03時` and `午前3時`.
Other padded numbers and durations retain existing normalization.
Space-separated qualifiers remain a known detection limit.
Inherited qualifiers and word-form negatives need human review.
Signs after kanji/katakana labels and whitespace-separated lists of signed values remain detection limits.
Supplementary Red tests preserve unrecognized-counter and spaced ranges without new alarms.
The frozen equivalent-expression group remains unchanged.

Review resolution: protecting non-ASCII URL paths extends the old ASCII-only URL tokens.
Record the complete extended token in existing URL fields; retain old term and role masking.
This intentional scope extension prevents duplicate numeric alarms within protected URLs.
Undelimited prose attached to a URL can hide a following number; this remains a lexical limit.
Markdown emphasis and table boundaries must preserve following numeric comparisons.

Before candidate execution, freeze an additional existing rewrite corpus and its input hashes.
Reject new numeric alarms unless independently confirmed as a scoped true change.
The synthetic fixture is regression evidence, not an independent accuracy estimate.
Six of the 78 existing pairs contain the target notation; 23 pairs already have numeric alarms.
Also freeze tracked Markdown under docs, evals and the skill for an extraction screen.
Every extraction difference must be a scoped adjacent sign or valid clock normalization.
Reject unexplained differences or extra/lost numeric items.

## Scope and Review Focus

| Area                           | Expected reach                                                                                                   |
| ------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| Shared extraction and equality | `skills/japanese-readability-editor/scripts/compare_rewrite.py`: `NUMBER_RE`, `number_key`, and their callers    |
| Behavior tests                 | `tests/test_compare_rewrite.py`; inspect matching and CLI tests for affected expectations                        |
| Integration                    | Existing consumers of comparison output, including readability review tools; preserve their interface            |
| Evaluation                     | Freeze cases and expectations before candidate execution; store raw results privately and summarize the decision |
| Documentation and distribution | Update only affected numeric-comparison guidance; if shipping a skill version, verify release and Mac installs   |

Review noon/midnight and equivalent signs first.
Also check date/range hyphens and durations versus clock times.
Include protected Markdown text.
The grep role's scope map must be incorporated before tests are finalized.

## Task 1: Freeze Expectations and Establish Red

- [x] Complete the call-site and guidance scope map with the grep role.
- [x] Record planning reviews in both modes and resolve specification findings.
- [x] Freeze a case table and source hash before running the candidate. Include changed and equivalent pairs, with expected missing/added counts.
- [x] Include changed pairs: `午後3時` to `午前3時`, `▲3.2%` to `3.2%`, and `△120円` to `120円`.
- [x] Include equivalent pairs: `午後3時` to `15時`, `午前3時` to `3時`, and `△120円` to `-120円`.
- [x] Include noon/midnight and full-width digits. Test minutes/seconds and invalid qualified hours.
- [x] Include dates and ranges. Test lists and durations. Check protected code and URLs.
- [x] Add focused unittest assertions using the existing `run`, `numbers`, and analyzer helpers. Assert both detection and absence of false alarms; retain source text and line assertions.
- [x] Run the new tests against unchanged runtime and retain intended assertion failures. Separate tests already passing from actual Red evidence.
- [x] Obtain both test-review modes before implementation. Do not weaken approved expectations.

## Task 2: Implement and Verify the Smallest Candidate

- [x] Make the minimum shared extraction/canonicalization change. Retain `number_key(text: str) -> str` and existing output structures.
- [x] Run focused comparison and matching tests. Check CLI and consumers. Verify Red turns Green.
- [x] Run the frozen old/new evaluation. Detect every scoped meaning-changing case.
- [x] Require zero new false alarms in equivalent/control cases.
- [x] Run `python3 -m unittest discover -s tests`. Report optional-analyzer skips explicitly.
- [ ] Run both review modes for implementation and effect verification. Record findings and resolutions.
- [x] Record adoption or rejection with counts, evidence paths, and synthetic-evaluation limitations.

## Task 3: Review, Delivery, and Cleanup

- [x] Update guidance and results after the adoption decision. Reuse the existing skill structure.
- [x] Record which surveyed skill patterns were retained and why.
- [ ] Format Markdown with Prettier. Run markdownlint-cli2, then textlint with the existing preset.
- [ ] Inspect fixes and run raw `git diff --check`.
- [ ] Have audit verify the integrated snapshot in isolation. Include only explicit untracked inputs.
- [ ] Remove audit-owned temporary artifacts after verification.
- [ ] Request advisor on the final integrated diff with no tools. Resolve material findings and recheck changed behavior.
- [ ] Prepare the PR with validation and limits. Check authorization before publication or merge.
- [ ] If raising a version, update applicable Mac installs with the supported updater.
- [ ] Retain replaced-copy backups. Verify installed content against the checked source.
- [ ] Before closing Issue #219, recheck every acceptance condition and applicable delivery step. Leave unverified items unchecked.
- [ ] After an authorized merge, verify delivery. Remove merged task branches locally and remotely.
- [ ] Remove owned worktrees. Report retained artifacts and their reasons.

## Work Log

### 2026-11-29: Investigation and Approval Draft

- Grep completed with the configured model.
- Call path: `parse_document` to `collect_line_items` at line 337.
- Extraction: `NUMBER_RE` at line 311; `number_key` at line 313.
- These line numbers refer to the unmodified runtime.
- Indirect tests include `tests/test_compare_rewrite.py` and `tests/test_tokenizer_modes.py`.
  Also check `tests/test_kokugo_modes.py` and `tests/test_review_readability.py`.
  Guidance: `references/readability-rules.md` and `references/scripts.md` under the skill directory.
  Also inspect `SKILL.md`. No direct named-symbol tests were found.
- Equivalent `午後3時` and `15時` currently produce a numeric difference.
  Equivalent `△120円` and `-120円` already produce none. Preserve that absence of false alarms.
- Issue #219 is open, with no comments or assigned people at inspection time.
- Repository review policy is `both`; user directed the agent to follow global role assignments.
- Read the global roles and checked deterministic `symbol_lookup` routing.
  It selects read-only `grep`, using `gpt-6.1-terra` with low effort.
- Started a fresh read-only grep worker with that model for references and affected guidance. Runtime and tests remain unmodified by this task.
- Reproduced both reported misses: `午後3時` to `午前3時` and `▲3.2%` to `3.2%`.
  Both returned empty numeric missing/added lists.
- An exploratory formatter failed when serializing nonempty Item objects. This is an observation-script error, not a comparison failure or test result.
- Applied `writing-plans`, `ponytail`, and `karpathy-guidelines`. Reuse the existing Python comparison and test architecture; add no implementation framework.
