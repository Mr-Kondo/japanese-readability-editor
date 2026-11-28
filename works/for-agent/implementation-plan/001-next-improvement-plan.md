# Next Improvement Plan for the Text Evaluation Tool

Implementation connection: Issues [#32](https://github.com/Mr-Kondo/japanese-readability-editor/issues/32) through [#36](https://github.com/Mr-Kondo/japanese-readability-editor/issues/36) were filed based on this report. The [evaluation-tool guide](../../../docs/human-evaluation.md) documents aggregation of disagreement, severity, and missingness; review records and regression outputs; human/LLM comparison; comprehension questions for a single candidate; and document-level approximate intervals. The following is a proposal from the research point in time; implementing the tool and demonstrating quality improvement are separate claims.

## 1. Context: Connecting Evaluation Results to Skill Improvement

Research date: October 16, 2026. Target: the current implementation, approximately v0.10.0. This work was research and a design proposal; no implementation or experiment was performed. Assume a small group using local HTML and Python on this Mac. Initially focus on Mode B (meaning-preserving editing).

**Next, prioritize aggregation that reveals disagreements and a procedure for turning confirmed feedback into regression cases. Add effect evaluation through comprehension questions afterward.** Merely increasing automatic-rating counts or metrics does not determine how to revise the skill.

“Adjudication” means a person checks a disputed evaluation against the source and supporting materials. A “regression case” is an example used to check that a fixed defect does not recur. “Held-out data” means documents retained until final evaluation rather than used to revise rules or rating methods.

## 2. Core Reasoning

### Evidence: Current Capabilities and Gaps

I inspected the current [user guide](../../../docs/human-evaluation.md), [anonymous comparison](../../../tools/compare_readability.py), and [automatic single-output review](../../../tools/review_readability.py) implementations.

| Current fact                                                                                                                                   | Implication for the next decision                                                                                            |
| ---------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| Anonymous two-candidate comparison, evaluator-specific left/right assignment, and quotes, categories, severity, and rationale can be recorded. | There is no need to build a new evaluation input system from scratch.                                                        |
| Every evaluator receives every item; missingness and preference among cases where both candidates pass are aggregated.                         | Do not interpret every vote as an independent sample when estimating a win rate. The scope of source documents also matters. |
| Meaning-preservation failure rate uses all assigned items as its denominator.                                                                  | More missing responses can make the apparent rate lower. Also report the rate among answered items.                          |
| Feedback retains issue severity, but candidate-level aggregation mainly counts feedback by category.                                           | There is room to add document counts with at least one severe issue and a disagreement list.                                 |
| Automatic evaluation is a standalone check for each candidate, unlike human preference between two candidates.                                 | First compare the meaning-preservation judgments directly. Do not compare them as if they were the same “win rate.”          |
| Comprehension questions, adjudication, inter-rater agreement, confidence intervals, and automatic skill updates are not implemented.           | Set additional goals and implement them in necessary order.                                                                  |

The following points were found in the literature:

- There are frameworks for evaluating information loss through simplification using comprehension questions. They cannot guarantee content that the questions do not cover. [Agrawal & Carpuat, 2024](https://aclanthology.org/2024.tacl-1.24/)
- Perceived readability and actual comprehension can differ, and the difference can vary by reader group. [Carrer et al., 2024](https://aclanthology.org/2024.humeval-1.7/)
- Research has compared human and LLM evaluation of Japanese document-level simplification. It also reports rating biases related to kanji density and sentence length. The findings cannot be directly generalized to meaning preservation in technical documents. [Yamashita et al., 2026](https://aclanthology.org/2026.lrec-1.85/)
- LLM judgments have limits in agreement with human judgments; simple agreement rates alone can mislead. [Thakur et al., 2025](https://aclanthology.org/2025.gem-1.33/)
- Agreement coefficients must be selected to fit the rating scale and assumptions. [Artstein & Poesio, 2008](https://aclanthology.org/J08-4004/)
- A small number of human evaluations may lack power to detect small quality differences. Do not choose the number of documents and evaluators solely by fixed convention. [Card et al., 2020](https://aclanthology.org/2020.emnlp-main.745/)

### Hypothesis: First Make It Clear What Cannot Be Trusted

Reviewing disagreements among evaluators or between human and LLM judgments may help distinguish ambiguous criteria, missing supporting information, and errors missed by the rating model. Reflect confirmed recurring failures in skill rules or examples, then reevaluate on unused documents. This causal path is a design hypothesis; its effects have not yet been demonstrated.

### Counterargument: Are Adjudication and Statistics Too Heavy for a Small-Group Tool?

This is a reasonable concern. There is no need to start with a web app for adjudication, complex agreement coefficients, or a database. A minimal implementation can produce a disagreement list from existing JSON and let a person record conclusions and evidence in a separate file. For a solo user, do not calculate inter-rater agreement; treat changes across repeat evaluations and differences from automatic judgments as reference information. Repeated ratings by one person are not evidence from multiple independent people.

## 3. Key Points: Priority, Cost, and Expected Effects

Effort is a relative assessment, not a work estimate or measured improvement rate.

| Priority | Improvement                                                         | Minimum change scope                                                                            | Effort       | Expected effect and opportunity cost                                                                    |
| -------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------- |
| P0       | Aggregation that shows disagreement, severity, and missingness      | Anonymous-comparison aggregation, Markdown output, corresponding tests, guide                   | Small        | Makes risky cases easier to find. Does not measure comprehension itself.                                |
| P0       | Turn confirmed feedback into regression cases                       | Manual-review record format, conversion/validation for existing evals, examples, guide          | Small–medium | Connects the reason for a fix to regression checking. Requires human time for review and anonymization. |
| P1       | Compare human and LLM meaning-preservation judgments                | Input-correspondence validation, comparison aggregation, tests, guide                           | Medium       | Reveals errors that automation cannot be trusted to handle. Needs calibrated human data.                |
| P1       | Run comprehension questions on a separate screen                    | Question, answer, and evidence format; single-candidate assignment; response UI; scoring; tests | Medium–large | Directly checks comprehension. Question authoring and reader recruitment are bottlenecks.               |
| P2       | Document-level differences and confidence intervals                 | Define estimand, document-level aggregation, statistical processing, tests                      | Medium       | Shows uncertainty around differences. Does not resolve information scarcity in small samples.           |
| Hold     | Server for many people, partial assignment, full automatic revision | Authentication, storage, distribution, and operations                                           | Large        | Current evaluator count and response volume do not justify the cost.                                    |

### P0-A: Aggregation That Reveals Disagreement and Serious Misses

Keep the existing response format and add the following:

1. List documents and generated candidates where evaluators disagree on meaning preservation. Show `pass/fail/uncertain` counts with quotes and rationale. Compare repeated generations of the same source document as separate candidates and combine them in document-level aggregation.
2. For each candidate version, report issue counts by severity and the number of documents with at least one severe issue. Do not assert that multiple evaluators reporting the same defect are separate defects. Unadjudicated feedback is an “issue,” not a confirmed error.
3. Report the number of failing responses over all assignments, the failure rate among answered items, undecided count, and missing count. The answered-only rate can also be biased by who responded. Do not treat missingness as a pass.
4. Retain preference among comparisons where both candidates pass, and state the share of documents and votes included. Good preference must not offset worse meaning preservation.

Agreement coefficients need not be required in the first version. Inspect the actual disagreements first. If coefficients are added, treat meaning preservation as nominal and 1–5 ratings as ordinal; if a coefficient is undefined, do not calculate it and state why. `uncertain` is a valid judgment, distinct from missing data. High agreement does not prove correctness.

### P0-B: Put Feedback Back into Regression Cases

Do not overwrite original responses. Keep a separate review record containing input hash, candidate ID, quote, reviewer, evidence, and conclusion. Use conclusions “confirmed issue / no issue / unresolved”; do not decide solely by majority vote.

Create cases from confirmed issues containing the source, failed candidate, relationship to preserve, failure type, and relevant skill rule. Do not make the proposed fix the sole correct text. Reuse a suitable format such as the existing [unsupported concretization case](../../../evals/concretization-cases.json). If the existing format is a poor fit, retain a manually managed case first.

Change only skill rules or examples relevant to recurring failures. Distinguish mechanically verifiable conditions such as numbers and line breaks from semantic relationships that require human or model review. Converting cases to JSON does not automate semantic verification. Also retain counterexamples: natural text that should not be changed. Keep cases used for tuning separate from held-out documents used to measure effects.

### P1-A: Calibrate Automatic Ratings Against Human Judgments

First compare meaning-preservation labels `pass/fail/uncertain` for the same candidate. Use the anonymous-comparison organizer mapping table and automatic-evaluation original IDs, version labels, and text to verify that source, candidate, request, context, and target reader match. Do not join different texts merely because IDs match.

Compare against adjudicated human judgments and report a confusion matrix, detection rate for meaning changes, confirmed failures among items the LLM passed, and abstention rate. Retain unresolved reference judgments and LLM undecided cases; state the denominator and scope of detection rates. Artificial failure examples can test detection capability, but do not directly estimate real-world error frequency or precision.

Use the current three-axis ratings as supporting information to examine differences in distributions. Do not directly compare human preference between two candidates with the LLM’s preference relative to the source. First inspect using one rating model and fixed instructions; add models only after measuring misses. If LLM pairwise comparison is added later, rescore with left/right sides reversed and leave inconsistent cases unresolved. [Position-bias study](https://aclanthology.org/2025.ijcnlp-long.18/)

### P1-B: Separate Comprehension Questions from the Current Comparison Screen

The current screen shows the source and both candidates, so adding comprehension questions there would let readers answer from the other version. In a comprehension experiment, each reader should see only one version of each source. Assign old and new versions across multiple documents and account for order and reader-group differences. Separate the role of people who assess fidelity to the source from that of actual target readers.

Write questions from the source and test important information such as quantities, conditions, exceptions, and agents. The organizer must verify answers and evidence; do not embed them in the pre-answer HTML because answers hidden in local HTML are not secret. Allow “I don’t know.”

The first version can use human-verified multiple-choice questions and an optional “passage that was confusing” response. Use correctness rate as a primary metric and retain document-level scores. If readers can refer to the text, define it as a task of “finding necessary information” and distinguish it from a memory experiment. Time is strongly affected by interruptions, so defer it; if collected, do not judge quality by speed alone.

### P2: Define the Estimand Before Adding Statistics

If the target gives documents equal weight, aggregate repeated generations and evaluator results within each document before estimating the old/new difference. When resampling documents, draw both versions of the same document together. Do not resample votes as independent samples. Generalizing to an evaluator population requires handling evaluator variation as well; distinguish this from a document-only interval.

Retain preference among cases where both candidates pass as a conditional result. Report overall effects separately, such as meaning preservation and comprehension outcomes. If intervals are wide, leave the result unresolved; failure to detect a difference does not prove equivalence. First measure variation and completion time in a short pilot, then plan document count. Do not guarantee adequacy with a fixed rule such as “30 items is enough.”

## 4. Concrete Example: An Edit That Drops an Approval Condition

Artificial example: changing 「管理者の承認後、30分以内に実行できます。」 to 「3分以内に実行できます。」.

- Automatic checks flag the number difference and other candidates for review. They do not determine meaning preservation.
- Human evaluators quote and explain “approval condition omitted” and “30 changed to 3.” If evaluators disagree on preservation, show the item in the disagreement list.
- A reviewer compares the source and records both issues. A high naturalness rating does not turn it into a pass.
- A regression case retains the requirements to preserve the approval condition and 30 minutes. Distinguish a failure actually generated by the skill from an artificial example for tool inspection.
- Comprehension questions ask “Can it be run before approval?” and “Within how many minutes?” Record responses from target readers who saw only the candidate.

Detecting this example does not prove the tool catches unknown changes to conditions, negation, or agents.

## 5. Plain-Language Explanation

In plain terms, before adding more scores, build a process to check disputed passages, turn confirmed failures into examples that prevent recurrence, and test reader comprehension on different text.

## 6. Self-Critical Assessment: Effect Projections and Limits

| Improvement                              | Direction predicted                                                  | What remains unknown                                                                                            |
| ---------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Disagreement/severity list               | Makes passages requiring review clearer                              | How much review time will decrease. Many disagreements alone do not establish poor evaluator quality.           |
| Regression cases from confirmed feedback | Makes known failures easier to check again                           | Whether the error rate on unseen documents decreases. Additional rules might also cause over-editing.           |
| Human/LLM calibration                    | Clarifies automatic-rating misses and limits                         | How much human review can be removed. Performance in new domains and after model updates needs separate checks. |
| Comprehension questions                  | Measures comprehension differences not visible in impression ratings | Whether a revised version will always be better. Question bias and reader knowledge matter.                     |

**There is insufficient evidence for a numerical prediction of improvement.** Becoming measurable and actually improving quality are separate. Confidence in the priority judgment in this proposal is 0.8. This is neither a measured probability nor the probability that quality will improve. Implementation gaps were confirmed, but the number of users, actual responses, and operating time have not been measured.

Research focused mainly on primary-source pages, abstracts, and official API documentation. No paper's experiments were reproduced. No human study of this skill on Japanese technical or business documents was conducted in this work.

## 7. Conclusion: Keep the Next Implementation Small

For the next implementation, recommend the two P0 items: “aggregate disagreement, severity, and missingness” and “turn confirmed feedback into regression cases.” Reuse the existing evaluation screen and storage format; limit changes to aggregation, review records, tests, and the guide. Add no model, dependency library, or server.

Use examples from that pilot to calibrate LLM ratings and design comprehension questions for target readers. Treat skill rules as limited changes for recurring failures that have been confirmed. Do not adopt automatic feedback insertion yet; it could encode errors or individual preferences into the rules.

## 8. References, Libraries, and Skills

Links above were checked on October 16, 2026. This does not mean the items were installed or run.

- [Agrawal & Carpuat, 2024](https://aclanthology.org/2024.tacl-1.24/): meaning-preservation evaluation with comprehension questions.
- [Carrer et al., 2024](https://aclanthology.org/2024.humeval-1.7/): evaluation including reader perception and comprehension.
- [Yamashita et al., 2026](https://aclanthology.org/2026.lrec-1.85/): human and LLM evaluation of Japanese documents.
- [Thakur et al., 2025](https://aclanthology.org/2025.gem-1.33/): limits of agreement between LLM and human judgments.
- [Shi et al., 2025](https://aclanthology.org/2025.ijcnlp-long.18/): position bias in LLM judgments.
- [Artstein & Poesio, 2008](https://aclanthology.org/J08-4004/): scales and assumptions for inter-rater agreement.
- [Card et al., 2020](https://aclanthology.org/2020.emnlp-main.745/): power and evaluation design.
- [NLTK agreement API](https://www.nltk.org/api/nltk.metrics.agreement.html): a candidate for a later agreement-coefficient feature. A disagreement list is enough initially, so do not add this dependency now.
- [SciPy bootstrap API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html): a candidate for adding statistical analysis as a separate step. Supports paired resampling but does not automatically resolve document/evaluator dependency structure.
- [Label Studio export](https://labelstud.io/guide/export.html): a candidate if collection by many evaluators becomes necessary. Conversion to current JSON and retention of pseudonymous IDs, version mapping, and hashes require separate design. Continue local HTML for now.
- Use the existing japanese-readability-editor skill for style review and docs-guard for consistency with implementation. Neither measures reader comprehension nor replaces human judgment.
