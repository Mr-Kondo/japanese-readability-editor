# Ragas 校正（人工ケース・構成ラベル）

> ラベルは構成によるもので人の確認前。実運用の成績ではない。件数が少なく、率は記述値。

- 呼出し: {'calls': 169, 'cache_hits': 38, 'failures': 0, 'seconds': 1031.3, 'cost_usd_list_price': 1.4601, 'calls_without_cost': 0}、モデル: claude-haiku-5-5, claude-sonnet-5-5

## 期待ラベル fail（8 件）
- factual の信号（precision/recall < 1）: 8/8（採点不能 0）
- rubric の信号（保持の観点のいずれか fail）: 8/8（採点不能 0）
- unnecessary_change が fail: 8/8
- 狙い撃ち（違反した観点が fail）: 8/8
- 1件あたり fail になった観点数: [3, 5, 6, 3, 4, 4, 5, 4]

## 期待ラベル pass（5 件）
- factual の信号（precision/recall < 1）: 1/5（採点不能 0）
- rubric の信号（保持の観点のいずれか fail）: 0/5（採点不能 0）
- unnecessary_change が fail: 0/5

## ケース別

| id | 期待 | 欠陥 | precision | recall | 保持で fail の観点 | 不要な変更 |
|---|---|---|---|---|---|---|
| control-s3a | pass | control_unchanged | 1.0 | 1.0 | — | pass |
| paraphrase-s3a | pass | legitimate_paraphrase | 1.0 | 1.0 | — | pass |
| number-s3a | fail | number_changed | 0.83 | 0.83 | condition_scope, numbers_order, ungrounded_specificity | fail |
| exception-drop-s3a | fail | exception_dropped | 1.0 | 0.67 | actor_target, condition_scope, modality_strength, negation_polarity, numbers_order | fail |
| negation-flip-s3b | fail | negation_flipped | 0.67 | 0.67 | actor_target, condition_scope, modality_strength, negation_polarity, numbers_order, ungrounded_specificity | fail |
| strength-s3b | fail | required_to_recommended | 0.67 | 1.0 | condition_scope, modality_strength, negation_polarity | fail |
| partial-negation-s5 | fail | partial_negation_to_full | 0.67 | 1.0 | actor_target, condition_scope, modality_strength, negation_polarity | fail |
| paraphrase-s5 | pass | legitimate_paraphrase | 1.0 | 1.0 | — | pass |
| tense-s5 | fail | frequency_and_tense_changed | 1.0 | 0.8 | condition_scope, modality_strength, numbers_order, ungrounded_specificity | fail |
| control-s6 | pass | control_unchanged | 1.0 | 1.0 | — | pass |
| ungrounded-s6 | fail | ungrounded_certainty_added | 0.4 | 1.0 | actor_target, condition_scope, modality_strength, numbers_order, ungrounded_specificity | fail |
| timing-swap-s6 | fail | timing_swapped | 0.5 | 0.4 | actor_target, condition_scope, modality_strength, numbers_order | fail |
| paraphrase-s6 | pass | legitimate_paraphrase | 0.75 | 1.0 | — | pass |
