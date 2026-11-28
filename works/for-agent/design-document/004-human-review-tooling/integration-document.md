# Integrating a Human-Evaluation Tool with the Existing Skill

Checked on 2026-10-16. Target commit: `26ec2c1d04da69409702f49408311c80af79174b`. No AGENTS.md was present in the repository, its ancestors, or the immediate paths consulted for this work; instructions supplied in the conversation and RTK.md were followed. No implementation, model rerun, or dependency installation was performed.

## 1. What Already Exists, and What Human Evaluation Could Add

### Takeaway: Existing Tools

The current approach centers on model scoring of meaning preservation and mechanical candidate detection. It would be useful to add an entry point where people read the source, request, and materials, then record readability gains separately from meaning loss. A small design can use existing JSON records as input and save ratings to separate files.

### Cited Findings: Existing Evaluations

- The Skill aims to reduce cognitive load while preserving meaning, accuracy, and necessary information, rather than to "make it shorter." It protects numbers, conditions, exceptions, agents, and similar details; character-count guides are not pass/fail criteria. — [SKILL.md:10-16](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:10), [SKILL.md:64-83](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:64)
- The existing comparison procedure hides version names, reverses left/right order, assigns each version pass/fail/uncertain for meaning preservation, and compares readability as left/right/tie/uncertain only for pairs where both pass. It requires explanations with evidence from the relevant text. Existing contracts distinguish human judgment, implementer self-review, and model scoring. — [comparison procedure:30-40](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-comparison.md:30)
- The generalization evaluation used 48 outputs from 16 cases × 3 repetitions. Meaning preservation was 46 pass, 1 fail, and 1 uncertain; all 12 grading-inspection questions were correct; the result was HOLD. Of 45 Mode B outputs, 13 were identical to the source after trimming whitespace. The 46 passes were not confirmed by independent human evaluators. — [evaluation result:18-27](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization-result.md:18)
- A concrete failure changed the policy statement "広げないようにします" ("I will try not to expand it") into the request "広げないでください" ("Please do not expand it"). An uncertain case changed the temporal sequence "引き上げた後" ("after raising it") into "引き上げると" ("when raising it"), which may also imply causation. — [evaluation result:29-49](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization-result.md:29)
- The development tool `evaluate_readability.py` records three Skill texts, hashes, cases, generation and scoring instructions, model, and raw output in `run.json`. Grading inputs include source, context, candidate, and preservation/prohibition items; `source_id` and `kind` are hidden from the grading model. However, model scoring covers meaning preservation only, not which candidate is more readable. — [generation and scoring instructions:18-31](/Volumes/SSD/Programming/japanese-readability-editor/tools/evaluate_readability.py:18), [grading_items:108-150](/Volumes/SSD/Programming/japanese-readability-editor/tools/evaluate_readability.py:108), [prepare:173-180](/Volumes/SSD/Programming/japanese-readability-editor/tools/evaluate_readability.py:173)
- Current run records contain `schema_version/status/suite/outputs/grading_items/grading_calls/skill_sha256/runner_sha256/summary`, and the actual summary matched HOLD and 46/1/1. — [run.json](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization-run/run.json)
- Mechanical checks identify candidate revisions; they do not guarantee meaning. The strict check for C normalizes CRLF/BOM, so confirming a contract to preserve every character, existing space, line break, and BOM also requires comparing the original text or bytes. — [SKILL.md:103-113](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:103), [evaluation procedure:21-29](/Volumes/SSD/Programming/japanese-readability-editor/evals/README.md:21)

### Inferences: Minimal Tool

- A minimal tool would be a local developer-facing interface that reads existing `run.json` and manually prepared inputs/outputs, supports evaluation in a browser, and explicitly exports results as JSON. For version comparisons, retain fixed left/right assignments per session. Hiding machine warnings, existing LLM judgments, and version names until primary human ratings are submitted may reduce anchoring on them.
- Normally show the full source and candidate; make diffs optional. Reading only differences may bias evaluation toward local edits and miss comprehension problems at paragraph level.
- Mode B is the main pilot because it has known failures and uncertain cases. Select examples with attention to four layers: long text, conditions/negation, sentence function, and causality. A set containing only known fail/uncertain cases can identify defects but cannot estimate improvement in ordinary use.

### Gaps: Existing Evidence

- No independent human evaluation data, comprehension tasks, or reading-time measurements were found in this repository. The current model pass rate cannot predict effects on reading speed or comprehension.
- The cost, sharing scope, and operational burden of external services were outside the scope of this survey. Decide these alongside the review of related libraries.

## 2. Evaluation Dimensions by Mode and Feedback Format

### Takeaway: Mode-Specific Evaluation

Applying the same "readability score" to every mode is inappropriate. First record violations of the request, mode, or operation contract separately from quality preferences.

### Cited Findings: Mode Contracts

- A generates new text, B rewrites while preserving meaning, C only inserts line breaks and blank lines. D is fiction with distinct contracts for plan/draft/continue/revise/critique. Explicit requests take priority; if they cannot be met, do not silently switch modes. — [SKILL.md:18-35](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:18)
- Structural revisions in A/B check whether the text answers the reader's question and preserves subject-predicate and modifier relations, the scope of negation/reasons/conditions, sentence function, and tense. B requires comparison with the source. — [SKILL.md:55-62](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:55), [SKILL.md:88-101](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:88)
- D revise preserves events, motivations, relationships, viewpoint, certainty, disclosure order, symbols, and ending; critique does not rewrite the text, but provides evidence and explains its impact on readers. Do not require exact source retention or one-to-one sentence correspondence for D draft/continue. — [fiction-writing.md:23-35](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/references/fiction-writing.md:23)
- Do not uniformly apply metaphor explanation, shortening, subject completion, or tense normalization to D. Evaluate literary quality through voice, viewpoint and knowledge, disclosure order, confusion, and request fit; no single score guarantees whether it is engaging. — [fiction-writing.md:52-60](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/references/fiction-writing.md:52), [fiction-writing.md:79-85](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/references/fiction-writing.md:79)

### Inferences: Proposed Dimensions

Proposed evaluation dimensions (a specification proposal, not implemented):

| Mode | Contract and preservation                                                                       | Human-judged quality                                                                                                       | Misleading evaluation to avoid                                                      |
| ---- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| A    | Agreement with instructions/materials, unsupported additions, required items/terms/numbers      | Answers to readers' questions, structure, comprehensibility, naturalness                                                   | Treating exact source match or brevity alone as success                             |
| B    | Conditions, negation, agent, quantities, sentence function, emphasis, tense                     | Clarity of subject/predicate and modifiers, rereading, paragraphs, naturalness. Compare only pairs that pass preservation. | Higher score for more changes; allowing quality scores to offset meaning changes    |
| C    | Mechanically check that only line breaks were inserted; record handling of original bytes       | Topic boundaries, reading flow, over-segmentation                                                                          | Rewarding word substitutions                                                        |
| D    | Operation, confirmed setting, scope of preserving existing text, viewpoint/knowledge/disclosure | Voice, dialogue, rhythm, unintended confusion. Separate preference from inconsistency.                                     | Applying generic-document shortening, conclusion-first writing, or metaphor removal |

Limit the minimum record to these fields:

- `task`: schema_version, task_id, mode, operation, request, audience/context, source/document_id, source_text or source_bytes_sha256, candidates[{candidate_id,text,skill_sha256,model_id,run_id,output_id}], rubric_version, split(training/regression/holdout). Existing run references and output hashes prevent candidate mix-ups. For byte preservation in C, also save check results generated from the original file.
- `assignment`: assignment_id, task_id, evaluator_id (pseudonyms allowed), evaluator_role/familiarity with the subject, candidate left/right order, date/time. Do not display the candidate mapping used for aggregation during scoring.
- `annotation`: annotation_id, assignment_id, revision, contract_status(pass/fail/uncertain), answers by dimension, preference(left/right/tie/uncertain/not applicable), evidence[{candidate_id,start,end,quote,category,severity,reason}], optional_suggestion, elapsed_ms, rubric_version. Keep unanswered, not applicable, uncertain, and tie as distinct values. Check offset and quotation consistency when saving.
- The first form has three blocks: "contract violation/uncertain → location and reason," "quality comparison → left/right/tie/uncertain and reason," and "optional revision suggestion." Collect a few evidence-backed dimensions rather than requiring everyone to fill many score fields. Run comprehension questions and time comparisons in separate sessions. Ordinary rating time includes close reading, annotation, and UI operation; it is not reading speed.
- Save primary ratings independently. Preserve disagreements as separate adjudication records rather than overwriting them. Do not assign the same severity to "the technical meaning is different" and "I prefer this style."

### Gaps: Evaluation Schema

- Evaluator count, expertise, target documents, and whether evaluators are authors or third parties are unspecified. There is no basis for treating aggregated ratings as representative of general readers.
- The schema is a proposal, not a recommendation to change existing schema v1 as-is. A shared envelope for multiple candidates, A/C/D, and manual input is safer outside the existing generation record.

## 3. Minimal Improvement Loop and Scope of a Future MVP

### Takeaway

An evaluation-collection interface alone will not improve the Skill. Findings must be turned into reproducible cases and limited rules or examples, then quality and preservation must both be rechecked on unused documents.

### Cited Findings

