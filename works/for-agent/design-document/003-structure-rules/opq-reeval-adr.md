---
status: accepted
date: 2026-11-11
decision-makers: User (after the previous decision not to adopt, chose to preregister the meaning-retention criterion again and reevaluate), Claude Code (design and verification). Decision: not adopted (criterion 6 unmet)
---

# Reevaluate the OPQ rule (experiment 3): compare with new cases using a criterion that permits reordering

Tracking: [Issue #162](https://github.com/Mr-Kondo/japanese-readability-editor/issues/162). Previous ADR: [2026-11-11-opq-analysis](opq-analysis-adr.md) (experiments 1 and 2; decision was not to adopt; this ADR carries out the user's request left open there to reevaluate under a criterion that permits reordering).

## Provenance note

The historical `adr_sha256` values in `run.json` already differ from the pinned pre-translation Japanese originals. `check_frozen()` verifies runner and helper files, not ADR bodies. The preserved Japanese originals are not claimed to be experiment-time snapshots. See [pre-translation OPQ provenance](../index.md#pre-translation-opq-provenance).

## Context

In the prior two experiments, the effect of “put conclusions and requests at the beginning” was observed, but the pre-registered meaning-retention criterion was not met. The failures were: (a) in two cases, evaluators treated the reordering itself to move requests to the beginning as a structural change; (b) in two cases, evaluations or check plans absent from the original were added. (a) arose because the scoring instructions did not specify the permissible range of meaning-preserving reordering. (b) arose because rule wording alone did not suppress the additions. In addition, the new cases in experiment 2 already met the opening test in the original, so they were not discriminating.

User decision (2026-11-11): preregister the meaning-retention criterion again and reevaluate.

## Changes (decided before seeing results)

1. **Scoring instructions**: Clarify how order is treated. If the request does not require preserving order or structure (Mode B with no such instruction; Mode A), moving a conclusion or request to the beginning does not itself count as a change. Mark as fail if reordering changes what conditions, exceptions, reasons, or scope (“どちらも,” “回答がない場合は,” etc.) apply to; makes the basis for the conclusion unreadable; or adds evaluations, interpretations, the character of a request, check plans, or introductory statements absent from the original or source material. If the request requires preserving order or structure, check that order is preserved. Wording is `ORDER_RULE` in `evals/opq3-run/runner.py`. Apply the same instructions to both old and candidate versions.
2. **Evaluator calibration**: Add five new controls to the existing 12: reordering only = pass; move while preserving conditions = pass; changed scope of a condition = fail; added evaluation = fail; added introductory text = fail. Require all 17 controls to meet expectations.
3. **Candidate 3**: Add to candidate 2 (a) one line instructing the model to move deadlines and conditions attached to a request along with it, and check that scope terms still apply to the right material; and (b) example 34 in `assets/examples.md` (move a request to the beginning, what not to add, and when not to move it). `SKILL.md` remains as in candidates 1 and 2 (only wording on two lines changes; it stays at 175 lines). Example 34's subject (a conference room projector) does not overlap with evaluation cases.
4. **Cases**: [13 new cases](../../../../evals/opq3-cases.json) (four buried B cases p01–p04, four A cases from source material q01–q04, three unchanged controls c1–c3, Paragraph-only c4, fixed-order c5). None were run against either version. **During preparation, check that buried B and A originals do not meet the opening test (that they are discriminating); stop preparation if they do.** Also check that originals for unchanged controls pass their own checks. The author is the same as in the previous experiments and created these after learning the failure types.
5. **Stronger order check**: For unchanged controls c2 and c5, verify order preservation by checking that the occurrence positions of terms increase in the specified order (`order_terms`).
6. **Pairwise judgment**: Same as the previous evaluation. Parse only the first JSON object.

The old version is `f062b66` (main; skill remains v0.22.0; verify during preparation that its hash matches the old version from the prior experiment). Generate both versions anew (no reuse). `sonnet / medium`, no tools, new context.

## Hypotheses

H1: Candidate 3 places conclusions and requests at the beginning more often than the old version (replicating experiments 1 and 2).
H2: Under the criterion that permits reordering, candidate 3 does not worsen meaning retention compared with the old version.
H3: It preserves unchanged controls and constraints.
H4: Additions of evaluations, introductory statements, request characteristics, and check plans absent from the original or source material do not increase compared with the old version.

## Success criteria

Adopt only if all of the following hold.

1. Retention: Candidate 3 has no more fails than the old version, and no more fails+uncertain combined (39 outputs each). All 17 calibration controls meet expectations. Actual model identifiers match.
2. Opening placement: Among 24 outputs from the 8 primary cases, the count where all conclusion/request terms appear within the first 220 characters is at least six higher for candidate 3 than the old version.
3. Pairwise `answer_first` (count only pairs where both reversed judgments agree): Candidate 3 wins more often than the old version.
4. Pairwise `no_additions`: Candidate 3 wins at least as often as the old version.
5. Unchanged controls (nine outputs for c1–c3): At most one output has a violated opening requirement or order, and the count is no higher than the old version.
6. Constraints (six outputs for c4 and c5): Zero violations.

## Rollback criteria

- If the old version places conclusions near the beginning in 20 or more of the 24 primary outputs (ceiling), do not add the rule; do not adopt it.
- If any criterion is unmet, do not add the rule; do not adopt it. **Do not rerun (experiment 3 is the last).** Treat missing pairwise judgments as failure to meet criteria 3 and 4; do not adopt.
- If adopting it, use the exact candidate 3 wording for the two lines in `SKILL.md`, the subsection in `readability-rules.md` and §13, and example 34 (do not adjust the wording). Keep `SKILL.md` at 175 lines. Increment VERSION and write release notes.

## Case revisions before generation (record)

Of the initial 13 cases, p04, q03, and q04 already met the opening test (first 220 characters) during preparation; for example, “30分” was at character 59 and “来月” at character 211 in p04. Before running either version, added background details to those three so the conclusion/request terms appeared after character 220. Also added background to q01 and q02 because they were near the boundary. After revision, in all eight cases, at least one conclusion/request term occurs after character 220 (confirmed by preparation checks and runner self-checks). The conclusion/request content, numbers, and conditions did not change. Revisions were made before examining model outputs.

## Limitations (stated in advance)

- The 13 self-authored cases do not show generalization to unused documents. The same author created them after learning the failure types. They are biased toward documents with conclusions at the end and explicit readers and decisions (conditions favorable to OPQ). Behavior when the reader is unknown was not measured.
- The scoring criterion changed after seeing experiments 1 and 2. This change is based on the types of their two failures. The same criterion is applied to old and candidate versions, making the comparison fair, but the interpretation remains that “a candidate that failed under the previous criterion passed after changing the criterion.” If adopted, state this history explicitly.
- Opening placement is a deterministic proxy and does not measure human reader comprehension. Evaluation uses the same model family, has no human scoring, and the three repeated runs are not independent.
- Order is checked by comparing `order_terms` positions only for c2 and c5. For other controls and A cases, only opening requirements are checked.
- Added evaluations, introductory statements, and check plans recurred in old and candidate versions in experiments 1 and 2. This is the first experiment to check whether the rule and example 34 suppress them.

## Results

Executed as preregistered (no rerun; runner, cases, and scoring instructions were not changed after preparation. The `amendments` record of in-run changes is absent from `run.json`. `adr_sha256` is the ADR hash before writing the results). Actual model identifier was `claude-sonnet-5-5` for all calls. Old version was `f062b66` (hash match with prior experiment's old version confirmed during preparation).

| Criterion                                                    | Old version     | Candidate 3                    | Pre-registered threshold                                                 | Assessment           |
| ------------------------------------------------------------ | --------------- | ------------------------------ | ------------------------------------------------------------------------ | -------------------- |
| 1 Meaning retention (39 outputs each)                        | pass 36, fail 3 | pass 36, fail 3                | Candidate fails no higher; all 17 calibration controls meet expectations | Met (controls 17/17) |
| 2 Opening placement (eight primary cases, 24 outputs)        | 11              | 20 (buried B: 2→11, A: 9→9)    | Difference of at least 6                                                 | Met (difference 9)   |
| 3 `answer_first` (27 pairs with matching reversed judgments) | 0 wins          | 11 wins (12 ties, 4 uncertain) | Candidate wins more than old                                             | Met                  |
| 4 `no_additions`                                             | 0 wins          | 3 wins (19 ties, 5 uncertain)  | Candidate wins at least as often as old                                  | Met                  |
| 5 Unchanged controls (c1–c3, 9 outputs)                      | 0 changes       | 0 changes                      | At most 1 and no more than old                                           | Met                  |
| 6 Constraints (c4–c5, 6 outputs)                             | 1 violation     | 1 violation                    | 0 violations                                                             | **Not met**          |

**Decision: HOLD (not adopted).** Criterion 6 was unmet, so do not add the rule. Do not rerun (experiment 3 is the last).

Meaning-retention failures (generated outputs only): candidate 3 added the qualification “10月に見つかった” to p03; added causality in q03, making last year's participation the reason for the review; and added the evaluation “対応は追いついていません” to q02 (one each). The old version added numbers and effects and reinterpreted a deadline in q04, and added causality in q03 (two cases; one also omitted “人数の記録はない”). **The q03 causal addition appeared in both versions** (the source only lists background and a proposed review as separate items). Candidate 3 did not produce the introductory-text additions or reordering failures seen in experiments 1 and 2. The added evaluation in q02 recurred once after adding the rule and example 34.

The two criterion 6 violations (old version c5 run 1; candidate 3 c5 run 3) are **false positives in the check** (confirmed after the fact). Outputs preserved order, but `order_terms` contained “月額4万円,” while the output changed it to “月額が4万円,” so the literal string was not found and the check reported order violation. The found terms were in ascending order. Meaning-retention scoring marked this change pass (j003). The preregistered checker is sensitive to particle changes.

Post hoc interpretation: Excluding these two false positives would satisfy all criteria. However, this is a reinterpretation after seeing the results; under the preregistered criteria, the result is HOLD. Adopting the candidate after correcting the checker post hoc would conflict with the purpose of preregistration, so this ADR does not adopt it. The decision whether to adopt remains with the user (below).

Constraints and other observations:

- Opening placement for the old version was 11 of 24 (below the ceiling of 20). Candidate 3's increase came from buried B cases (2→11); there was no increase for A (9→9; q03 was 0/3 for both versions because the conclusion term was in the final source item and did not appear at the beginning).
- All 17 calibration controls met expectations. The judgment problem from experiments 1 and 2—treating reordering itself as a change—did not occur under these instructions (`ORDER_RULE`; e.g., c13). However, because the criterion changed, the interpretation remains that a candidate that failed previously passed after changing the criterion (as noted in limitations).
- Cost was about US$5.7 at API rates (about 4.85 for 78 generation calls, 0.49 for 7 scoring calls, and 0.32 for 14 pairwise-judgment calls; sum of `cost_usd` in each `run.json`).
- Candidate 3's diff is retained in [candidate3.diff](../../../../evals/opq3-run/candidate3.diff) (`SKILL.md`, `readability-rules.md`, `assets/examples.md`). The skill was not changed (remains v0.22.0).

## Decision

**Not adopted. Do not add the OPQ rule or example 34 to the skill.** Pre-registered criterion 6 (zero constraint violations) was unmet. The effect (opening placement, `answer_first`) and no worsening in meaning retention were observed this time.

The decision for this experiment is final as stated above (experiment 3 was the last; do not rerun).

User policy choices outside this experiment (they do not change this ADR's decision):

1. Adopt candidate 3 (`candidate3.diff`) as an exception by reinterpreting the pre-registered criterion after the fact because the two criterion 6 cases were false positives. If so, state the exception in the release notes.
2. Preregister a new experiment in a separate ADR with separate new cases and a check robust to particle changes (this would be a new experiment outside this ADR's “experiment 3 is the last”).
3. Do not adopt it; keep current practice of moving content toward the beginning only when explicitly asked to “put the conclusion first.”
