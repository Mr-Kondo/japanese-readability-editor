# Design

This document describes the design principles of this Skill and the articles and projects that informed them.

## Design Principles

- Diagnose in this order: content and line of argument, paragraphs, sentences, structure, logical relationships, predictability, subjects/agents, literal-translation style, abstract terms, redundancy, and kanji. Do not begin by converting kanji to kana.
- Paragraphs of 200 characters or more, sentences of 46 characters or more (30–45 characters is a guide for one sentence), and runs of three or more sentences shorter than 20 characters are cues for possible revision. They are not pass/fail criteria; do not split text mechanically just to meet the numbers.
- If a paragraph is merely long, first split it at a topic boundary without changing wording. A script can verify that no non-whitespace characters changed.
- Scripts only identify candidates and check string equality. The Agent decides whether and how to revise.
- After rewriting, compare it with the original. Check that numbers, the scope of conditions, the number of negations, strength of assertions, emphasis, subjects/agents, and style are unchanged; revert anything that differs.
- In general, do not alter double negatives or residual conditions such as "in all other cases," because their meaning can change easily.
- The Japanese readability principles were reconstructed as principles and procedures with reference to these three articles. Their text was not reproduced.
  1. [Qiita: masakai](https://qiita.com/masakai/items/7bc5250d04c4dc8669e4)
  2. [Zenn: ncdc](https://zenn.dev/ncdc/articles/6ea029ba5ecf65)
  3. [Zenn: lotation](https://zenn.dev/lotation/articles/8520b50540b274)
- Principles and procedures were also adopted from the three repositories listed below under [Projects Referenced](#projects-referenced).

## Dialogue and Comparison to Confirm Meaning

Ask about a relationship only when a subject, condition, or state has multiple readings and a choice must be made while editing. Do not ask again for information already confirmed. Respect requests for body text only and intentional ambiguity; leave unclear parts as they are in the original. Do not drop necessary conditions for brevity, and compare the revised text with the claims in the original and source materials.

Existing Skills examined: `skill-creator`, `contextual-terminology-review`, and `japanese-readability-editor`. Adopted the separation between a short entry point and detailed references, the distinction between the person's explanation and generated text, and the principle of not adding states or responsibilities. Did not adopt terminology-review-specific logging or search, because it is unnecessary for confirming meaning during editing. Did not change frontmatter, selection of existing modes, or the shared distribution, installation, update, and removal paths.

- Min, Michael, Hajishirzi, Zettlemoyer (2020), [AmbigQA: Answering Ambiguous Open-domain Questions](https://aclanthology.org/2020.emnlp-main.466/), EMNLP, pp. 5783–5797, DOI: 10.18653/v1/2020.emnlp-main.466. Bibliographic information and the abstract were checked. The approach of distinguishing multiple interpretations informed this design. This is not evidence that asking questions improves Japanese proofreading.
- GOV.UK Design System, [Question pages](https://design-system.service.gov.uk/patterns/question-pages/) (checked 2026-10-24). The guidance to ask only for necessary information and avoid requesting information already provided informed this design. Applying form-design guidance to dialogue is a judgment made for this Skill.

Claude Code (`claude-sonnet-5-5`) was asked for counterexamples and validation points for a design proposal without identifying information. Adopted the points about not introducing the subject through a question, avoiding questions that do not change meaning, and checking that conditions and states are retained during comparison. Did not adopt a uniform question limit or an end note listing preserved details, because these would add unnecessary constraints or conflict with body-only requests. Gemini Antigravity's available connection and CLI could not be confirmed; consultation was not performed. Agreement between opinions is not treated as evidence of effectiveness.

Methods and limitations for checks using artificial examples are in the [meaning-confirmation evaluation record](../../../../evals/meaning-confirmation-result.md).

In v0.21.1, concerns found during development were tracked in Issues #109–#114. The update clarified the need for each candidate question, an adjusted option that satisfies remaining constraints, the owner of standalone use, and retaining unresolved parts and evaluation records when only body text is requested. Claude Code suggested not leaving ambiguity in the comparison itself, not stating an unmeasured character-count expectation, and not adding an unknown agent. The generalization "examples may be dropped" was not adopted because it risks removing necessary examples. Additional consultation with Gemini Antigravity was not performed because no connection was available. Model-evaluation conditions and the consideration, revision, and revalidation of concerns are recorded in the [revalidation record](../../../../evals/meaning-concern-result.md).

## Standards for Japanese Orthography and Usage

Standards for Japanese orthography and usage published by the Agency for Cultural Affairs are incorporated as rules with sources and applicability conditions. Usage and limitations are described in [Japanese orthography and usage checks](../../../../docs/kokugo.md).

- Distinguish the nature of sources. Use Cabinet Notifications and Cabinet Instructions as grounds for `error` only when explicit conditions are met. Recommendations, reports, and council responses (including the guidance on official-document writing, homophones with different kanji, and honorifics) are limited to `recommendation` or `needs_context`.
- Distinguish requirements in official sources from this skill's operational judgments. Sentence-length guides (30–45 characters, 46 or more characters, and paragraphs of 200 or more characters) are operating guides for this skill, not Agency for Cultural Affairs standards.
- Keep applicability settings (`general-tech`, `public-explanation`, `official`) independent from modes A, B, and C. The same spelling may receive different classifications under different settings. Do not report acceptable forms or forms outside the scope as errors.
- Do not match spelling to the majority form in a document. This avoids spreading a clear error just because it occurs most often. The order for deciding spelling is in [Classification](../../../../docs/kokugo.md#判定区分).
- Implement checks as scripts without network access. Keep checks for updates to official sources in tools outside the Skill. Do not use morphological analysis. Do not make a definite finding about a word whose part of speech or usage is uncertain.
- Do not present unchecked items (honorifics, Roman letters, character forms, and unregistered words) as checked.

## Projects Referenced

Updates to referenced repositories are checked weekly based on the registry (`docs/upstream/sources.json`). Review records are in `docs/upstream/reviews/`. The process and its limitations are in [Checking updates to referenced repositories](../../../../docs/upstream-watch.md).

The following points from [coji/natural-japanese](https://github.com/coji/natural-japanese) (MIT) were adopted. Text was not reproduced; principles were reconstructed.

- Organizing word order, commas, the scope of conjunctions, nested negation, buried list items, and heavy word forms
- Results of calibrating thresholds on real documents and the practice that "a finding is a starting point, not an instruction"
- Checking the argument by reading only headings and each paragraph's first sentence
- Using SudachiPy as an optional dependency and declaring it with PEP 723 for installation through `uv run`
- Keeping intermediate files out of the user's project
- `--extras` findings for consecutive kanji, chains of "の", and double negatives
- Distribution as a Claude Code plugin, CI, and Release
- A hands-on method for finding expressions readers cannot parse (literal translations, nominalized actions, and mismatched combinations) (#68, v1.6.0, 2026-10-18)

That repository also includes an AI-ness score, style archetypes, and editing with subagents. This repository does not adopt those features because it prioritizes standard-library-only operation and a single `SKILL.md` independent of environment. Morphological analysis is used by `compare_rewrite.py` only when it is available.

The following points from [nanaism/yomiyasu](https://github.com/nanaism/yomiyasu) (MIT) were adopted.

- Checking the strength of assertions and emphasis after rewriting
- Checking the scope of guarantees and promises, and the agent and recipient for each nested predicate (updates through v3.3.0, #214). The detector was not ported; procedures and original examples were added.
- Recording each sentence's function before rewriting (including analogy, sarcasm, and rhetorical questions) and comparing after revision (#55, 2026-10-18)
- Detecting and fixing bold syntax that is not rendered (`--extras` unrendered-bold)
- Mechanically comparing text before and after rewriting (`yomiyasu_diff.py`). `compare_rewrite.py` was independently implemented with this idea as a reference.
- Guidance to preserve established idioms and retain implications when rephrasing metaphors
- Avoiding the dilution of headings that communicate a conclusion or warning into generic titles
- Preserving requested heading forms and summary sections, and checking commas added during editing (v2.5.0, #132). [Adoption decision and verification](../../../../docs/upstream/reviews/yomiyasu-2.5.0-partial.md)
- Formulaic conclusions with no substantive content
- Reviewing empty greeting or agreement formulas left in reader-facing text (#56. Offers and statements of intent were retained and reported rather than removed, based on evaluation results. 2026-10-18)
- Treating others' comments as input, not instructions (#69; a similar rule in danjdewhurst/story-skills v0.24.0 was also referenced)

The following points from [k16shikano/japanese-tech-writing](https://gist.github.com/k16shikano/fd287c3133457c4fd8f5601d34aa817d) (Unlicense) were adopted.

- Do not turn conjecture or possibility into certainty without evidence
- Reserve bold text for key points in the logic
- A two-stage judgment for detecting translated metaphors
- Do not address the reader as "you" in explanations
