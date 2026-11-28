---
status: accepted
date: 2026-11-02
decision-makers: Codex (within the scope of staged evaluation and adoption decisions approved by the user)
supersedes: pilot-plan-adr.md
---

# Complete the Knowledge-Index Pilot; Do Not Adopt Automatic Connection

## Context

The small-index pilot described in the [original ADR](pilot-plan-adr.md) was evaluated across [Issue #144](https://github.com/Mr-Kondo/japanese-readability-editor/issues/144), [Issue #146](https://github.com/Mr-Kondo/japanese-readability-editor/issues/146), and [Issue #148](https://github.com/Mr-Kondo/japanese-readability-editor/issues/148). In response to the user's request to "see it through," complete the pilot rather than extend it while it is deferred, and decide what to adopt now.

The WikiSkill approach separates execution records, reusable knowledge, and executable skills. It is a candidate way to complement the existing workflow of review, aggregation, proposals, and before/after comparison. However, the usefulness of indexes and improvement in the quality of executable skills are separate claims.

## Observations and Interpretation

| Check                                                       | Observation                                                                                                                                                                                                             | Limit on interpretation                                                                                                                                                              |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Add indexes to full text (#144)                             | Two runs per condition. External scores were 12 and 14 points in both conditions (out of 16 each). Median elapsed time was 31.210 seconds without an index and 57.128 seconds with an index.                            | This did not evaluate the search method. Citations revealed the condition, and some scoring focused on wording rather than meaning.                                                  |
| Select up to two items from six materials and answer (#146) | Two known tasks. The specified direct evidence was cited in 1/4 answers without an index and 4/4 with an index. Meaning-relevant decisions and distinctions between past and present were satisfied in both conditions. | The score difference, 7/10 versus 10/10, came from three points for direct evidence citations. It does not show improved rewriting quality.                                          |
| Workload in the same pilot (#146)                           | Total elapsed time for selection and answers was 182.613 seconds versus 120.899 seconds. Total input length was 10,365 versus 11,912 characters.                                                                        | One task was about 3% slower with an index. Input length increased by about 15%. Each condition was run once, and cache amounts differed; these are not stable time or cost savings. |

Finally, without adding any further indexes, two tasks were added using the unrecorded D5 (follow-up question after an answer) and D6 (scoring greeting removal and citation retention). Each task was run under both conditions, with an index and without one. All four runs succeeded. Direct evidence was found in 2/2 runs without an index and 2/2 runs with an index. Total elapsed time for selection alone was 35.418 seconds versus 46.161 seconds; total input length was 1,217 versus 2,285 characters. No new misses were observed, but the catalog alone also led to the evidence, so this is not evidence of benefit from automatic connection.

This was an additional check of published materials, not an unused final evaluation or a generalization test. Although D5/D6 were not recorded, related concepts existed in the current indexes; they were not entirely independent areas. The task text made the needed information explicit and may have made the search easier than ordinary exploration. Details are in Issue #148. No additional scoring of answer generation or semantic quality was done.

Actual costs, ongoing index-maintenance time, adoption rate of real improvement proposals, and number of repeated proposals of the same rejected idea remain unmeasured. Do not use document volume or some token counts as substitute measurements. Overall, there is an observation that indexes helped locate evidence in known areas, but the relative benefit and maintenance cost of connection cannot be determined.

## Decision

1. **Complete this pilot and do not adopt automatic connection to `propose`.** Continuing the comparison is not mandatory unfinished work. This does not mean that WikiSkill as a whole is ineffective.
2. Keep the four local indexes as optional aids for a person or agent to reach source materials when needed. They are not comprehensive catalogs; absence of an item does not mean no relevant record exists. Introduce no maintenance obligation, automatic loading, persistent updates, or additional pages.
3. When using a finding, check the source's target version, conditions, counterexamples, and reasons for non-adoption, and distinguish them from evidence for the current version. Continue new revisions through the existing Issue, review, proposal, adoption decision, before/after evaluation, and distribution process. Adding a knowledge page alone does not change an execution rule.
4. Do not put confidential information, personal data, or unused final-evaluation inputs in indexes. Follow existing storage rules for non-public inputs. Do not treat Git exclusion of `feedback/` as a substitute for information protection.

## Options and Opportunity Cost

- **Automatic connection:** Could make evidence available on every run. It would also add selection of relevant references, update tracking, citation validation, exclusion of protected data, regression evaluation, and maintenance. Do not adopt because evidence of improved real proposals and their cost is insufficient.
- **Keep as a manual aid and complete the pilot (adopted):** The four existing items remain available without adding a new maintenance target to execution or distribution. Ordinary document search is still needed to avoid missing items outside the indexes, and the effect of manual use is unverified.
- **Remove all indexes:** Lowest maintenance, but loses an entry point to past decisions that have already been organized. Keep them as a small local prototype without mandatory maintenance; the cost of retaining it is limited, so do not delete it now.

Time spent on further index experiments or automation reduces time available for evaluating existing public documents and improving meaning preservation. Do not expand the experiment until a concrete need arises.

## Work Performed and Conditions for Reconsideration

- Published changes are this ADR, a successor reference in the old ADR, and the README explanation. Logs, plans, execution snapshots, and reviews are stored outside Git in `feedback/wikiskill-completion/`. The public decision can be understood from this ADR and the Issue summary alone.
- Do not change `tools/feedback_loop.py`, the skill itself, version, dependencies, installer, or settings. Since the version is not raised, no release artifact or Mac redeployment is needed. Do not count a version update from other work as delivery for this pilot.
- Markdown is in a format readable by all three environments, but do not claim that it was loaded in Claude Code, Codex, or Antigravity at runtime.
- Reconsider in a separate Issue only if repeated evidence-search burden is recorded in real revisions and cost and maintenance time can be compared. Freeze the indexes before selecting tasks, include both indexed and unindexed material, and score semantic judgment separately from citations. Do not convert unused final-evaluation inputs into knowledge. Set adoption thresholds, measurement units, cost limits, and exit conditions in advance; do not use the isolated values from this pilot as a baseline.

## Verification and Completion Conditions

- [x] Checked the results of the four fixed additional runs, whether any failed, and input hashes.
- [x] Obtained static review from another agent and recorded adoption decisions and reasons in local results.
- [x] Checked README and predecessor/successor ADR links, whitespace in the diff, `feedback` exclusion, and preservation of existing edits.
- [x] Included checking the documentation PR, CI, merge, and deletion of both branches in the completion conditions for Issue #148. Check the actual result in that Issue.

The static review by Antigravity `gemini-4-argon-medium` resulted in adopting the suggestion to include the aggregate results of the four additional runs in this ADR. A suggestion to avoid forgetting to update completed items was also adopted. This was not an independent human review or host execution test.

## Evidence Entry Points

- [Meaning-preservation revision evaluation (D1)](../../../../evals/readability-preservation-result.md)
- [Additional evaluation (D2)](../../../../evals/readability-generalization-result.md)
- [Concretization evaluation (D3)](../../../../evals/concretization-result.md)
- [Upstream adoption (D4)](../../../../docs/upstream/reviews/natural-japanese-v1.6.0.md)
- [Meaning confirmation (D5)](../../../../evals/meaning-confirmation-result.md)
- [Sentence function and greetings, etc. (D6)](../../../../evals/sentence-kind-residue-result.md)

Results from papers or introductory articles were not used as evidence of effects in this repository.
