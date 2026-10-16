# Ragas 校正（人工ケース・構成ラベル）

> ラベルは構成によるもので人の確認前。実運用の成績ではない。件数が少なく、率は記述値。

- 呼出し: {'calls': 238, 'cache_hits': 0, 'failures': 0, 'seconds': 1243.9, 'cost_usd_list_price': 2.0582, 'calls_without_cost': 0}、モデル: claude-sonnet-5-5

## 期待ラベル fail（23 件）
- factual の信号（precision/recall < 1）: 0/0（採点不能 23）
- rubric の信号（保持の観点のいずれか fail）: 23/23（採点不能 0）
- unnecessary_change が fail: 20/23
- 狙い撃ち（違反した観点が fail）: 22/23
- 1件あたり fail になった観点数: [5, 3, 3, 4, 1, 1, 2, 3, 2, 2, 1, 2, 3, 1, 2, 3, 1, 2, 1, 2, 3, 2, 1]

## 期待ラベル pass（11 件）
- factual の信号（precision/recall < 1）: 0/0（採点不能 11）
- rubric の信号（保持の観点のいずれか fail）: 0/11（採点不能 0）
- unnecessary_change が fail: 0/11

## ケース別

| id | 期待 | 欠陥 | precision | recall | 保持で fail の観点 | 不要な変更 |
|---|---|---|---|---|---|---|
| control-s3a | pass | control_unchanged | None | None | — | pass |
| exception-drop-s3a | fail | exception_dropped | None | None | actor_target, condition_scope, modality_strength, negation_polarity, numbers_order | fail |
| partial-negation-s5 | fail | partial_negation_to_full | None | None | condition_scope, modality_strength, negation_polarity | fail |
| control-s6 | pass | control_unchanged | None | None | — | pass |
| paraphrase-s6 | pass | legitimate_paraphrase | None | None | — | pass |
| paraphrase-s3a | pass | legitimate_paraphrase | None | None | — | pass |
| negation-flip-s3b | fail | negation_flipped | None | None | condition_scope, modality_strength, negation_polarity | fail |
| paraphrase-s5 | pass | legitimate_paraphrase | None | None | — | pass |
| ungrounded-s6 | fail | ungrounded_certainty_added | None | None | actor_target, condition_scope, modality_strength, ungrounded_specificity | fail |
| number-s3a | fail | number_changed | None | None | numbers_order | pass |
| strength-s3b | fail | required_to_recommended | None | None | modality_strength | fail |
| tense-s5 | fail | frequency_and_tense_changed | None | None | modality_strength, numbers_order | fail |
| timing-swap-s6 | fail | timing_swapped | None | None | actor_target, condition_scope, numbers_order | fail |
| hedge-s3a | fail | qualifier_added | None | None | condition_scope, modality_strength | fail |
| timing-s6 | fail | timing_shifted | None | None | condition_scope, numbers_order | fail |
| hedge-k8s | fail | default_hedged | None | None | condition_scope | pass |
| order-py | fail | order_lost | None | None | condition_scope, numbers_order | fail |
| tension-essay | fail | contrast_reversed | None | None | condition_scope, modality_strength, negation_polarity | fail |
| paraphrase-k8s | pass | legitimate_paraphrase | None | None | — | pass |
| paraphrase-essay | pass | legitimate_paraphrase | None | None | — | pass |
| necessity-s5 | fail | necessity_dropped | None | None | modality_strength | fail |
| quantifier-k8s | fail | quantifier_changed | None | None | condition_scope, ungrounded_specificity | fail |
| strength-py | fail | limit_and_strength_weakened | None | None | condition_scope, modality_strength, negation_polarity | fail |
| qualifier-essay | fail | subject_qualifier_dropped | None | None | condition_scope | fail |
| actor-org | fail | actor_swapped | None | None | actor_target, ungrounded_specificity | fail |
| paraphrase-py | pass | legitimate_paraphrase | None | None | — | pass |
| control-essay | pass | control_unchanged | None | None | — | pass |
| possibility-s6 | fail | possibility_to_certainty | None | None | modality_strength | fail |
| flag-dropped-k8s | fail | required_flag_dropped | None | None | actor_target, condition_scope | fail |
| only-py | fail | exclusivity_dropped | None | None | actor_target, condition_scope, negation_polarity | fail |
| hedge-essay | fail | hedge_removed | None | None | condition_scope, modality_strength | fail |
| strength-up-org | fail | recommendation_to_instruction | None | None | modality_strength | pass |
| paraphrase-org | pass | legitimate_paraphrase | None | None | — | pass |
| control-org | pass | control_unchanged | None | None | — | pass |
