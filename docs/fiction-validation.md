# 小説モード D の実装・検証記録

初回確認日: 2026-10-10。実装時点の検証の記録で、その後の変更は反映していません。今の構成は[開発](development.md#小説モードの正本と評価)、評価の入力と範囲は[評価ケース](../evals/README.md)にあります。

## 追加したもの

- Skill の正本: `SKILL.md` の D の入口、`references/fiction-writing.md`(操作契約)、`references/fiction-checks.md`(補助検査の仕様)、`assets/fiction-examples.md`(修正例)、`assets/fiction-context-template.md`(任意の文脈メモ)、`scripts/check_fiction.py`(読み取り専用の字数・括弧・指定文字列の検査)。
- 配布: `tools/package.py` が、ZIP と OpenCode・Hermes 向けフォルダへ複製する。Gemini 貼付用の指示にも D の契約を埋め込む。
- 開発用: `tests/test_check_fiction.py`、`test_fiction_integration.py`、`test_fiction_evals.py`、`evals/fiction-cases.json`(18観点を網羅する自作24ケース)、`evals/fiction-model-run.json`(12入力の実出力と判定)。
- 変えなかったもの: 既存の `measure.py`、`compare_rewrite.py`、`verify_preservation.py`、`check_kokugo.py`、文化庁の規則データ、OpenCode・Hermes の対応。

## 設計判断

明示A/B/Cを優先し、本文・引用・コードの指示を素材として扱う。Dでは新規生成と保持を伴う推敲を分け、標準reviseは最小変更、critiqueは書き換えない。比喩、反復、時制、必要な要約や表記を一般文書の規則で一律に均さない。

検査器は字数・括弧・指定文字列の候補だけを示す。コードポイント数は見た目の文字数とは一致しない。人物の同一性や意味保存は推定しない。Cの既存検証器はCRLF/BOMを正規化するため、生バイト比較を追加テストで併用した。既存CLIは変更していない。

## 検証結果

- `tools/check_all.py`(実装後): 772実行、771成功、失敗0、エラー0、スキップ1(変更前から同じ)。2026-10-11 に最新の main を取り込んだ後は、784実行、783成功。Skill 構造の警告0、文化庁の規則データと生成文書も正常。
- `tools/package.py`: ZIP、Gemini フォルダ、貼付用指示、OpenCode・Hermes の配布物を生成できた。D の新規素材5ファイルは正本とバイト一致。展開した Markdown の相対参照の切れは0件。
- `check_fiction.py` の終了コード: 候補なし 0、候補あり 1、入力の失敗 2。不正な Unicode の設定は、トレースバックを出さずに失敗として扱う。
- 初回の PR の Windows CI で、字数テスト2件が失敗した。Windows が改行を CRLF に変換したためで、検査器ではなくテストの入力が原因だった。テストの原稿を UTF-8 のバイトで保存する形に直し、LF と CRLF の計数は専用のテストで維持している。

モデル評価は初回の12ケースの記録を維持し、統合後の再実行はしていません。テストの件数は当時の値で、その後のテストの整理で変わっています。決定的なテストをモデル挙動の追加証拠とは扱いません。

## モデル評価と限界

更新したSkillを明示的に読ませた新しいモデル文脈で12ケースを一括実行し、別の新しいモデル文脈で評価した。12件pass、0件fail、0件uncertain。r03の空白・タブ・既存改行保持と、r07/r08の長さ（93/100コードポイント）もPythonで照合した。r09では「夜が肺に溜まる」等を保ち、重複助詞だけが直った。

使用モデルはCodexのGPT-6系とだけ確認でき、正確な識別子・サンプリング設定は不明。12件はケース別の隔離実行でも反復評価でもない。r03のLF/TABには輸送時の明示的な正規化指示を使った。生成後の表・descriptionの整形変更を記録に注記し、ハッシュは実際に読み込んだ版を示す。採点理由は別担当の報告の要約で、採点指示全文・生の回答は保存していない。

残り12ケースのモデル挙動、製品固有のSkill起動・検出、他製品でのD動作、Windows/Linux上の今回の実行、人間による文学的評価は未実行。静的構造テストや実装者レビューをモデル挙動の実証にしない。文学的品質や全編整合性を保証しない。根拠・採否は [設計参考](fiction-design.md)、実入力と実出力は [モデル実行記録](../evals/fiction-model-run.json) を参照できる。