- The existing evaluation plan says that once inputs/outputs have been reviewed and adjustments made, later checks cannot be called evaluation on unused documents; move them to regression and use new inputs. The authored set of 16 documents × 3 repetitions is not 48 independent documents and cannot estimate general failure rates. — [readability-generalization.md:9-21](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization.md:9), [same:43-45](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization.md:43)
- The current tool permits only a new output destination and checks model-score format, omissions, inspection errors, uncertainty, and model changes. Tests confirm no network use, refusal to overwrite existing records, and preservation of partial failures. — [evaluate_readability.py:124-180](/Volumes/SSD/Programming/japanese-readability-editor/tools/evaluate_readability.py:124), [test_evaluate_readability.py:28-99](/Volumes/SSD/Programming/japanese-readability-editor/tests/test_evaluate_readability.py:28)
- The Skill prioritizes use of the standard library, and the existing development evaluation CLI does not add external model dependencies to the distributed Skill. — [design.md:42](/Volumes/SSD/Programming/japanese-readability-editor/works/for-agent/design-document/005-readability-principles/design-principles-document.md:42), [readability-generalization.md:25](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization.md:25)
- The only canonical source is `skill/japanese-readability-editor/`; the packaging tool enumerates its files to generate ZIPs and copies for each environment. Development tools in `tools/` are outside that source. — [package.py:20-43](/Volumes/SSD/Programming/japanese-readability-editor/tools/package.py:20), [test_package.py:43-54](/Volumes/SSD/Programming/japanese-readability-editor/tests/test_package.py:43)
- The full check includes `unittest discover`, so tests placed under `tests/` will run during the existing full check. — [check_all.py:64-72](/Volumes/SSD/Programming/japanese-readability-editor/tools/check_all.py:64)

### Inferences

Proposed improvement cycle:

1. Freeze the Skill, model, instructions, and evaluation criteria. Select documents for the same use case and generate or import candidates.
2. Conduct independent human evaluation with version names and LLM judgments hidden. Double-rate a small subset and calibrate differences in interpretation first.
3. Separate contract violations, quality problems, preferences, and insufficient information. Have a responsible person adjudicate disagreements using the source and materials.
4. Make only recurring, demonstrated problems into minimal Skill revisions. Do not simply multiply abstract instructions such as the existing "preserve sentence function" rule; consider failure/retention examples and concrete comparison actions.
5. Add cited examples and counterexamples with natural source text to regression data. Compare before/after Skill versions under the same conditions, assessing preservation regressions separately from quality gains.
6. Even after known examples succeed, reevaluate on different unused documents. Check for overfitting to particular evaluators' preferences by using other people or fields.

Minimum scope for a future MVP (not to be implemented in this work):

| Area                                         | Proposed change                                                                                                                                      | Impact and checks                                                                                                                                                                                  |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| tools/                                       | One development CLI such as `human_review.py` that reads existing `run.json` or shared task JSON and handles a local evaluation UI and response JSON | Preserve the existing generation/scoring CLI and schema in `evaluate_readability.py`. Treat run as read-only.                                                                                      |
| UI                                           | Small local HTML/JS generated with the Python standard library; explicit download/reimport of response JSON                                          | Display Japanese, line breaks, quotations, and code unchanged; do not execute HTML strings. Check `textContent` for XSS prevention, keyboard use, save state, and left/right order after resuming. |
| Data                                         | Versioned task/annotation format, pseudonymous evaluator ID, evidence quotations, data split, aggregation                                            | Test invalid enums, candidate mismatch, duplicates/omissions, double-counting revisions, uncertain judgments, and C source-byte mismatch.                                                          |
| tests/fixtures                               | Small tests for new human-evaluation tool and minimal fixtures for A/B/C/D                                                                           | Roundtrip, source preservation, invalid input, HTML injection, response resume, exclusion of pairs that fail preservation. Check browser saving and keyboard use separately.                       |
| evals/README.md and docs/                    | Procedure, evaluation criteria, limitations, JSON format, storage location, existing-record import example                                           | Keep description consistent with CLI. Do not publish or bundle research notes or real documents accidentally.                                                                                      |
| skill/, package/install, dependency settings | No changes needed for initial evaluation UI MVP                                                                                                      | Design separately once distribution to users is a confirmed requirement. Putting the UI in the canonical source would affect every distribution target.                                            |

- A local HTML proposal avoids collaboration editing, authentication, remote servers, automatic cloud transmission, and automatic fine-tuning. In exchange, downloading and reimporting responses takes some extra effort. For a few people and dozens of cases, it is predicted that the opportunity cost of avoiding an operations platform is lower. If concurrent work by many people or strict access control becomes necessary, prefer an existing annotation platform.
- Expected effects in order: (i) improved reproducibility and traceability of findings is relatively likely; (ii) discovery of meaning/reading problems specific to humans is expected if human perspectives differ from model perspectives; (iii) fewer specific failures is expected only if revisions, regression, and unused-document evaluation succeed; (iv) no numerical prediction can currently be made for general comprehension, speed, or literary-quality improvement.
- Measure evaluation-collection effort, adjudication, Skill bloat from adding rules, and the adverse effect where increased caution retains original text and halts improvement. Treat planned effort and evaluator counts as planning values, not measured effect sizes.

### Gaps

- Before human evaluation is measured, there is no evidence for "X% improvement" or "Y hours saved." If assigning confidence, distinguish confidence in the surveyor's design judgment from the probability of demonstrated effectiveness.
- The new UI implementation, tests, real-browser checks, and rerunning existing tests were not performed in this survey. The finding that this repository lacked human evaluation applies only to the files reviewed; it does not establish that no unshared external evaluation exists.
