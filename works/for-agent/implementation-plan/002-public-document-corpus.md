# Plan for Preparing Evaluation Data from Public Documents

These decisions were finalized in Issue #38. Use real, publicly available documents to investigate meaning-preserving readability improvements and decisions not to change text unnecessarily. Public documents are not ground-truth-labeled data. This is a preliminary evaluation added to existing artificial examples; effects have not been measured.

## Document Groups and Priorities

| Priority | Document group                                              | Issue / procedure                                                        | Status                                                                                             |
| -------- | ----------------------------------------------------------- | ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------- |
| P0       | Digital Agency (procedures, responsibilities, requirements) | #40, [group procedure](../../../docs/public-documents-digital-agency.md) | Sources collected. 11 candidates, 0 adopted (awaiting human review).                               |
| P0       | Python documents in Japanese                                | #41, [group procedure](../../../docs/public-documents-python.md)         | Sources collected. 18 candidates, 0 adopted (awaiting human review).                               |
| P0       | Kubernetes documents in Japanese                            | #42, [group procedure](../../../docs/public-documents-kubernetes.md)     | Sources collected. 25 candidates, 0 adopted (awaiting human review).                               |
| P0       | Aozora Bunko essays (supplementary group)                   | #39, [group procedure](../../../docs/public-documents-aozora.md)         | Sources collected. 21 candidates, 0 adopted (awaiting human review).                               |
| P1       | IPA OSS / OSPO materials                                    | #43, [group procedure](../../../docs/public-documents-ipa.md)            | Starter kit only collected (PDFs not collected). 18 candidates, 0 adopted (awaiting human review). |
| P1       | Skill improvements based on evaluation results              | #44                                                                      | After preparing this data.                                                                         |
| P0       | Calibration of automatic metrics such as Ragas              | #45                                                                      | Separate plan.                                                                                     |

Aozora Bunko is a supplementary group of literary and historical prose. Do not aggregate it with business and technical documents. Prioritize human review of context, preservation requirements, and comprehension questions over large-scale collection or a new evaluation platform.

## Shared Decisions

### 1. Track Work in a Manifest

Record sources, excerpts, preservation requirements, comprehension questions, and splits in one manifest, `evals/public-documents/manifest.json`, rather than keeping separate records for each document group. `tools/validate_public_corpus.py` checks its format (standard library only; no network or writes).

| Unit                                    | Required fields                                                                                                                                                                                                   |
| --------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Source (`sources[]`)                    | `group`, `title`, `provider`, `url`, `version` (release or commit), `format`, `retrieved_on`, original file's `raw_sha256`, and `lineage_id` (same value for prior versions, alternate formats, and translations) |
| Usage terms (`license`)                 | Separate terms for content (`body`) and bibliographic information (`bibliographic`), each with `name`, `url`, `checked_on`, and `redistribution`; content also has `attribution` and `modification_notice`        |
| Excerpt (`excerpts[]`)                  | `source_id`, `locator` (excerpt range), `correspondence` (who checked the match to the source and when), `text`, `text_sha256`, `transform_history`, `status`, and `split`                                        |
| Preservation requirement (`preserve[]`) | `kind`, quoted text in the excerpt (`quote`), `allowed_changes`, `confirmed_by`, and `reason`                                                                                                                     |
| Comprehension question (`questions[]`)  | Same fields as `comprehension_readability.py`. Reuse that tool's rules for validation.                                                                                                                            |

Do not store source files (PDF, Word, or HTML) in the repository. Identify them by retrieval source and SHA-256. Do not identify a version only by a mutable URL; retain a release, commit, or retrieval point in `version`.

- Include source text in the manifest only when the source content terms say `redistribution: allowed`. The validator rejects body text from other sources.
- Extract Word (docx), HTML, and Markdown in paragraph/block order with `tools/extract_docx_text.py`, `tools/extract_html_text.py`, and `tools/extract_markdown_text.py` (standard library only; automatic numbering in docx and emphasis in HTML are not restored). Use the paragraph identifier (P<連番>) for the excerpt `locator`.
- `transform_history` records each transformation from the source hash to the excerpt's `text_sha256` (extraction, ruby or note processing, range selection, etc.). Reject the record unless the first input matches `raw_sha256`, each stage's input matches the preceding output, and the last output matches `text_sha256`. Never overwrite source files.

