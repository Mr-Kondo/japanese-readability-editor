# Ragas 校正（人工ケース・構成ラベル）

> ラベルは構成によるもので人の確認前。実運用の成績ではない。件数が少なく、率は記述値。

- 呼出し: {'calls': 204, 'cache_hits': 82, 'failures': 0, 'seconds': 611.7, 'cost_usd_list_price': 1.2274, 'calls_without_cost': 0}、モデル: claude-sonnet-5-5

## 期待ラベル fail（23 件）
- factual の信号（precision/recall < 1）: 19/23（採点不能 0）
- rubric の信号（保持の観点のいずれか fail）: 0/0（採点不能 23）
- unnecessary_change が fail: 0/0
- 狙い撃ち（違反した観点が fail）: 0/0
- 1件あたり fail になった観点数: []

## 期待ラベル pass（11 件）
- factual の信号（precision/recall < 1）: 0/11（採点不能 0）
- rubric の信号（保持の観点のいずれか fail）: 0/0（採点不能 11）
- unnecessary_change が fail: 0/0

## ケース別

| id | 期待 | 欠陥 | precision | recall | 保持で fail の観点 | 不要な変更 |
|---|---|---|---|---|---|---|
| control-s3a | pass | control_unchanged | 1.0 | 1.0 | — | None |
| exception-drop-s3a | fail | exception_dropped | 1.0 | 0.8 | — | None |
| partial-negation-s5 | fail | partial_negation_to_full | 0.5 | 1.0 | — | None |
| control-s6 | pass | control_unchanged | 1.0 | 1.0 | — | None |
| paraphrase-s6 | pass | legitimate_paraphrase | 1.0 | 1.0 | — | None |
| possibility-s6 | fail | possibility_to_certainty | 0.67 | 1.0 | — | None |
| flag-dropped-k8s | fail | required_flag_dropped | 0.0 | 0.0 | — | None |
| only-py | fail | exclusivity_dropped | 1.0 | 0.75 | — | None |
| hedge-essay | fail | hedge_removed | 1.0 | 1.0 | — | None |
| strength-up-org | fail | recommendation_to_instruction | 1.0 | 0.86 | — | None |
| paraphrase-org | pass | legitimate_paraphrase | 1.0 | 1.0 | — | None |
| control-org | pass | control_unchanged | 1.0 | 1.0 | — | None |
| paraphrase-s3a | pass | legitimate_paraphrase | 1.0 | 1.0 | — | None |
| negation-flip-s3b | fail | negation_flipped | 0.5 | 0.5 | — | None |
| paraphrase-s5 | pass | legitimate_paraphrase | 1.0 | 1.0 | — | None |
| ungrounded-s6 | fail | ungrounded_certainty_added | 0.5 | 1.0 | — | None |
| hedge-s3a | fail | qualifier_added | 1.0 | 1.0 | — | None |
| timing-s6 | fail | timing_shifted | 1.0 | 1.0 | — | None |
| hedge-k8s | fail | default_hedged | 1.0 | 1.0 | — | None |
| order-py | fail | order_lost | 1.0 | 0.6 | — | None |
| tension-essay | fail | contrast_reversed | 0.5 | 0.4 | — | None |
| paraphrase-k8s | pass | legitimate_paraphrase | 1.0 | 1.0 | — | None |
| paraphrase-essay | pass | legitimate_paraphrase | 1.0 | 1.0 | — | None |
| number-s3a | fail | number_changed | 0.67 | 0.67 | — | None |
| strength-s3b | fail | required_to_recommended | 1.0 | 0.67 | — | None |
| tense-s5 | fail | frequency_and_tense_changed | 0.5 | 0.5 | — | None |
| timing-swap-s6 | fail | timing_swapped | 0.33 | 0.33 | — | None |
| necessity-s5 | fail | necessity_dropped | 1.0 | 0.67 | — | None |
| quantifier-k8s | fail | quantifier_changed | 1.0 | 0.75 | — | None |
| strength-py | fail | limit_and_strength_weakened | 1.0 | 0.67 | — | None |
| qualifier-essay | fail | subject_qualifier_dropped | 0.8 | 0.67 | — | None |
| actor-org | fail | actor_swapped | 0.83 | 0.83 | — | None |
| paraphrase-py | pass | legitimate_paraphrase | 1.0 | 1.0 | — | None |
| control-essay | pass | control_unchanged | 1.0 | 1.0 | — | None |
