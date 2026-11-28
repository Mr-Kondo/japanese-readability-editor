---
status: superseded
date: 2026-11-02
decision-makers: repository owner
---

# Pilot a Small Set of Indexes for Skill-Improvement Knowledge

2026-11-02: The pilot was completed, and its adoption decision was recorded in the [successor ADR](conclude-pilot-adr.md). The following is preserved as the original pilot plan.

## Context and Decision

[Issue #140](https://github.com/Mr-Kondo/japanese-readability-editor/issues/140). The user approved a staged proposal based on the evaluation report. The first stage was to create a design record and 3–5 knowledge indexes. The results would then inform whether to connect them to the proposal feature.

The existing [improvement workflow](../../../../docs/feedback.md#受け取って改良につなぐメンテナー向け) covers intake, review, aggregation, proposals, and before/after comparison. The repository also has [evaluation cases](../../../../evals/README.md) and [upstream adoption records](../../../../docs/upstream-watch.md). This pilot adds an entry point to causes, counterexamples, and reasons for not adopting proposals across revisions. Whether it measurably reduces search effort has not been measured.

WikiSkill's separation of execution records, knowledge, and executable skills serves as a reference. The paper's benchmark results are not evidence that WikiSkill is effective for Japanese proofreading or that these indexes are effective. This design indexes existing materials and introduces no new execution infrastructure or external packages.

## Decision and Scope

- Put indexes, four pages based on published evidence, the pilot plan, results, and review in `feedback/wikiskill-pilot/`, which is excluded from Git. Publish only this ADR and an entry point in the README. These indexes are unevaluated prototypes and must not be loaded at runtime.
- Each page records an ID, search terms, observations, causal hypotheses, applicability conditions, candidate actions, counterexamples, evidence paths and the source record's target version/model, adoption status and rationale, and unverified items. Distinguish confirmation by an implementer or model from independent confirmation by a person.
- Link to existing evaluations and upstream reviews instead of copying their evidence. Preserve reasons for non-adoption, but do not promote unverified hypotheses into rules.
- Do not change `skills/`, `tools/feedback_loop.py`, the installer, version, dependencies, or environment settings. Do not add knowledge to ordinary proofreading or distributed artifacts.
- Connecting to `propose` is out of scope. Defer until usefulness can be compared with maintenance cost.

## Hypotheses, Evaluation, and Exit Conditions

| Hypothesis                                                | What this pilot will check                                                                                                                   | What this pilot cannot establish                                                     |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| H1: An index can lead to evidence for a revision decision | For all four fixed questions, the relevant page and the evidence location in the primary record agree                                        | Whether it is faster than searching without an index or yields more useful proposals |
| H2: Adding knowledge can avoid false generalization       | All four pages include counterexamples, hypotheses, evaluation limits, and adoption rationale, and a review checks them against the evidence | A guarantee that future updates will not accumulate incorrect knowledge              |

The limits for this pilot are four pages (no more than 80 lines each) and an index of no more than 60 lines; 120 minutes of active work for creation and structural checks; and one external static review (maximum 240 seconds). Do not run a comparative evaluation of model-generated proofreading. Use an existing CLI allowance for the review; add no new billing settings, dependencies, or persistent processes. If the actual cost cannot be obtained, record it as unmeasured.

If links are inconsistent, claims exceed the evidence, or protected or unused final-evaluation data is included, put the work on HOLD and correct it. When the active-work limit is reached, stop adding pages or features and record remaining work in the Issue. Do not expand the pilot if serious review findings continue.

If connection is reconsidered, freeze a separate comparison plan. With the same revision task, skill version, and model, measure evidence-search time with and without indexes, useful proposals, repeated proposals of the same previously rejected idea, and maintenance time and token cost. Do not include unused final-evaluation documents in proposal input, and do not offset regressions in meaning preservation, unresolved results, or missing data with average scores. Reduce or remove the indexes if maintenance cost exceeds benefit. Do not treat this static check as a substitute for that comparative experiment.

## Nonfunctional Requirements

- **Information protection:** Use only evaluation results and adoption records for published artificial examples. Do not collect users' source text, messages, or confidential information. Git exclusion is not a substitute for confidentiality; follow existing out-of-worktree storage rules for non-public input.
- **Evaluation data:** Index evaluated, published records. Treat documents already used as regression data, and do not reuse them for future generalization evaluation. Do not read unused final-evaluation documents.
- **Dependencies and licensing:** Add no dependency. Refer to the paper's methods without reproducing external implementations or text.
- **Compatibility:** Keep development materials in ordinary Markdown readable by Claude Code, Codex, and Antigravity. Do not report that loading or auto-start behavior was verified in any host. Since the skill itself is unchanged, no version bump or Mac redeployment is needed.
- **Accessibility:** Make information reachable through text links and headings; do not encode status only through color or diagrams.

## Implementation and Verification

Scope: this ADR, the README, and `feedback/wikiskill-pilot/`. Follow the separation between the existing japanese-readability-editor runtime and reference materials, and the distinction between evidence and unverified items in official-prompt-tailor. Do not change skill frontmatter or triggers, and add no wrapper or installation mechanism.

1. Review existing records and create pages for these four topics: sentence function, unresolved completion status, invented guarantees during concretization, and overlap between upstream and existing functionality.
2. Check the index against the four fixed questions, evidence, relative links, line counts, and Git exclusion. Keep the plan and results distinct.
3. Request a static review from Antigravity with the plan, ADR, index, pages, and evidence attached. Record adopted and not-adopted feedback and the reasons in the results.
4. Create a documentation-only PR, check existing CI and review, and merge it. Do not create a release because the version is unchanged. After confirming the merge, delete the merged working branch locally and remotely, while preserving existing uncommitted changes.

### Checks

- [x] The four pages and index exist, and their relative links resolve.
- [x] Each of the four fixed questions leads to evidence; hypotheses are not conflated with observations or adoption status.
- [x] The prototype is excluded from Git; the only published changes for this work are this ADR and the README.
- [x] The other agent's review, response to it, and its limits are recorded in the results.
- [x] The results state why connection is deferred and explicitly say that effectiveness is unmeasured.
- [x] The Issue acceptance conditions include checking the PR, CI, merge, and branch deletion.

## Alternatives and Consequences

- **Use existing materials only:** Lowest maintenance cost. Return to this approach if indexes are not useful. This pilot tests a small number of entry points to decide whether additional functionality is needed.
- **Connect to `propose` immediately:** Would allow direct comparison of effects, but increases implementation cost for evaluation, reference selection, and information protection. Defer because the evidence-search problem has not been measured.
- **Adopt the full external WikiSkill implementation:** Could make an automated loop available, but it would overlap with existing workflow and add environment dependencies and maintenance. Do not adopt.

Maintaining indexes and rechecking their evidence takes time away from evaluating real documents. This pilot does not promote them to an official public knowledge layer. If sharing becomes necessary, develop reproducible procedures and publishable content under a separate decision.

## References and History

- [WikiSkill original paper, v1](https://arxiv.org/html/2608.27454v1)
- [Specified article](https://zenn.dev/suwash/articles/wikiskill_20261015)
- The location of the local prototype and verification results is recorded in the completion record for Issue #140. Do not imply that the local prototype can be opened from GitHub.

2026-11-02: Structural checks of the four questions and a static review by Antigravity `gemini-4-argon-medium` were completed. There were no findings with material impact, so no additional fixes were adopted or rejected. Comparative evaluations of time savings, proposal quality, and quality improvement were not performed; therefore, connection remains deferred. Do not treat blind testing with the prototype or host runtime checks as completed.
