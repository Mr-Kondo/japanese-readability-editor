# Ragas 繰り返し実行の安定性

> ラベルは構成によるもので人の確認前。率は記述値で、有効性の根拠にしない。

- 繰り返し: 3 回、ケース: 13 件
- factual の信号が回ごとに変わったケース: 2
- rubric の信号が回ごとに変わったケース: 0
- fail になった観点の集合が回ごとに変わったケース: 7
- 観点の値（pass/fail/uncertain）が回ごとに変わった数: 7/91（0.077）
- precision の最大の幅: 0.34、recall の最大の幅: 0.25

## 期待ラベル fail（8 件）
- factual の信号: 回ごと [8, 8, 7]、多数決 8
- rubric の信号: 回ごと [8, 8, 8]、多数決 8
- 狙い撃ち（違反した観点が fail）: 回ごと [8, 8, 8] / 8

## 期待ラベル pass（5 件）
- factual の信号: 回ごと [1, 0, 0]、多数決 0
- rubric の信号: 回ごと [0, 0, 0]、多数決 0

## ケース別

| id | 期待 | factual | rubric | fail の観点 | 値が変わった観点 |
|---|---|---|---|---|---|
| control-s3a | pass | [False, False, False] | [False, False, False] | —; —; — | — |
| paraphrase-s3a | pass | [False, False, False] | [False, False, False] | —; —; — | — |
| number-s3a | fail | [True, True, True] | [True, True, True] | condition_scope,numbers_order,ungrounded_specificity; actor_target,condition_scope,numbers_order,ungrounded_specificity; condition_scope,numbers_order,ungrounded_specificity | actor_target |
| exception-drop-s3a | fail | [True, True, True] | [True, True, True] | actor_target,condition_scope,modality_strength,negation_polarity,numbers_order; actor_target,condition_scope,modality_strength,negation_polarity,numbers_order; actor_target,condition_scope,modality_strength,negation_polarity,numbers_order | — |
| negation-flip-s3b | fail | [True, True, True] | [True, True, True] | actor_target,condition_scope,modality_strength,negation_polarity,numbers_order,ungrounded_specificity; actor_target,condition_scope,modality_strength,negation_polarity,numbers_order; actor_target,condition_scope,modality_strength,negation_polarity,numbers_order,ungrounded_specificity | ungrounded_specificity |
| strength-s3b | fail | [True, True, False] | [True, True, True] | condition_scope,modality_strength,negation_polarity; condition_scope,modality_strength; condition_scope,modality_strength,negation_polarity | negation_polarity |
| partial-negation-s5 | fail | [True, True, True] | [True, True, True] | actor_target,condition_scope,modality_strength,negation_polarity; actor_target,condition_scope,modality_strength,negation_polarity,numbers_order; actor_target,condition_scope,modality_strength,negation_polarity | numbers_order |
| paraphrase-s5 | pass | [False, False, False] | [False, False, False] | —; —; — | — |
| tense-s5 | fail | [True, True, True] | [True, True, True] | condition_scope,modality_strength,numbers_order,ungrounded_specificity; condition_scope,modality_strength,numbers_order,ungrounded_specificity; condition_scope,modality_strength,numbers_order | ungrounded_specificity |
| control-s6 | pass | [False, False, False] | [False, False, False] | —; —; — | — |
| ungrounded-s6 | fail | [True, True, True] | [True, True, True] | actor_target,condition_scope,modality_strength,numbers_order,ungrounded_specificity; actor_target,condition_scope,modality_strength,numbers_order,ungrounded_specificity; actor_target,condition_scope,modality_strength,ungrounded_specificity | numbers_order |
| timing-swap-s6 | fail | [True, True, True] | [True, True, True] | actor_target,condition_scope,modality_strength,numbers_order; actor_target,condition_scope,modality_strength,numbers_order; actor_target,condition_scope,modality_strength,numbers_order,ungrounded_specificity | ungrounded_specificity |
| paraphrase-s6 | pass | [True, False, False] | [False, False, False] | —; —; — | — |
