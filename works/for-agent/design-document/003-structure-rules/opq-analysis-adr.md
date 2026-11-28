---
status: accepted
date: 2026-11-11
decision-makers: User (requested adding OPQ analysis and asked for research and testing if useful, with implementation if effective), Claude Code (research and verification)
---

# Whether to add a rule for reaching a conclusion from the reader's questions (OPQ: objective, problem, question) (decision: not adopted)

Tracking: [Issue #160](https://github.com/Mr-Kondo/japanese-readability-editor/issues/160). Prior evaluation: [ADR 2026-11-11-section-single-message](section-single-message-adr.md) (rule to limit each section to one message was not adopted).

## Provenance note

The historical `adr_sha256` values in `run.json` already differ from the pinned pre-translation Japanese originals. `check_frozen()` verifies runner and helper files, not ADR bodies. The preserved Japanese originals are not claimed to be experiment-time snapshots. See [pre-translation OPQ provenance](../index.md#pre-translation-opq-provenance).

## Context

User request: Add “OPQ analysis” for business documents and presentations to the skill. Conduct additional research and verification from another perspective if needed, and implement it if it appears effective.

### OPQ analysis (as researched)

| Element          | Description                                                                     |
| ---------------- | ------------------------------------------------------------------------------- |
| O (Objective)    | What the reader wants to achieve                                                |
| P (Problem)      | The gap between the current state and the objective                             |
| Q (Question)     | What to do to close the gap; the question the reader wants answered             |
| Content to write | The answer to Q, in the form of a proposal, request, or decision for the reader |

Japanese course materials ([slide 1](https://speakerdeck.com/mssmkmr/kao-eruji-shu-shu-kuji-shu-matome), [slide 2](https://speakerdeck.com/nyattx/pyramid-structure)) describe OPQ as based on _The Pyramid Principle_ by Minto. **It could not be confirmed whether Minto herself used the abbreviation OPQ.** No English-language source using the name OPQ was found. A related method, SCQA (situation, complication, question, answer), is widely introduced in consulting materials ([Management Consulted](https://managementconsulted.com/scqa-framework/), a secondary source). Its full text was not checked. Therefore, OPQ is positioned as one Japanese-language teaching approach for organizing ideas before writing, based on the Pyramid Principle. Confidence is low; do not use it as “evidence of an improvement rate.”

OPQ is a tool for deciding “what to write” before writing; it was not designed as a tool for revising written prose.

## Why the previous evaluation did not work and how that informs this design

The previous evaluation (section splitting) tested an idea supported by prior research, but neither the old nor the candidate version split mixed sections. Separate observed facts from conjecture about why.

| Type                  | Description                                                                                                                                                                                                                                                                 |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Observation           | The old version returned s01 (four topics under “How to use” in a README) unchanged in all three runs. The candidate did the same. The candidate acted only on s04, which matched the example in the rule; it over-split and shifted what the concluding phrase applied to. |
| Observation           | Mode B was “rewrite within the bounds of preserving meaning.” The model treated adding or splitting headings as outside the default scope of rewriting (as inferred from the outputs).                                                                                      |
| Conjecture (untested) | Prior research supports a design principle for people while writing and an effect on human readers' memory; it does not show that a rule changes LLM behavior when revising existing prose. Therefore, adding the rule alone did not change the behavior.                   |
| Conjecture (untested) | Readers may have perceived mixed sections such as s01 as one topic (“How to use”). Most judgments were ties.                                                                                                                                                                |

Applied to this evaluation: (1) Target **the order of sentences and paragraphs (move the conclusion toward the beginning)**, an operation already allowed by Mode B, rather than an operation such as splitting headings that the model does not take by default. (2) Try OPQ, a tool for writing, in **Mode A (create new text from source material)** as well. (3) First check whether the old version already meets the goal (ceiling). (4) Use smaller pairwise-judgment batches to avoid missing judgments. (5) Record this ADR's body hash in the run record.

## Overlap with existing rules

| Existing location                                                         | Content                                                                                                                                       |
| ------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `readability-rules.md` §1, What to check                                  | “Who will read this, and for what purpose?” “Which reader question does each paragraph answer?” “Does the conclusion appear only at the end?” |
| Same document §13 (preparation for new generation), and `SKILL.md` Mode A | Before writing, organize the reader, information needed by the reader, the conclusion, and facts that support the conclusion.                 |
| Same document §6, “Unresolved questions”                                  | Answer what the reader has been led to expect.                                                                                                |
| Around §3, “Conclusion and supporting details”                            | Give the conclusion first, then conditions and reasons.                                                                                       |

There is substantial overlap. OPQ would add three things: (a) vocabulary and a procedure for defining the conclusion as the answer to the reader's objective, problem, and question; (b) a way to fix a “conclusion appears only at the end” structure (move the answer to the opening paragraph); and (c) a safeguard against inventing objectives or problems that are absent from the source material.

## Options and selection

| Option                       | Description                                                                                                                                                                                                | Assessment                                                                            |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- |
| A. New numbered rule         | Create it separately from §1.                                                                                                                                                                              | Overlaps with existing rules. `SKILL.md` has reached its 175-line limit. Not adopted. |
| B. Strengthen existing rules | Add a subsection to §1 called “Does it answer the reader's question (OPQ)?” and revise wording in the §13 item and two lines in `SKILL.md` (diagnostic order 1 and Mode A), without increasing line count. | **Candidate. Decide whether to adopt based on the evaluation below.**                 |
| C. Do not adopt              | Existing rules are sufficient.                                                                                                                                                                             | Conclusion if the old version already meets the goal or the candidate is ineffective. |

Do not add OPQ signals to `measure.py`. OPQ concerns meaning and cannot be counted by a script.

## Hypotheses

H1: The candidate places conclusions and requests near the beginning more often than the old version for documents where the conclusion or request is buried (Mode B) and documents created from source material (Mode A).
H2: It does so without disrupting the order of documents that already lead with the conclusion or documents where chronology carries meaning.
H3: It follows ordering and structure requirements, and Paragraph-only constraints.
H4: It does not worsen retention of meaning, numbers, and code, or the rule against adding objectives, issues, and background absent from the original or source material.

## Evaluation design

Evaluation set: [11 self-authored cases](../../../../evals/opq-cases.json). Three B cases with buried conclusions (o01–o03), three A cases created from source material (o04–o06), three unchanged controls (o07 conclusion-first, o08 chronological order, o09 short notice), Paragraph-only (o10), and fixed-order instruction (o11). Use the existing 12 controls to calibrate the meaning-retention evaluator.

- Old version: `b589a94` on main (skill v0.22.0). Candidate: `SKILL.md` (wording in diagnostic order 1 and two Mode A lines) and `readability-rules.md` (subsections in §1 and §13). `examples.md` is identical.
- Generation: three runs per case per version; `sonnet / medium`, no tools, new context (same call as the prior evaluation).
- Deterministic check: whether all terms indicating the conclusion or request (`lead_terms`) appear within the first 220 characters of the body, excluding headings and whitespace. For controls and fixed-order constraints, check whether opening requirements (`first_must_have`, etc.) are preserved. For Paragraph-only, compare after removing whitespace.
- Blind judgment (only pairs that pass meaning retention in both versions, left/right reversed, batches of four): `answer_first` (whether the answer is at the beginning and background later) and `no_additions` (whether it adds objectives, issues, background, effects, or examples absent from the original or source material).
- Staging: generate the old version, then the candidate. If the old version already puts conclusions in the opening in at least 14 of the 18 outputs for the six primary cases, treat it as ceiling and do not adopt the rule.

## Success criteria

Adopt the candidate only if all of the following hold.

1. Retention: All 33 candidate outputs pass meaning retention; its fail and uncertain counts are no higher than the old version. All 12 calibration controls meet expectations. Actual model identifiers match.
2. Placement near the beginning (H1): Across 18 outputs for the six primary cases, the candidate has at least four more cases than the old version where all `lead_terms` appear within the first 220 characters.
3. Pairwise `answer_first` judgment (H1): The candidate wins more often than the old version.
4. Pairwise `no_additions` judgment (H4): The candidate wins at least as often as the old version.
5. Unchanged controls (H2): Across nine outputs for o07–o09, at most one candidate output violates the opening requirement, and the count is no higher than the old version.
6. Constraints (H3): Zero violations in the six candidate outputs for o10 and o11.

## Rollback criteria

- If the old version already puts conclusions or requests at the beginning in at least 14 of 18 outputs for the six primary cases (ceiling), do not add the rule; do not adopt it.
- If any criterion is unmet, do not add the rule. If an H2, H3, or H4 failure suggests narrowing the rule, run it as a separate experiment without overwriting this record (at most once).
- If pairwise judgment cannot be run (missing judgments), treat criteria 3 and 4 as unmet and do not adopt the rule. Do not rerun.

## Limitations (stated in advance)

- The 11 self-authored cases are development inputs used to shape the design and do not show generalization to unused documents. They are biased toward cases where the source states the objective, problem, and question and identifies the reader (conditions favorable to OPQ). Behavior when the reader is unknown was not measured.
- “The conclusion appears at the beginning” and “the text is easy to read” are different. Opening placement is a deterministic proxy; human reader comprehension is not measured.
- Evaluation uses the same model family (sonnet), with no human scoring. Three repeated runs are not independent; do not calculate general improvement rates from them.
- Product skill invocation (`--skill-dir`) and tool use are out of scope (the skill was pasted into the prompt).
- Creating presentations (slides) is out of scope; only prose structure is evaluated.

## Results (experiment 1; records: `evals/opq-run/`)

The ADR hash before execution is `adr_sha256` in the run record. The old version was not at ceiling (opening placement 8/18), so the candidate was generated.

| Criterion                                            | Old version                  | Candidate                | Assessment                                                                                                                                                    |
| ---------------------------------------------------- | ---------------------------- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2. Opening placement (six primary cases, 18 outputs) | 8/18 (B 2/9, A 6/9)          | **18/18** (B 9/9, A 9/9) | Met (difference 10; threshold is 4)                                                                                                                           |
| 5. Violations in nine unchanged-control outputs      | 0                            | 0                        | Met                                                                                                                                                           |
| 6. Constraint violations (o10 and o11)               | 0                            | 0                        | Met                                                                                                                                                           |
| 1. Meaning retention (33 outputs)                    | pass 31, fail 1, uncertain 1 | pass 29, **fail 4**      | **Not met**. All 12 calibration controls met expectations.                                                                                                    |
| 3–4. Pairwise judgment                               | —                            | —                        | **Could not run** (`execution_failed`). Explanatory text followed the judgment, causing a parse failure. The two batches already judged remain in the record. |

The four candidate fails were additions made while moving content toward the beginning: introductory statements “以下は…の経緯です” and “承認をお願いする背景は…です” (two cases in o02); an evaluation, “9月は5%減で、減少幅が広がっています” (o05); and added character or conditions to the request, “ご推薦ください” and “負担が大きくないかをご確認のうえ” (o06). The old version had one fail (o06) and one uncertain (o04, omission of “見込み”), which were different types.

Experiment 1 conclusion: **The rule helps move conclusions toward the beginning, but it did not meet the pre-registered criterion 1 (meaning retention), so it was not adopted.** Since the types of additions were identifiable, conduct the “narrow the scope in a separate experiment, at most once” work specified in the rollback criteria.

During execution, one defect in `runner.py` judgment was fixed (after old-version generation and before candidate generation). In a short control document, if a term intended for later appeared within the opening window, it was incorrectly reported as “changed.” Since the original itself did not pass this check, comparison of occurrence positions replaced it, with a self-check that the original passes. Criteria, cases, and outputs did not change. See `amendments` in the run record.

## Experiment 2 pre-registration (written before seeing results)

Compare revised candidate 2 with the experiment 1 old-version outputs (same skill and instructions; verify matching hashes before reuse).

Changes:

- Candidate 2: Add to the candidate's `readability-rules.md`: (a) add only words needed for the moved sentence to read on its own, and do not add transition sentences such as “以下は〜の経緯です”; (b) do not add evaluations or interpretations absent from the original or source material; (c) do not add a request's character (mandatory, recommended, optional) or conditions absent from the original or source material. Add one sentence with the same intent to §13. `SKILL.md` is unchanged from experiment 1's candidate.
- Cases: [15 cases](../../../../evals/opq2-cases.json). Add four new cases (n01–n04: two buried B, one A, one unchanged control) to the 11 experiment 1 cases (o01–o11). **o01–o11 are reused after seeing experiment 1 failures and revising the rules, so they are not independent.** n01–n04 are new and were not run against either version, but were created after the failure types were known. Generate only 12 new outputs for the old version on n01–n04; reuse o01–o11.
- Pairwise judgment: Change parsing to read only the first JSON object and add “Do not add explanations or supplementary text” to the judgment instructions. Rerun all experiment 1 judgments for experiment 2; do not use experiment 1 judgment results.
- Criterion 1 change: The experiment 1 requirement that “all 33 outputs pass” was not met by the old version itself (one fail, one uncertain). In experiment 2, change it to **candidate 2 has no more fails than the old version, and no more fail+uncertain combined (45 outputs each); all 12 calibration controls meet expectations; actual model identifiers match**. The intent of “does not worsen” is to be no worse than the old version; requiring every output to pass would be stricter than the old version. State that this change is made after seeing experiment 1 results.

Criteria (same structure as experiment 1, with counts adjusted to 27 and 45 outputs):

1. Retention: As above.
2. Opening placement: Among 27 outputs for nine primary cases, candidate 2 exceeds the old version by at least six.
3. Pairwise `answer_first`: Candidate 2 wins more often than the old version.
4. Pairwise `no_additions`: Candidate 2 wins at least as often as the old version.
5. Among 12 unchanged-control outputs (o07–o09 and n04), opening requirement violations are at most one and no higher than the old version.
6. Zero violations among the six outputs for constraints (o10 and o11).

Rollback: If the old version has opening placement in at least 21 of 27 cases (ceiling), or any criterion is unmet, do not add the rule; do not adopt it. Do not rerun (experiment 2 is the last). Treat missing judgments as failure to meet criteria 3 and 4; do not adopt.

Limitations: Same as experiment 1 (self-authored cases, same model family, no human scoring, opening placement is a proxy). In addition, o01–o11 were used to adjust the rule, so only n01–n04 count as independent evaluation. There are too few n01–n04 cases to claim a general improvement rate even if adopted.

## Results (experiment 2; records: `evals/opq2-run/`)

Experiment 2 judgment: **HOLD (not adopted)**. It failed the pre-registered criterion 1 (meaning retention).

| Criterion                                                                                                                             | Old version                  | Candidate 2                      | Assessment                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | -------------------------------- | -------------------------------------------------------------------------------------------- |
| 2. Opening placement (nine primary cases, 27 outputs)                                                                                 | 17/27                        | 25/27                            | Met (difference 8; threshold 6)                                                              |
| Of these, discriminating cases o01–o06 (18 outputs)                                                                                   | 8/18                         | 16/18                            | Reference only                                                                               |
| 3. Pairwise `answer_first` (32 pairs; count wins/ties only when judgments from both reversed runs agree; disagreements are uncertain) | 0 wins                       | 15 wins, 10 ties, 7 uncertain    | Met                                                                                          |
| 4. Pairwise `no_additions`                                                                                                            | 0 wins                       | 0 wins (23 ties, 9 uncertain)    | Met                                                                                          |
| 5. Violations in 12 unchanged-control outputs                                                                                         | 0                            | 0                                | Met                                                                                          |
| 6. Constraint violations (6 outputs)                                                                                                  | 0                            | 0                                | Met                                                                                          |
| 1. Meaning retention (45 outputs)                                                                                                     | pass 43, fail 1, uncertain 1 | pass 40, **fail 4**, uncertain 1 | **Not met**. All 12 calibration controls met expectations. Actual model identifiers matched. |

The four candidate 2 fails: (1) For o03 and n02, the evaluator treated the reordering to move the request to the beginning as “a change in structure” and “a change in the basis for the request” (for n02, “if there is no response, it will not renew” appeared before the price increase information). (2) In o05, it again added the evaluation “減少幅が広がっています,” as in experiment 1. (3) In n03, it added “製造工程を確認します” as a check plan absent from the notes. One uncertain case was o03 (the relation in “見直しにあたり” became weaker). The old version had one fail in o04 (dropped “見込み,” making it definitive) and one uncertain in n03 (used process verification as a method).

Observations and limitations:

- New experiment 2 cases n01–n03 were not discriminating. The original itself already met the opening test (conclusion/request terms within the first 220 characters): n01 and n02 were not buried enough; n03 already placed source material first. The opening-placement difference arose only in o01–o06, inputs used to adjust the rule. **The experiment 2 opening-placement difference cannot be considered an independent evaluation.**
- Two of the meaning-retention fails came from the evaluator's criterion that “reordering counts as a structural change.” Its instructions included “order” among the checks and did not specify permissible meaning-preserving reordering (the permissible range was ambiguous). Changing this criterion after the fact would change the metric, so it was not changed. However, the n02 finding (the response-if-no-reply condition precedes the price increase rationale) is also a substantive concern that reordering can affect semantic relations.
- In experiments 1 and 2, the added evaluation (“減少幅が広がっている”) recurred even after a prohibition was added. Whether rule wording alone can suppress this tendency remains unchecked.
- Experiment 2 was the last (per this ADR's rollback criteria). Judgment ran successfully.
- The order check (o08, o11) checks only the relative order of terms required at the beginning and terms required later. It may miss other order violations involving moving terms (for example, moving an approval request from the end to the second paragraph). “Zero violations” is a weak guarantee.

## Decision

**Not adopted. Do not add the OPQ rule to the skill.** Leave `SKILL.md` and `readability-rules.md` unchanged (full candidate versions 1 and 2 are retained in `skill_files.candidate` in each `run.json`).

Rationale: The effect of placing conclusions and requests at the beginning was observed in two experiments (experiment 1: 8/18 → 18/18; experiment 2 o01–o06: 8/18 → 16/18; candidate also led in pairwise `answer_first` judgments). However, worsened meaning retention from reordering and added evaluations or plans failed the pre-registered criterion twice. Do not add a rule that fails the required meaning-retention condition, even when an effect is observed.

Items left for the user's decision (unresolved):

1. Whether to reevaluate after changing the meaning-retention criterion to allow reordering when moving requests to the beginning. Changing the criterion after seeing results changes the metric, so preregister it in a new ADR. → Done: [experiment 3 (2026-11-11-opq-analysis-reeval)](opq-reeval-adr.md). Decision: not adopted (constraint criterion unmet).
2. Whether to keep current practice without adding the rule, moving content toward the beginning only when the user explicitly asks to “put the conclusion first” (within the existing rules). Some of this already occurs in the old version: for example, 2/3 o03 outputs put the conclusion first, though much remains unmeasured.
3. Whether another method could suppress added evaluations (o05, n03), such as adding “do not use evaluative terms” to Mode A source material.
