# 使った後の変化の記録

利用者が、この Skill を使った後の変化を記録したいと言ったときだけ読む。自分から勧めない。通常の依頼では実行しない(Bash のターンが1回増え、入力が増える)。勝手に送らない。

書き換える前の文章と、返した文章のファイルから、本文を含まない選択式の記録(JSON)を出す。原文・結果・引用・行番号・ファイル名・件数は出ない。

```bash
python3 scripts/make_change_report.py --original before.md --result after.md --mode B --model <自分のモデル名> > change-report.json
```

- 出力は、9つの検査(`numbers` `urls` `code` `terms` `added_content` `omitted_content` `negation` `modality` `style`)ごとの `status`、`method`、`direction` と、読みやすさの方向(`chars` `long_paragraphs` `long_sentences` `short_runs` が `decreased` / `same` / `increased`)。
- `status` は `no_candidate`(候補なし)、`candidate`(候補あり。問題とは限らない)、`ok` / `problem`(見比べた結果)。`method` は `deterministic`(スクリプト)、`human`、`model_self_report`。
- 候補が挙がった検査は、元の文と見比べて、`--review 検査名=ok`(または `=problem`)と `--reviewed-by human`(または `model`)を付けて、もう一度実行する。モデルが見比べたなら `model` にする。人が確かめていないものを `human` にしない。
- 版は `SKILL.md` の `VERSION`、モデルは `--model`(英数字と `. _ : / -` の64字まで。分からなければ省く)から入る。
- スクリプトは書き込みも送信もしない。標準出力の JSON を保存する場所は、利用者に確かめる。送る前に、利用者が JSON の内容を確かめる。
