# 結果への問題の報告

利用者が、この Skill の結果の問題を報告したいと言ったときだけ読む。自分から勧めない。勝手に送らない。スクリプトを実行できる環境では、次で報告票の JSON を出せる。

```bash
python3 scripts/make_feedback.py --original before.md --result after.md --type over_editing --quote "結果の該当箇所" --consent-storage
```

- `--type` は `added_content`(原文にない主体・条件などを足した)、`strength_changed`(言い切りの強さが変わった)、`number_or_negation`(数値・否定が変わった)、`meaning_lost`(情報が抜けた)、`over_editing`(直さなくてよい所まで直した)、`unneeded_change`(変更が不要な文章を変えた)、`unnatural`(不自然・読みにくい)、`other` から選ぶ。
- `--quote` は、問題の箇所を結果からそのまま写す。情報が抜けた場合は原文から写す。
- 任意の項目: `--mode`、`--severity`(major/minor)、`--comment`、`--request`(Skill に出した依頼文)、`--origin`(`model_output` か `artificial`)。
- 版とモデル: 先に `python3 scripts/skill_info.py --model <自分のモデル名>` を実行し(JSON は `save_to` の場所へ保存する)、出力の `skill_version` を `--skill-version` に、`model` を `--model` に渡す。
- `--consent-storage`(非公開の保管と、スキル改良の検討への同意)は必須。`--consent-ai`(改良案の下書きのための AI への送信)と `--consent-publish`(匿名化した公開)は任意。どれも、利用者に意味を伝えて確かめてから付ける。確かめずに付けない。
- JSON は `~/.agents/feedback/japanese-readability-editor/` に自動保存する。`--out-dir <フォルダ>` で変更できる。記録ごとに別名で保存し、標準エラーの `saved_to` に実際の保存先を出す。標準出力にも従来どおり JSON を出す。保存に失敗したら終了コード 2 で、JSON は標準出力に出さない。自動送信はしない。送付は、メンテナーが利用者に個別に伝えた窓口(メールなど)で、利用者が自分で行う。
- 標準エラー出力の警告(メールアドレス、URL、電話番号らしい文字列)は、利用者に見せる。機密を含みうる文書は、GitHub Issue に貼らず、メールで送る。送る前に、利用者が JSON の内容を確かめる。
