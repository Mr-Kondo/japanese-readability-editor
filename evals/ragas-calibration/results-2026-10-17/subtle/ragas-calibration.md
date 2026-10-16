# Ragas 校正（人工ケース・構成ラベル）

> ラベルは構成によるもので人の確認前。実運用の成績ではない。件数が少なく、率は記述値。

- 呼出し: {'calls': 272, 'cache_hits': 46, 'failures': 1, 'seconds': 1263.7, 'cost_usd_list_price': 2.1234, 'calls_without_cost': 0}、モデル: claude-sonnet-5-5

## 期待ラベル fail（15 件）
- factual の信号（precision/recall < 1）: 7/15（採点不能 0）
- rubric の信号（保持の観点のいずれか fail）: 15/15（採点不能 0）
- unnecessary_change が fail: 15/15
- 狙い撃ち（違反した観点が fail）: 15/15
- 1件あたり fail になった観点数: [6, 3, 3, 3, 5, 3, 3, 3, 3, 3, 3, 4, 4, 3, 1]

## 期待ラベル pass（6 件）
- factual の信号（precision/recall < 1）: 0/5（採点不能 1）
- rubric の信号（保持の観点のいずれか fail）: 0/6（採点不能 0）
- unnecessary_change が fail: 0/6

## ケース別

| id | 期待 | 欠陥 | precision | recall | 保持で fail の観点 | 不要な変更 |
|---|---|---|---|---|---|---|
| hedge-s3a | fail | qualifier_added | 1.0 | 1.0 | actor_target, condition_scope, modality_strength, negation_polarity, numbers_order, ungrounded_specificity | fail |
| timing-s6 | fail | timing_shifted | 1.0 | 1.0 | condition_scope, numbers_order, ungrounded_specificity | fail |
| hedge-k8s | fail | default_hedged | 1.0 | 1.0 | condition_scope, modality_strength, ungrounded_specificity | fail |
| order-py | fail | order_lost | 1.0 | 1.0 | actor_target, condition_scope, numbers_order | fail |
| tension-essay | fail | contrast_reversed | 0.5 | 0.4 | actor_target, condition_scope, modality_strength, negation_polarity, ungrounded_specificity | fail |
| paraphrase-k8s | pass | legitimate_paraphrase | 1.0 | None | — | pass |
| paraphrase-essay | pass | legitimate_paraphrase | 1.0 | 1.0 | — | pass |
| necessity-s5 | fail | necessity_dropped | 1.0 | 1.0 | condition_scope, modality_strength, negation_polarity | fail |
| quantifier-k8s | fail | quantifier_changed | 1.0 | 0.8 | actor_target, condition_scope, ungrounded_specificity | fail |
| strength-py | fail | limit_and_strength_weakened | 1.0 | 1.0 | condition_scope, modality_strength, negation_polarity | fail |
| qualifier-essay | fail | subject_qualifier_dropped | 0.83 | 0.71 | actor_target, condition_scope, negation_polarity | fail |
| actor-org | fail | actor_swapped | 0.87 | 0.87 | actor_target, condition_scope, ungrounded_specificity | fail |
| paraphrase-py | pass | legitimate_paraphrase | 1.0 | 1.0 | — | pass |
| control-essay | pass | control_unchanged | 1.0 | 1.0 | — | pass |
| possibility-s6 | fail | possibility_to_certainty | 0.75 | 1.0 | condition_scope, modality_strength, ungrounded_specificity | fail |
| flag-dropped-k8s | fail | required_flag_dropped | 1.0 | 0.6 | actor_target, condition_scope, modality_strength, negation_polarity | fail |
| only-py | fail | exclusivity_dropped | 1.0 | 0.8 | actor_target, condition_scope, negation_polarity, ungrounded_specificity | fail |
| hedge-essay | fail | hedge_removed | 1.0 | 1.0 | condition_scope, modality_strength, numbers_order | fail |
| strength-up-org | fail | recommendation_to_instruction | 1.0 | 1.0 | modality_strength | fail |
| paraphrase-org | pass | legitimate_paraphrase | 1.0 | 1.0 | — | pass |
| control-org | pass | control_unchanged | 1.0 | 1.0 | — | pass |
