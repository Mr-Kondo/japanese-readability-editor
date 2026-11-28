# Connect Human Evaluation to an Evidence-Preserving Improvement Cycle

For implementation steps after the survey, see the [text evaluation tool](../../../../docs/human-evaluation.md). In addition to single-candidate evaluation and automated checks, the implementation includes anonymous two-candidate comparison for Mode B, fixed assignments by evaluator, issue records with quotations, and aggregation that includes missing data. This is a record of the survey at that time; effectiveness has not yet been demonstrated through a human study.

## 1. Context: Limit the First Version to Human Comparison in Mode B

**The recommendation is to build a local evaluation interface for a small number of people, recording meaning preservation separately from readability.** The first version should target Mode B (editing existing text) and save problem locations, reasons, and optional revision suggestions. People can review the collected findings, revise the Skill, and reevaluate on unused documents. Introducing a tool alone does not establish that text quality improves.

The survey date was 2026-10-16. The target was repository commit `26ec2c1d04da69409702f49408311c80af79174b`. This was research and design review only; no implementation, deployment, or human study was conducted. Since evaluator count and usage environment were unspecified, the assumption is that the author or a few people would use it. "Readability" means ease of understanding for the target reader. "Meaning preservation" means not changing quantities, conditions, negation, agent, sentence function, and similar elements. "Blind" means evaluators are not told the candidate's skill version or model name.

## 2. Core Rationale: Use Meaning Preservation as an Entry Condition, and Measure Comprehension Separately

### Evidence: What Existing Evaluations and Prior Research Show

This Skill does not aim merely to shorten text; it aims to reduce cognitive load while preserving meaning, accuracy, and necessary information. The existing comparison procedure also requires hiding version names and comparing readability only when both versions pass the meaning-preservation check. [Canonical Skill](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:10), [comparison procedure](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-comparison.md:30)

The existing generalization evaluation used model scoring on 48 outputs from 16 documents × 3 repetitions: meaning preservation was 46 pass, 1 fail, and 1 uncertain, and the overall decision was HOLD. This was not an independent human check or a study of 48 documents. Of the 45 Mode B outputs, 13 were identical to the original after trimming leading and trailing whitespace. **The meaning-preservation pass rate cannot be treated as a readability improvement rate.** [Existing evaluation result](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization-result.md:18)

A study of Japanese document-level simplification evaluated 1,128 pairs from 188 source texts with five native speakers, distinguishing retention of required information and main content from sentence- and document-level simplicity. However, it focused on substantial simplification for sixth-grade readers, so its criteria cannot be transferred directly to this Skill's technical documents, emails, or creative writing. [Yamashita et al., 2026](https://aclanthology.org/2026.lrec-1.85/)