Usage terms apply to the data. Do not substitute the repository's code license (`LICENSE`). Separate terms for the content and bibliographic information, and third-party quotations and figures. Do not adopt excerpts containing third-party content (`third_party_content: none`).

- For every adopted document, record attribution and modification notices in `attribution` and `modification_notice`. Do not present an edited text as an official document from its source.

### 2. Select Excerpts

- Initially select about 10 excerpts per document group from multiple independent source documents. This count is an operational starting point, not evidence of statistical adequacy.

Record candidates (`candidate`) in the manifest before viewing generated results. Retain counts and reasons for adoption (`adopted`) and exclusion (`excluded`, reason required). Do not select only convenient excerpts after seeing generated results.

Repair or exclude excerpts that are not self-contained, depend on surrounding context, or lose headings, tables, footnotes, or notes during extraction.

Include unchanged control examples in each group (`role: no_change_control`, with reason `no_change_reason`). Returning the source text unchanged is not a failure.

### 3. Split at the Source-Document Level

Separate `tuning` and `final` data by original source document. Keep chapters, excerpts, alternate formats, older versions, and translations with the same `lineage_id` on the same side. Reject identical text hashes that appear on both sides.

- Fix the split in the manifest before looking at model outputs. Where possible, also reduce author and series imbalance (the validator does not check this; a person must review it).

