# Implementation Proposal and Additional Research for Fixing the Over-Concretization Example

## Context and Status

2026-10-16. The target is a contradiction remaining under “万能動詞” (“all-purpose verbs”) in `references/readability-rules.md`. Baseline: v0.8.0 (`69188f6`); working branch: `codex/fix-concretization-example`. The following research and design were prepared before implementation. At the user's later direction, the fix and comparative evaluation were completed. The [results](../../../evals/concretization-result.md) distinguish removal of the instruction contradiction from the effect on quality, which remained unresolved. Additional research retained the proposal to check evidence before rewriting, and added separate checks for information added or omitted after a change and separation of evaluation axes.

## Evidence and Hypothesis About the Cause

- “万能動詞” in the baseline [reference document](https://github.com/Mr-Kondo/japanese-readability-editor/blob/69188f6fc505ae44b64187a03cd29eb4713aa69c/skills/japanese-readability-editor/references/readability-rules.md) says 「再試行が安定性に効く」 can be expanded to 「通信が失敗しても再試行するため、一時的な障害でジョブが止まらない」. This adds a communication target, failure/outage conditions, and a guarantee of no stoppage that are absent from the source.
- The preceding check also asks only whether “what is done” and “what changes as a result” are present. This section says nothing about what to do when evidence is insufficient.
- The [shared instructions](../../../skills/japanese-readability-editor/SKILL.md) say to preserve the original predicate when its meaning is conveyed, and not to change the type or strength of the evaluation merely because it is abstract.
- [Example 7 in the examples](../../../skills/japanese-readability-editor/assets/examples.md) has already been revised to retain “supports” and “increases” without narrowing the target to communication or jobs. It shows changes to similar guarantees as errors.

The statements above are facts observed in the pre-implementation files. The possibility that a local example takes precedence over shared instructions and induces concretization without evidence is a hypothesis. The completed comparison changed the procedure and example together; it does not establish that this example alone caused prior model failures.

## Decisions Informed by External Sources

I reviewed the current [yomiyasu instructions](https://github.com/nanaism/yomiyasu/blob/main/skills/yomiyasu/SKILL.md) on clarifying subject/object relationships, concretizing figurative verbs, and avoiding information addition. When fixing subject-predicate relationships, first preserve the source verb; if a natural paraphrase cannot preserve meaning, leave it unchanged. Also do not replace a vague term with a narrower fact, and treat supplied materials as evidence. Apply this judgment to the target section.

Use the [explanatory article](https://zenn.dev/algoartis/articles/0b1c731881b25c) as background. The proposed revision is grounded in consistency with the instruction text above, the shared instructions here, and revised Example 7. The existence of instructions in another skill is not itself evidence of improved effects.

## Additional Sources Reviewed and Adoption Decisions

The search covered public Japanese proofreading skills, technical-writing linters, public-sector writing guidance, and research on style transfer and model evaluation. The following are representative primary sources checked on 2026-10-16, not an exhaustive literature review. Public skills were read as instruction text; they were not installed or tested for effectiveness. GitHub links point to mutable branches such as `main`, so record commit and license if their content is incorporated in later implementation.

| Source                                                                                                                                                                                                                                                                                                                                           | What was verified                                                                                                                                             | Use here and limitations                                                                                                                                                                                                                                                             |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [geonwoo-jeong/japanese-humanizer: SKILL.md](https://github.com/geonwoo-jeong/japanese-humanizer/blob/main/plugins/japanese-humanizer/skills/japanese-humanizer/SKILL.md), [audit procedure](https://github.com/geonwoo-jeong/japanese-humanizer/blob/main/plugins/japanese-humanizer/skills/japanese-humanizer/references/revision-playbook.md) | Distinguishes priorities for surface edits, contextual judgment, and higher-order judgment; audits factuality, expertise, clarification, and false positives. | Consider adopting its distinction between simple wording cleanup and concretization that changes a target or guarantee. Do not import its priority scores or full output format. The existence of instructions is not evidence of effectiveness.                                     |
| [coji/natural-japanese: SKILL.md](https://github.com/coji/natural-japanese/blob/main/skills/natural-japanese/SKILL.md)                                                                                                                                                                                                                           | Separates detection from contextual judgment and emphasizes planning the audience, main message, and structure before drafting.                               | Reuse structural checks already adopted. Do not introduce its naturalness scores, additional convergence loop, or parallel-review mechanism here.                                                                                                                                    |
| [blader/humanizer: SKILL.md](https://github.com/blader/humanizer/blob/main/SKILL.md)                                                                                                                                                                                                                                                             | Categorizes unnecessary contrast, repeated conclusions, exaggeration, and ornamentation; rechecks added and omitted information after revision.               | Use the idea of judging a phrase by its role in the text rather than word counts. Do not directly transfer permission to add reactions based on voice, blanket dash restrictions, or individual conversion examples to this meaning-preservation policy. It is designed for English. |
| [textlint-rule-preset-ja-technical-writing: README](https://github.com/textlint-ja/textlint-rule-preset-ja-technical-writing)                                                                                                                                                                                                                    | Detects sentence length, particles, double negatives, style, and other issues. Defaults are strict and allow for document-specific tuning and exceptions.     | Supports treating detections as suggestions rather than editing commands. This linter cannot verify identity of target, causality, or guarantee; add no dependency.                                                                                                                  |
| Agency for Cultural Affairs, [public-document writing guidance announcement](https://www.bunka.go.jp/koho_hodo_oshirase/hodohappyo/93650001.html)                                                                                                                                                                                                | Distinguishes document types and accepts reader-focused plain language for public relations and similar materials.                                            | Use as background for audience-dependent judgment. Do not use it as evidence for identifying AI-written text or proofreading-model performance. Only the official announcement page was reviewed, not the full guidance.                                                             |
| [Mir et al., 2019, Evaluating Style Transfer for Text](https://aclanthology.org/N19-1049/)                                                                                                                                                                                                                                                       | Treats style-transfer strength, content preservation, and naturalness as distinct criteria and discusses their trade-offs.                                    | Grounds separate judgments of meaning preservation, improvement to unnatural phrasing, and natural flow. The study uses Yelp sentiment transfer; effects on Japanese technical writing require separate verification.                                                                |
| [Babakov et al., 2022, A large-scale computational study of content preservation measures](https://aclanthology.org/2022.acl-srw.23/)                                                                                                                                                                                                            | Compares content-preservation measures and proposes MIS based on mutual entailment.                                                                           | Consider checking information additions and omissions in both directions. This procedure is not an MIS implementation or reproduction study. No Japanese automatic-entailment model is added.                                                                                        |
| [Wang et al., 2024, Large Language Models are not Fair Evaluators](https://aclanthology.org/2024.acl-long.511/)                                                                                                                                                                                                                                  | Reports position bias in model ratings, where candidate order changes rankings.                                                                               | Reflect in the proposal by hiding version names, scoring the same pair with sides reversed, and retaining inconsistent judgments as undecided. This alone will not remove every rating bias.                                                                                         |

For the papers, only ACL Anthology bibliographic information and abstracts were checked; experiments were not reproduced and full papers were not reviewed in depth. The “use here” column presents design judgments derived from the sources; it does not mean the papers demonstrated the effectiveness of this skill.

### Method Derived from the Additional Research

Keep the adopted candidate to the following small check. Do not build a new editing engine or composite score.

1. Before editing, identify which target, condition, result, or evaluation is established by the source or materials.
2. After editing, check whether the input supports any new concrete claim in the output. If no corresponding evidence exists, remove it as an addition.
3. Conversely, check whether claims, conditions, and caveats from the source remain in the output. Checking only for contradictions can miss omission or generalization.

Materials may help resolve ambiguity in the source, but do not add every detail found in the materials. Use a qualification only when it is established that it applies to the source as well. Check semantic correspondence, not identical word occurrence. This is a human- or model-assisted comparison, not an automatic proof.

## Options

| Option                                                          | Benefit                                                                                              | Remaining issue / opportunity cost                                                                                 | Decision                     |
| --------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------- |
| Delete only the erroneous example                               | Removes the contradiction with the smallest change.                                                  | The procedure could still be read as requiring a concrete result.                                                  | Insufficient.                |
| Start the procedure by checking evidence and refer to Example 7 | Distinguishes cases with sufficient evidence from those without it, and reduces duplicated examples. | Requires a short explanation and behavior check.                                                                   | Recommended.                 |
| Add prohibited words, automatic replacements, or a new detector | Mechanically finds candidate expressions.                                                            | Word matches cannot determine whether “works” is suitable or whether a guarantee changed; maintenance scope grows. | Not adopted for this change. |

## Recommended Change Proposal

The first implementation should replace only the check procedure and example under “万能動詞” in `skills/japanese-readability-editor/references/readability-rules.md` with the following:

```text
確認の手順:

1. 何が何にどう関わるかを読み取り、元の述語で意味が伝わるか確かめる。伝わるなら残す。
2. 読み取りにくい場合は、対象・条件・動作・結果のうち原文・提供資料から確定できるものを確認し、同じ範囲・評価の強さで言い直す。資料の限定を原文にも適用できるか確かめ、書かれていない動作や結果を補わない。
3. 根拠が足りなければ、その表現を残す。確認が必要で利用者に尋ねられる場合は、何を指すかを確かめる。本文だけを求められた場合は、質問や編集用の注記を本文へ足さない。
4. 言い直した主張に原文・資料の根拠があるかと、原文の主張・条件・留保が残っているかを確かめる。同じ意味と確認できない部分は戻す。

「再試行が安定性に効く」だけでは、何を再試行するかや、失敗後にどう動くかは分からない。この一文だけを根拠に、通信やジョブへ対象を限定したり、「止まらない」と保証したりしない。原文の表現を残し、ほかに直せる箇所を整える。名詞の展開と評価の保持は、assets/examples.md の例7を参照する。
```

During implementation, make the Example 7 reference a Markdown link to `../assets/examples.md`. Do not mechanically replace “works” with “contributes” or “helps” either. That may not resolve abstraction and can change the evaluation's meaning.

The objection “leaving the source unchanged does not reduce AI-sounding prose” is valid. Therefore, do not prohibit concretization when evidence supports it; permit revisions that preserve the same meaning. However, an output that retains an unsupported phrase may pass meaning preservation but must not count as a successful improvement in expression.

## Change Scope and Downstream Effects

- Limit the normative-source change to the section above. The shared `SKILL.md` and Example 7 already express the same judgment; do not add duplicative prohibitions.
- When behavior evaluation is performed, add development inputs, rating criteria, and results under `evals/` and link them from `evals/README.md`. Do not change historical run records.
- Generate distributions from the source of truth using `tools/package.py`. Verify propagation to ZIP, Gemini Apps, OpenCode, and Hermes by regenerating; do not edit `dist/` by hand.
- Do not change APIs, configuration, dependencies, or existing CLIs. This research searched the source of truth, tests, and packaging tool for the target expression and found no identical affirmative example elsewhere. Keep the erroneous example in Example 7 as a contrast case.

## Verification Proposal and Decision Criteria

Priority 1 is instruction consistency. Review the diff to ensure it adds no target, condition, or strength of evaluation. Testing for matching prohibition phrases alone does not verify meaning preservation.

Priority 2 is a small comparison using six inputs. These are regression checks based on this analysis, not evidence of generalization to unused documents.

| Input type                                                                                            | Count | Check                                                                                             |
| ----------------------------------------------------------------------------------------------------- | ----: | ------------------------------------------------------------------------------------------------- |
| Abstract statements with unknown target/result (retrying and an example from another field)           |     2 | Do not invent target, condition, or guarantee.                                                    |
| Abstract statements of similar degree with materials that state action, result, and failure condition |     2 | Organize available information within its supported scope; retain failure conditions and caveats. |
| Natural abstract evaluation and literal technical action description                                  |     2 | Do not revise solely because of abstract wording or an inanimate subject.                         |

Pair the two inputs with unknown information and the two with evidence so the same source has one case without supporting material and one with it. Check both that the model does not invent in the former and that it does not leave known relationships vague in the latter. Even where materials exist, do not require unnecessary additions or mechanical full rewrites.

Generate baseline and candidate versions with the same model, reasoning settings, and inputs, three times each, one input per separate context (36 outputs total). Save inputs, skill text, hashes, and actual model identifiers. Use the [existing comparison procedure](../../../evals/readability-comparison.md) to score meaning preservation first. State added and lost claims separately in rating rationales. In addition to existing rating audits, mix in a hidden gold example where an evaluation of usefulness is changed to a guarantee of no stoppage, and a meaning-preserving paraphrase with different natural wording. Use them to check missed guarantees and overreaction to wording.

Compare the following two axes separately, and only for pairs where both versions pass meaning preservation:

- Improvement to expression: identify exactly where ambiguous subject-predicate relationships, unsupported exaggeration, empty previews, or repetition decreased.
- Naturalness: judge whether word combinations and sentence flow are natural, and whether readability problems remain after substitution with another abstract term or formulaic phrase.

Hide version names, randomize left/right assignment, and score the same pair again with sides reversed. If the outcome is inconsistent after reversal, retain it as undecided. Do not hide meaning-preservation failures from the full denominator; also report how many pairs were excluded from expression comparison. Retaining the source can pass meaning preservation, but alone does not count as a win for improvement in expression. Do not decide winners by prohibited-word counts or ending types, and do not offset a meaning-preservation failure with a composite score. State the limit if no independent human review was performed.

`tools/evaluate_readability.py` can generate and score meaning preservation for a single version on a specified suite. However, it does not implement before/after comparison or expression-improvement scoring, so the tool alone does not complete the comparison. For this scale, use existing prompts and record formats; decide separately whether to add general-purpose comparison features.

Defer any conclusion of behavioral improvement if the candidate has a meaning-preservation `fail` or `uncertain`, omissions, a mismatch in actual model, or errors on the rating audit. Count baseline failures without hiding them, but do not fail the candidate solely because of a baseline failure. Also defer if expression comparisons remain undecided. Even if the candidate passes meaning preservation on every case, report only removal of the instruction contradiction if expression-improvement wins do not outnumber losses or if naturalness has more losses than wins. These small-sample criteria are design judgments for this work, not statistical guarantees from the cited papers. Do not claim measured effectiveness or absence of failures on other text.

Priority 3 is structural validation, tests, and distribution generation after implementation. Run `python3 tools/check_all.py` and `python3 tools/package.py` and verify the distributed files. Model evaluation uses external communication and usage quota, so do it after review of instruction consistency. These steps were unrun at design time, but have since been completed as reported in the [results](../../../evals/concretization-result.md).

## Limits

This proposal is not expected to resolve shifts from policy to request or from chronology to causality in the earlier long text. Those remain separate failures. Confidence is high that the instruction contradiction existed, but the output-improvement effect of this local fix remained unresolved in the completed comparison.