Comprehension questions can detect information removed such that a question can no longer be answered. They do not guarantee retention of information that the questions do not address. A human study in German also found a gap between subjective difficulty and actual comprehension, and no significant result showing that post-editing after automatic simplification was faster than manual editing. [Agrawal & Carpuat, 2024](https://aclanthology.org/2024.tacl-1.24.pdf), [Carrer et al., 2024](https://aclanthology.org/2024.humeval-1.7.pdf)

### Hypothesis: Two-Stage Evaluation Makes Problems Easier to Locate

The proposed primary evaluation compares each candidate with the source, request, and materials, then labels it "pass / fail / uncertain." Record meaning changes and mode violations as separate defects; do not offset them with a high naturalness score. Then compare anonymous left/right displays among passing candidates and record "left / right / tie / uncertain" with evidence. The tool should also support single-candidate checks. At first, do not require a diff display; make the full text readable.

**Report failures, uncertain judgments, and missing data using all cases as the denominator, separately from preferences among pairs where both candidates pass.** If failed cases are removed and only the win rate among remaining candidates is shown, overall improvement will be overstated. Keep the original as a comparison baseline to detect cases where "it would have been better not to change it." Initially measure the effect of the Skill by comparing the same model and request with and without the Skill; measure revision effects by comparing old and new versions under the same generation conditions. Do not conflate these questions.

When checking comprehension by target readers, do not have the same person read both the original and revision of the same content in sequence. Assign readers and ask comprehension questions using only one version. Separating editorial review from a reader-comprehension study avoids mistaking memory of already-read content for improved comprehension. Recording evaluator characteristics, display order, independent ratings, and disagreements also follows human-evaluation reporting guidance. [van der Lee et al., 2019](https://aclanthology.org/W19-8643.pdf)

### Counterargument: Are Existing Scores or Free-Text Feedback Sufficient?

If a person is choosing for their own writing, free-text feedback has minimal preparation burden and may fit the purpose. Automatic metrics such as SARI have also aligned with system rankings in particular comprehension tasks. However, the relationship between a metric and human evaluation depends on the task, generation method, and reference text; it does not guarantee meaning preservation for this Skill. [Alva-Manchego et al., 2021](https://aclanthology.org/2021.cl-4.28.pdf), [Agrawal & Carpuat, 2024](https://aclanthology.org/2024.tacl-1.24.pdf)

Therefore, the first version should not require many ratings; limit them to a judgment, quotation, and reason. Show automatic warnings or LLM scores only after the primary human evaluation. Pairwise comparison makes preference direction easier to see, but does not measure the magnitude of improvement. Do not claim improved quality for general readers based on one person's evaluation. [Ethayarajh & Jurafsky, 2022](https://aclanthology.org/2022.emnlp-main.406.pdf)

## 3. Key Points: Reuse Existing Records and Start Small

### Define Success Differently by Mode

| Mode                  | Contract and preservation checks                                                                    | Quality judged by people                                |
| --------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| A: Generate new text  | Agreement with request, source materials, and required items; unsupported additions                 | Answers to readers' questions, structure, naturalness   |
| B: Edit text          | Conditions, negation, agent, quantities, tense, sentence function                                   | Ease of understanding, rereading, preservation of style |
| C: Insert line breaks | Whether only permitted line breaks changed; compare original characters and existing whitespace too | Topic boundaries, over-segmentation, reading flow       |
| D: Fiction            | Operation contract for plan/draft/continue/revise/critique, setting, viewpoint, and disclosure      | Voice, dialogue, rhythm, unintended confusion           |

Do not require exact source preservation for D draft/continue, or apply uniform shortening and conclusion-first rules to fiction. The existing strict check for C also normalizes BOM and CRLF, so strict preservation requires additional comparison against the original data. [Mode requirements](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:18), [fiction evaluation](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/references/fiction-writing.md:79), [machine-check limits](/Volumes/SSD/Programming/japanese-readability-editor/evals/README.md:21)

### Compare Tools and Libraries

| Candidate                  | Useful capability                                        | Decision and added burden for this case                                                                                                                                                                                                                                                                       |
| -------------------------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Local HTML + standard APIs | Load selected JSON, forms, download results              | **First choice for the initial version.** Suitable for a small group. Assignment, validation, and resume need implementation. [FileReader](https://developer.mozilla.org/en-US/docs/Web/API/FileReader)                                                                                                       |
| Gradio                     | Python UI, record inputs and outputs through Flagging    | Reuse if already adopted. Flag alone does not provide assignment, reasons, or resume management. [Official docs](https://gradio.app/main/docs/gradio/flagging)                                                                                                                                                |
| Streamlit                  | Forms, selection, result download                        | Suitable for a Python prototype. Persistence and evaluation procedures need separate design. [Official docs](https://docs.streamlit.io/develop/api-reference/widgets)                                                                                                                                         |
| Label Studio               | Pairwise comparison, choices, span labels, JSON output   | Prefer if ongoing multi-person use or span annotation is needed. Represent tie/uncertain explicitly through Choices. [Pairwise](https://labelstud.io/tags/pairwise.html), [Choices](https://labelstud.io/tags/choices.html)                                                                                   |
| Argilla                    | Ratings, labels, free text, span annotation              | Consider if already in use. Its official README says new feature development is not planned, so it is not preferred as a new platform. [Official repository](https://github.com/argilla-io/argilla)                                                                                                           |
| SciPy / statsmodels        | Aggregate confidence intervals and inter-rater agreement | Optional dependencies at the analysis stage after data is collected. Do not add them to the Skill itself. [bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html), [kappa](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.cohens_kappa.html) |

Local HTML should use no external CDN and display text as strings. Make explicit JSON export and reimport the default for saving. Since localStorage behavior under `file:` is not guaranteed, do not rely on it as the only place to save responses. This is an implementation proposal; behavior with network access blocked has not been verified. [MDN localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)

Use supporting Skills for limited roles. [huggingface-gradio](/Users/masatomiwada/.codex/plugins/cache/openai-curated-remote/hugging-face/1.0.0/skills/gradio/SKILL.md) is suited to building the UI if Gradio is selected; [statistical-analysis](/Users/masatomiwada/.codex/plugins/cache/claude-cowork/data/1.0.0/skills/statistical-analysis/SKILL.md) to considering effect sizes, interval estimates, and small samples; and [skill-creator](/Users/masatomiwada/.codex/skills/.system/skill-creator/SKILL.md) to incorporating demonstrated failures into rules or examples. None substitutes for human Japanese evaluation or verification of actual quality.

### Information to Save and Improvement Cycle

| Record     | Minimum fields                                                                                                                                                                                             |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| task       | Document ID, request, target reader, mode/operation, source/materials, candidate text and hash, generation conditions, skill version, evaluation-criteria version, data split                              |
| assignment | Task ID, pseudonymous evaluator ID, expertise, fixed left/right assignment, date/time                                                                                                                      |
| annotation | Preservation judgment for each candidate, quality preference, quotation and sentence number for issue location, type/severity/reason, optional revision suggestion, response revision number, elapsed time |

Keep the table mapping candidate names to identities separate from evaluation files. Hiding names in the UI alone does not ensure strict blinding. Use distinct values for unanswered, uncertain, and tie; keep primary ratings and adjudication in separate records. For the first version, do not require precise character-span selection; start with quotations and sentence numbers.

Existing `run.json` contains source, candidates, generation conditions, and hashes, so import it read-only and add human evaluation records alongside it. Do not change the existing generation or scoring schema. The flow is "freeze generation conditions → independent evaluation → adjudicate disagreements → turn recurring failures into regression cases → minimal human revision → compare old/new on unused documents." **Saving an evaluation and updating a Skill are separate steps**; automatic application is not part of the first version. [Existing evaluation CLI](/Volumes/SSD/Programming/japanese-readability-editor/tools/evaluate_readability.py:108)

| Priority | Next item                                                                                                       | Opportunity cost and decision condition                                                                                  |
| -------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| P0       | Mode B criteria, JSON format, 3–5 practice examples                                                             | Align criteria before the UI. It takes preparation time but reduces collection of incomparable responses.                |
| P1       | Local evaluation interface in `tools/`, response resume and aggregation, required tests/fixtures and procedures | Avoid authentication, database, and public server; spend time on evaluation operations. JSON integration effort remains. |
| P2       | Pilot and reevaluation on unused documents; revise Skill for demonstrated problems                              | Reduces overreaction to one-off preferences, but takes time to establish improvement.                                    |
| P3       | Dedicated forms for A/C/D, comprehension tests, and an existing collaborative evaluation platform if needed     | Building every mode at the start expands evaluation axes and UI validation. Expand based on actual use.                  |

The initial changes can be limited to development tools, tests, and procedures; the `skill/` canonical source, distribution and installation process, and required Skill dependencies need not change. At implementation time, check that existing records cannot be overwritten, inputs are valid, assignments persist when resuming, HTML is handled safely, and Japanese text and keyboard operation work.

## 4. Example: A Shorter Text Fails if It Changes the Meaning of an Instruction

In an existing evaluation, the policy statement "広げないようにします" ("I will try not to expand it") changed into the request "広げないでください" ("Please do not expand it"). A human evaluation form could record "meaning preservation: fail," "category: sentence function / agent," "evidence: the two relevant expressions," and "reason: who acts and the purpose of the utterance changed." A revision suggestion is optional; brevity and naturalness do not make it pass. [Actual evaluation record](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization-result.md:29)

Rather than adding another abstract rule to fix this one example, consider contrastive examples for policy statements, requests, and prohibitions, plus a procedure to compare communicative intent before and after editing. Move the used example into regression data and check whether similar failures decrease on unused examples. [Existing rule for checking sentence function](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:55)

## 5. Plain-Language Explanation

Put simply, this is not a box for scoring text; it is a tool for recording "what is hard to read, where, why, and what must not have changed," then checking whether the next revision really improved it.

## 6. Critical Self-Assessment: Improvement Rates Cannot Be Predicted; First Design for Measurability

**The direct effect that can reasonably be expected is better traceability and reproducibility of findings; a conditional indirect effect is fewer recurring failures.** The latter depends on producing an effective revision from findings and confirming it on unused documents. There is no basis to predict a percentage improvement in comprehension, reading speed, or post-editing time. Evaluation burden and adjudication work may increase, or excessive concern about preservation may lead only to retaining the original text.

For an exploratory pilot, start with 24–40 Mode B documents and 2–3 evaluators per document. These are practical planning values, not a guarantee of adequate statistical power. Record document type, length, and reader; separate a diagnostic set of known failures from a set representing ordinary use. After an evaluated document has been used to improve the Skill, do not return it to the unused set for confirming results. [Small samples and power: Card et al., 2020](https://aclanthology.org/2020.emnlp-main.745.pdf)

Thirty documents × three people yields 90 ratings, not 90 independent documents. Report simple agreement, judgment distributions, and an agreement coefficient suited to the scale. A suitable proposal for interval estimates is to resample all ratings grouped by document. However, such an interval is conditional on the participating evaluators; estimating across evaluators generally requires a separate design. [Artstein & Poesio, 2008](https://aclanthology.org/J08-4004.pdf)

To illustrate the scale of uncertainty, under the approximation of independent binomial observations and a success rate near 50%, the approximate 95% interval is ±18 percentage points for 30 cases and ±10 points for 100. This is not an effect forecast or an interval for the planned study, which includes ties and correlation. Workload is also unmeasured. If each document pair took an assumed 5–10 minutes, 24–40 documents × 2–3 evaluators would require about 4–20 person-hours, with practice and adjudication additional. Typical evaluation time includes annotation and UI operation; do not treat it as reading speed.

Subjective confidence in the design direction is **0.8**. This reflects confidence in the fit with existing contracts and research, not a calibrated probability or likelihood of quality improvement. Japanese interaction, library compatibility, networking, save recovery, and effects for target readers are unverified.

## 7. Conclusion

Starting with anonymous Mode B comparison, preservation judgments, evidence-backed findings, and JSON storage is a minimal, verifiable proposal for the current state. The first outcome check should not ask only whether high ratings increased; it should connect the full count of meaning changes with which problems were fixed and whether they also improved on unused documents. Expand when demand for collaboration or other modes is confirmed.

## 8. References

See the direct links to primary sources in the text. The main sources considered were [van der Lee et al. (2019)](https://aclanthology.org/W19-8643.pdf) for human-evaluation design, [Yamashita et al. (2026)](https://aclanthology.org/2026.lrec-1.85/) for Japanese document evaluation, [Agrawal & Carpuat (2024)](https://aclanthology.org/2024.tacl-1.24.pdf) for meaning preservation, [Carrer et al. (2024)](https://aclanthology.org/2024.humeval-1.7.pdf) for comprehension and editing effort, [Card et al. (2020)](https://aclanthology.org/2020.emnlp-main.745.pdf) for statistical power, and [Artstein & Poesio (2008)](https://aclanthology.org/J08-4004.pdf) for inter-rater agreement. Detailed survey evidence is in the [methods memo](/Volumes/SSD/Programming/japanese-readability-editor/works/for-agent/requirement-definition-document/002-human-evaluation-methods.md), [tool memo](/Volumes/SSD/Programming/japanese-readability-editor/works/for-agent/requirement-definition-document/001-evaluation-tool-selection.md), and [existing Skill integration memo](/Volumes/SSD/Programming/japanese-readability-editor/works/for-agent/design-document/004-human-review-tooling/integration-document.md).

Not performed: implementation, dependency installation, browser-interaction testing, human study, or test reruns. The feature review was a desk check of official documentation.
Main risks: overfitting to a small number of evaluators' preferences and mistaking preferences among passing candidates for overall improvement.