Do not use excerpts used for tuning in the final evaluation after skill revision (#44).

### 4. Do Not Treat the Source as the Only Correct Answer

Record claims, conditions, exceptions, agents, numbers, and sentence functions to preserve in `preserve`; record permitted changes in `allowed_changes`. Retain the reviewer and rationale for human comparison against the source. Do not include a preservation requirement in an adopted excerpt without a named reviewer. LLM judgments are supplementary and must not define preservation requirements or correct comprehension answers.

### 5. Separate Evaluation Tasks

| Category                     | Content                                                                                                         | Tool                                                        |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Automatic checks             | Differences in numbers, URLs, code, negation, conditions, etc. Do not count as a pass for meaning preservation. | `review_readability.py auto`, `compare_readability.py auto` |
| Human evaluation             | Meaning preservation, readability, and qualitative comments with quotes.                                        | `compare_readability.py`                                    |
| Comprehension questions      | Answer after reading only one candidate.                                                                        | `comprehension_readability.py`                              |
| LLM judgment (supplementary) | Scores and rationale from `--judge`; use for comparison with human judgments.                                   | `feedback_readability.py calibrate`                         |

Do not combine subjective ratings and actual comprehension in an overall score. Retain unrun, failed, undecidable, and missing cases by document group; do not treat them as passes.

### 6. Record Run Conditions

For each case, record `request`, `audience`, `provenance.model`, and `provenance.skill_version`. Add generation settings such as temperature to `provenance`. The assignment mapping is stored in `organizer.json` by the preparation tool. Public documents may be included in training data; treat this as unknown. Do not claim results apply to internal company documents.

## Integration with Existing Tools

Do not build a new evaluation platform. Match the existing input formats. The following constraints were found by inspecting actual input validation:

| Constraint                                                                                                                                                                             | Consequence                                                                                                                                                                                                                        |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `compare_readability.py` and `statistics_readability.py` count `document_id` as an independent document and assign repeated instances of the same `document_id` in the same direction. | Use the original source (`source_id`) for `document_id`. Do not treat multiple excerpts from one source as independent documents. The aggregation requested for #44 will be at the source-document level under this configuration. |
| `comprehension_readability.py` rejects duplicate `document_id` values (give one person the same text only once).                                                                       | Use the excerpt ID as `document_id` and include no more than one excerpt per source in a single assignment. Assign other excerpts from that source in separate sessions.                                                           |
| Comprehension-question aggregation is descriptive and has no interval estimates.                                                                                                       | Do not estimate effects or confidence intervals from comprehension questions (same caution as #44).                                                                                                                                |
| Anonymous comparison and comprehension questions are Mode B only.                                                                                                                      | Do not score fiction (Mode D) or modernization as Mode B (boundary from #39).                                                                                                                                                      |
| Review records are created from `organizer.json` produced by `compare_readability.py prepare`.                                                                                         | Convert to regression cases (`feedback_readability.py`) only after anonymous comparison.                                                                                                                                           |

`validate_public_corpus.py` checks these constraints using `--cases`.

## Procedure

1. Register each source as `planned` in the manifest. After retrieval, change it to `collected` and record version, retrieval date, `raw_sha256`, and usage terms.
2. Register excerpts as `candidate`, compare them with the source, then mark them `adopted` / `excluded`. Have a person verify preservation requirements and comprehension questions.
3. Validate the manifest.

   ```bash
   python3 tools/validate_public_corpus.py --manifest evals/public-documents/manifest.json
   # candidate を採用するまでに残る不備（人の確認）を一覧する
   python3 tools/validate_public_corpus.py --manifest evals/public-documents/manifest.json --readiness
   ```

4. Create `cases` JSON for the existing CLIs. Use the manifest's `text` unchanged as `original`. Before running, validate correspondence with the manifest and the split.

   ```bash
   # 比較・統計: document_id は原本
   python3 tools/validate_public_corpus.py --manifest evals/public-documents/manifest.json --cases cases.json --split tuning
   # 理解問題: document_id は抜粋ID
   python3 tools/validate_public_corpus.py --manifest evals/public-documents/manifest.json --cases comprehension.json --split tuning --document-id-by excerpt
   ```

5. Follow the procedure in the [text evaluation tools guide](../../../docs/human-evaluation.md).

Validator exit codes: `0=合格`, `1=台帳または cases に不備`, `2=入力を読めない`. The tool checks only format and consistency. A person verifies the meaning of preservation requirements, interpretation of usage terms, excerpt-to-source correspondence, and correct answers to comprehension questions.

## Out of Scope

Guaranteeing effects in internal business practice, autonomous skill updates, proving that a document was not used for training, and predicting an improvement rate in advance. The initial scope excludes NTT materials with nonprofit and inheritance conditions, the Japanese PostgreSQL edition with a notice about use in other media, and BCCWJ. Check their terms separately if they become necessary.

## Current Status

- A shared manifest format, validator, docx / HTML / Markdown extractors, and procedures for all five groups are ready.
- Digital Agency (#40): five source documents collected; 11 candidates and 6 exclusions recorded in the manifest. Preservation requirements and comprehension questions are drafts; **human review and adoption are both 0**. See the [group procedure](../../../docs/public-documents-digital-agency.md#状態2026-10-16-時点).
- Python (#41): four source pages collected; 18 candidates and 4 exclusions recorded. Zero adopted. See the [group procedure](../../../docs/public-documents-python.md).
- Kubernetes (#42): four source pages collected; 25 candidates and 5 exclusions recorded. Zero adopted. See the [group procedure](../../../docs/public-documents-kubernetes.md).
- Aozora Bunko (#39): five essay works collected; 21 candidates and 5 exclusions recorded. Zero adopted. See the [group procedure](../../../docs/public-documents-aozora.md).
- IPA (#43): nine Markdown files from the OSPO Starter Kit (CC0) collected; 18 candidates and 6 exclusions recorded. PDF materials have not been collected. Zero adopted. See the [group procedure](../../../docs/public-documents-ipa.md).
- Across all five groups, there are 93 candidates (Digital Agency 11, Python 18, Kubernetes 25, Aozora Bunko 21, IPA 18). Preservation requirements and comprehension questions are assistant drafts; none has been adopted after human review.
- Generation, evaluation, and automatic metrics (#45) have not been run. Effects are unmeasured.
