# 自動検証（表層）

表層指摘件数は誤り数でも品質点でもない。Bの意味保持はLLMまたは人手で別途検証する。

終了コード0は検査完了を示し、意味・品質の合格を保証しません。

## "condition"

契約判定: uncertain。表層検査では意味保持・理解・文学的品質は未判定。

|項目|原文|候補|
|---|---:|---:|
|chars|27|12|
|sentences|1|1|
|paragraphs|1|1|
|mean_sentence_chars|27.0|12.0|
|kanji_ratio|0.48148148148148145|0.4166666666666667|
|long_sentences|0|0|
|long_paragraphs|0|0|

指摘（修正候補）:

> {"category": "numbers", "direction": "missing", "line": 1, "quote": "30分", "reason": "原文と候補の要素・文対応に差。意味の変化か照合が必要。"}

> {"category": "numbers", "direction": "added", "line": 1, "quote": "3分", "reason": "原文と候補の要素・文対応に差。意味の変化か照合が必要。"}

> {"category": "unmatched", "direction": "before", "line": 1, "quote": "管理者が承認した場合に限り、30分以内に実行できます。", "reason": "原文と候補の要素・文対応に差。意味の変化か照合が必要。"}

> {"category": "limit", "before": 1, "after": 0, "reason": "否定・条件・文の働き等の表現数に差。表現数だけで意味改変を確定しない。"}

## "paragraph"

契約判定: pass。JSON内の原文字列を保持し、LF挿入のみか検査。元ファイルのバイト保持と読解品質は対象外。

|項目|原文|候補|
|---|---:|---:|
|chars|26|26|
|sentences|2|2|
|paragraphs|1|2|
|mean_sentence_chars|13.0|13.0|
|kanji_ratio|0.5384615384615384|0.5384615384615384|
|long_sentences|0|0|
|long_paragraphs|0|0|

指摘（修正候補）:
