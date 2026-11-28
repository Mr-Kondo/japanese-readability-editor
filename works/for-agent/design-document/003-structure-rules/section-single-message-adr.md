---
status: accepted
date: 2026-11-11
decision-makers: User (approved defining four items before starting and the default five cycles), Claude Code (research and verification)
---

# Whether to add a rule that limits each section and subsection to one message (decision: not adopted)

Tracking: [Issue #158](https://github.com/Mr-Kondo/japanese-readability-editor/issues/158)

## Context

User proposal: Readability might improve if each level—part, chapter, section, subsection, and item—were limited to “one piece of content” (as with atomicity, one message per chunk).

This overlaps with existing rules.

| Existing location                        | Content                                                                                                                                |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| `readability-rules.md` §1, What to check | “Are multiple points mixed in one paragraph or section?”                                                                               |
| Same section, How to fix                 | “Separate paragraphs or sections by point.”                                                                                            |
| Same section, “Headings”                 | Can the content be understood from headings alone? Can the content be followed from headings and the first sentence of each paragraph? |
| Same document §2                         | Split long paragraphs only with line breaks at topic boundaries.                                                                       |
| `SKILL.md`, diagnostic order 1           | Check whether points are mixed and whether the content can be followed from headings and first sentences alone.                        |

Three aspects may be missing: (1) a concrete procedure for checking “what to verify” at the section level (whether the heading describes all paragraphs and whether the paragraphs address the same question); (2) how to handle a concluding phrase such as “both” after splitting; and (3) a safeguard against over-splitting at the section level (only over-fragmented paragraphs are currently identified as a problem).

## Prior research (with sources; all are hypotheses, not evidence of this skill's improvement rate)

Search conducted on 2026-11-11. Many sources are secondary, and some original texts were not checked.

| Area                               | Finding                                                                                                                                                                                                                                       | Source and confidence                                                                                                                                                                                                                                                                                              |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Paragraph writing                  | A paragraph discusses one topic and states it in an opening topic sentence. Chapter 4 of Takeo Kinoshita's _Rika-kei no sakubun gijutsu_ is a typical example.                                                                                | Confirmed in explanatory materials. **The book itself was not checked.**                                                                                                                                                                                                                                           |
| Experiments on headings            | Headings improve memory for a text's topic structure and incorporation of it into summaries. Effects on memory for facts are inconsistent. If only some topics have headings, topics without headings are more likely to be omitted.          | Bibliographic records and abstracts for Lorch et al. (2001) and Lorch, Lemarié, and Chen (2013) checked via the [University of Kentucky record](https://scholars.uky.edu/en/publications/signaling-topic-structure-via-headings-or-preview-sentences/). **Full texts not checked.**                                |
| Information mapping                | Horn's “chunking” is said to be based on Miller's 7±2, but that rationale is weak and has been criticized by Tufte and others.                                                                                                                | [Information Mapping (vendor)](https://informationmapping.com/blogs/news/writing-for-the-web-the-magical-number-seven-plus-minus-two), [Tufte](https://www.edwardtufte.com/notebook/the-magical-number-seven-plus-or-minus-two-not-relevant-for-design/). The “7±2” number is not adopted.                         |
| Minimalism and topic-based writing | Carroll's _Minimalism Beyond the Nurnberg Funnel_ influenced DITA's concept/task/reference idea of “small, self-contained units.”                                                                                                             | [Wikipedia](<https://en.wikipedia.org/wiki/Minimalism_(technical_communication)>), [Oxygen DITA guide](https://www.oxygenxml.com/dita/styleguide/Topics_and_Information_Types/c_How_Chunking_Works.html). Secondary sources. A technical-document “topic” is at a different granularity from this skill's section. |
| Harm from over-splitting           | No controlled experiments were found. Claims such as “a heading for every paragraph makes headings meaningless” and “wrong splits cause misreading” come from blogs, tool documentation, and literature on segmentation algorithms.           | Low confidence. **The harm is a hypothesis to be measured with this skill.**                                                                                                                                                                                                                                       |
| Japanese public-sector writing     | Long documents should have concise headings that state the point of each content group. The flow should be understandable from headings, which should correspond to the title. Put the conclusion first. Each sentence should have one point. | Confirmed from a search-result summary of the [Agency for Cultural Affairs' guidance on public-sector writing](https://www.bunka.go.jp/seisaku/bunkashingikai/kokugo/hokoku/pdf/93651301_01.pdf). **Relevant passages in the full text were not checked.** “One document, one purpose” was not found.              |

What can be inferred: “Keep one topic under each heading” is consistent with paragraph writing, heading research, and public-sector writing. However, this is **support for the idea**, not evidence that “LLM-revised output becomes easier to read.” The harm from over-splitting has also not been tested experimentally.

## Options and selection

| Option                    | Description                                                                                                                                                                                                         | Assessment                                                                                                                      |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| A. New numbered rule      | Create it separately from §1.                                                                                                                                                                                       | Overlaps with existing rules. `SKILL.md` is at its 175-line limit (`MAX_SKILL_LINES`), so no pointer can be added. Not adopted. |
| B. Strengthen existing §1 | Add a subsection under “Headings” covering “what to check,” “how to fix,” “avoid over-splitting,” and “when not to fix.” Leave `SKILL.md` unchanged, or change only wording on the same line as diagnostic order 1. | **Candidate. Decide whether to adopt based on the evaluation below.**                                                           |
| C. Do not adopt           | Existing rules are sufficient.                                                                                                                                                                                      | Conclusion if the existing version already meets the goal or the candidate is ineffective.                                      |

Do not add heading-level signals (character count and paragraph count per section) to `measure.py`. Mixing of points is a semantic issue and cannot be measured by a script. No labeled real documents are available to measure signal accuracy (not measured). Even if the candidate proves effective, handle this as a separate issue.

## Hypotheses

H1: Candidate version (option B) splits sections that mix points more often than the old version.
H2: It does not over-split or merge sections that already have one point.
H3: It follows heading requirements and Paragraph-only constraints as the old version does.
H4: Retention of meaning, numbers, and code does not worsen.

## Evaluation design

- Evaluation set: [11 self-authored cases](../../../../evals/section-single-message-cases.json). Sections that may be split (split: s01, s02, s03, and s11 as primary cases; s04 reported separately), controls not to split (s05, s06, s07), Paragraph-only (s08), fixed-heading requirement (s09), and judgment of new generation only (s10). Use the existing 12 controls to calibrate the meaning-retention evaluator.
- Old version: `355a42e` on main (v0.22.0). Candidate version: add a subsection to `readability-rules.md`. `SKILL.md` and `examples.md` remain identical.
- Generation: three runs per case per version; `sonnet / medium`, no tools, new context (same call as `tools/evaluate_readability.py`).
- Deterministic checks: number and wording of heading lines, equality after removing whitespace for Paragraph-only, and fixed-heading equality.
- Blind judgment: Only pairs where both versions pass meaning retention. Reverse left/right. Judge (a) whether each section is limited to one piece of content and its heading identifies it, and (b) whether the text is fragmented or over-split.
- Stages: Generate the old version first and check whether it already splits mixed sections (ceiling). If it is near the ceiling, do not generate the candidate and do not adopt it.

## Success criteria

Adopt the candidate only if all of the following hold.

1. Retention: All 33 candidate outputs pass meaning retention. Candidate fail and uncertain counts are no higher than the old version. All 12 evaluator calibration controls meet expectations. The actual model identifiers match.
2. Separation (H1): Among 12 outputs from the four primary split cases × three runs, the candidate has at least three more outputs with an increased number of heading lines than the old version.
3. Judgment (H1): The candidate wins more than the old version in pairwise “focus on one piece of content” judgments.
4. Over-splitting (H2): Among nine control outputs, at most one candidate output has more or fewer headings, and the count is no higher than the old version. The candidate does not lose more “fragmented” judgments than it wins.
5. Constraints (H3): Zero violations across the six candidate outputs for s08 and s09.

## Rollback criteria

- If the old version already adds headings in 11 or more of the 12 primary split outputs (ceiling), do not add the rule; do not adopt it (option C).
- If any criterion above is unmet, do not add the rule. If an H2 or H3 failure suggests a correction that narrows the rule or adds an over-splitting safeguard, conduct it as a separate experiment without overwriting this record (at most once).
- Worse meaning retention is grounds to stop even if other criteria improve.

## Limitations (stated in advance)

- The 11 self-authored cases are development inputs used to shape the design. They do not show generalization to unused documents. s04's handling of a concluding phrase uses an input shaped to match the candidate rule's example, so it is excluded from the primary tally.
- Evaluation uses the same model family (sonnet), with no human scoring. “Readability” is represented by changes in heading count and model comparisons; reader comprehension is not measured.
- Three repeated runs are not independent texts. Do not calculate general improvement or failure rates from the results.
- Product skill invocation (`--skill-dir`) and tool use are out of scope (the skill was pasted into the prompt).

## Results

**Decision: Option C (not adopted). Do not add the rule.** Details: [results](../../../../evals/section-single-message-result.md).

- The old version was not at ceiling (zero heading increases in 12 primary outputs across four cases), so the candidate was generated and compared.
- The candidate also had zero heading increases in the 12 primary outputs. Criterion 2 (at least three more) was not met.
- Meaning retention was 32 pass and 1 uncertain for both versions (both on s10). Criterion 1 requiring all candidate outputs to pass was not met.
- The candidate added headings for s04, whose input matched the rule's example; this revealed over-splitting and a shift in what the concluding phrase applied to.
- Pairwise judgment could not run because the reversed-side judgment was missing (`execution_failed`). It was not used as evidence for the decision.
- Do not add heading-level signals to `measure.py` (for the reasons above; because the candidate was not effective, there is no basis for assessing the signal's value).
- Leave the existing §1 rules “Are multiple points mixed?” and “Headings” unchanged.

To revisit this, explicitly request a redesign of the structure or run a separate experiment targeting Mode A.

## Review record

Codex (read-only) checked numerical consistency and whether not adopting the rule was justified. It raised two points, and both were adopted: (1) Because pairwise judgment was incomplete, changed criterion 4's status from “met” to “heading-count condition met; overall undetermined.” (2) Explicitly noted in the results that the ADR had not been pinned before execution.
