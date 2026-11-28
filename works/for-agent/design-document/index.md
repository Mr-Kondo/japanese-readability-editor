# Design Decision Index

## Pre-translation OPQ Provenance

Baseline commit: `07b5c6dd68f12b745d3a5a6e5b177c6c28696498`.
These links preserve the Japanese bodies before translation.
They do not establish the earlier evaluation-time ADR versions.

| Japanese original                                                                                                                                                                                    | SHA-256                                                            |
| ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [opq-analysis-adr.md](https://github.com/Mr-Kondo/japanese-readability-editor/blob/07b5c6dd68f12b745d3a5a6e5b177c6c28696498/works/for-agent/design-document/003-structure-rules/opq-analysis-adr.md) | `4bfee46da6a3da7c3bf50597bf31bc67153d5c5c4645d8d1da04da5f15c3b283` |
| [opq-reeval-adr.md](https://github.com/Mr-Kondo/japanese-readability-editor/blob/07b5c6dd68f12b745d3a5a6e5b177c6c28696498/works/for-agent/design-document/003-structure-rules/opq-reeval-adr.md)     | `b68792fba170fe30878228152b0a16c03d73f26272f3a9fac30f8d88e9665aa3` |

These baseline hashes already differ from historical `adr_sha256` values in OPQ `run.json` files.
Translation does not create that mismatch. Historical records remain unchanged.
The runners' `check_frozen()` functions compare runner and helper hashes, not ADR hashes.
The existing `prepare()` limitation and old `adr/` paths remain unchanged.

## Numbered Folders

| Number | Name                   | Contents                                                                      |
| ------ | ---------------------- | ----------------------------------------------------------------------------- |
| 001    | knowledge-index        | Pilot plan and conclusion for reusing development findings in later updates   |
| 002    | installer              | Removal of `install.py` and `uninstall.py`                                    |
| 003    | structure-rules        | Evaluations of OPQ and the single-message-per-section rule                    |
| 004    | human-review-tooling   | Design survey and integration policy for human evaluation of Japanese writing |
| 005    | readability-principles | Japanese readability principles and the articles and projects consulted       |
| 006    | fiction-mode           | Design references and limitations for fiction mode                            |

## Architecture Decision Records

Find historical decisions by topic. An ADR's `status` describes the record itself.
The Decision column states whether the proposal was adopted.

| Date       | ADR                                                                                        | `status`     | Decision                                                                                                                                                                |
| ---------- | ------------------------------------------------------------------------------------------ | ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-11-11 | [OPQ reevaluation, experiment 3](003-structure-rules/opq-reeval-adr.md)                    | `accepted`   | Not adopted. Leading conclusions improved under grading that allowed reordering, but the zero-violation criterion was not met.                                          |
| 2026-11-11 | [OPQ leading conclusions, experiments 1 and 2](003-structure-rules/opq-analysis-adr.md)    | `accepted`   | Not adopted. Leading conclusions increased, but meaning preservation failed the criterion. See [experiment 3](003-structure-rules/opq-reeval-adr.md) for the follow-up. |
| 2026-11-11 | [One message per section or subsection](003-structure-rules/section-single-message-adr.md) | `accepted`   | Not adopted. Heading splits did not improve in the primary cases. The candidate failed to preserve meaning in every case.                                               |
| 2026-11-10 | [Installer removal](002-installer/remove-install-py-adr.md)                                | `accepted`   | Removed `install.py` and `uninstall.py`. Use `npx skills add` by default; retain manual-copy instructions for some destinations.                                        |
| 2026-11-02 | [Knowledge-index pilot conclusion](001-knowledge-index/conclude-pilot-adr.md)              | `accepted`   | Retain the prototype index for manual reference. Do not connect it automatically to improvement proposals.                                                              |
| 2026-11-02 | [Knowledge-index pilot plan](001-knowledge-index/pilot-plan-adr.md)                        | `superseded` | Planned a small set of pages recording skill-update findings. See the [conclusion ADR](001-knowledge-index/conclude-pilot-adr.md) for the final decision.               |

Update this table when adding an ADR or changing its status or successor.

The English OPQ ADRs correct relative links for their current location.
Their pinned Japanese originals retain the historical relative links.

The runners in `evals/opq-run`, `opq2-run`, and `opq3-run` remain unchanged.
Their recorded `run.json` files check runner hashes.
The `prepare()` functions still read the old `adr/` paths.
These experiments are complete; rerunning `prepare()` is not expected.
For reproduction, supply the ADR at its historical path or create a new record.

The plan `evals/no-skill-comparison.md` is also unchanged.
Its `plan_sha256` is frozen in `evals/no-skill-run/run.json`.
Its `docs/design.md` reference uses the old path.
The current location is `005-readability-principles/design-principles-document.md`.

## Other Japanese Originals

All links use the same 40-character baseline commit as the OPQ snapshots above.
Retrieve a file through its immutable link or `git show <commit>:<path>`.

| Document                         | Japanese original                                                                                                                                                                                          |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Knowledge-index pilot plan       | [Original](https://github.com/Mr-Kondo/japanese-readability-editor/blob/07b5c6dd68f12b745d3a5a6e5b177c6c28696498/works/for-agent/design-document/001-knowledge-index/pilot-plan-adr.md)                    |
| Knowledge-index pilot conclusion | [Original](https://github.com/Mr-Kondo/japanese-readability-editor/blob/07b5c6dd68f12b745d3a5a6e5b177c6c28696498/works/for-agent/design-document/001-knowledge-index/conclude-pilot-adr.md)                |
| Installer removal                | [Original](https://github.com/Mr-Kondo/japanese-readability-editor/blob/07b5c6dd68f12b745d3a5a6e5b177c6c28696498/works/for-agent/design-document/002-installer/remove-install-py-adr.md)                   |
| Single-message sections          | [Original](https://github.com/Mr-Kondo/japanese-readability-editor/blob/07b5c6dd68f12b745d3a5a6e5b177c6c28696498/works/for-agent/design-document/003-structure-rules/section-single-message-adr.md)        |
| Human-review design survey       | [Original](https://github.com/Mr-Kondo/japanese-readability-editor/blob/07b5c6dd68f12b745d3a5a6e5b177c6c28696498/works/for-agent/design-document/004-human-review-tooling/design-survey-document.md)       |
| Human-review integration         | [Original](https://github.com/Mr-Kondo/japanese-readability-editor/blob/07b5c6dd68f12b745d3a5a6e5b177c6c28696498/works/for-agent/design-document/004-human-review-tooling/integration-document.md)         |
| Readability principles           | [Original](https://github.com/Mr-Kondo/japanese-readability-editor/blob/07b5c6dd68f12b745d3a5a6e5b177c6c28696498/works/for-agent/design-document/005-readability-principles/design-principles-document.md) |
| Fiction references               | [Original](https://github.com/Mr-Kondo/japanese-readability-editor/blob/07b5c6dd68f12b745d3a5a6e5b177c6c28696498/works/for-agent/design-document/006-fiction-mode/design-references-document.md)           |
