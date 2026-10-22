# スクリプトの使い方

同梱のスクリプトは、実行して出力だけを使う。**ソースは読まない**(読んでも出力は変わらず、文脈が増えるだけである)。
用法は `--help` で分かる。実行できない環境では、規則と目視で確かめ、実行したとは報告しない。

## スクリプト一覧

すべて標準ライブラリだけで動き、通信しない。`make_feedback.py` と `make_change_report.py` は記録を新規保存する。ほかの CLI は読み取り専用である。**実行して出力だけを読む。ソースは読まない。** 出力の項目は `--help` と `--json` で分かる。

| スクリプト | 使う場面 | コマンド | 出力 | 終了コード |
|---|---|---|---|---|
| `compare_rewrite.py` | B で書き換えた後に、意味が変わった候補を挙げる | `compare_rewrite.py before.md after.md` | 種類ごとの候補(数値・URL・コード・用語の増減、対応する文のない文、否定・推量などの増減、文体)。`--json` で全件、`--max N` で件数を絞る | 0=完了、2=読めない |
| `check_kokugo.py` | 国語の表記・用法の検査([kokugo-check.md](kokugo-check.md)) | `check_kokugo.py FILE --profile general-tech` | 規則 ID、位置、該当表記、区分、理由、候補、出典 ID と、検査していない項目(`coverage`)。`--json` あり | 0=指摘なし、1=error あり、2=検査できず |
| `measure.py` | 長さの計測と、直す候補の箇所の特定 | `measure.py --locate FILE` | 段落・文の長さの候補(ファイル名、行番号、長さ、冒頭)。`--json`、`--extras`、`--max-locate N` あり | 0=完了、2=読めない |
| `verify_preservation.py` | C の保存の検証(`SKILL.md` の「Paragraph-only の手順」) | `verify_preservation.py --strict before.md after.md` | 一致したか、違う位置 | 0=一致、1=不一致、2=読めない |
| `check_fiction.py` | D の文字数・括弧・指定文字列の検査([fiction-checks.md](fiction-checks.md)) | `check_fiction.py FILE [--settings FILE] [--json]` | 候補の一覧 | fiction-checks.md を参照 |
| `make_feedback.py` | 利用者が結果の問題を報告したいと言ったときだけ([feedback.md](feedback.md)) | feedback.md を参照 | フィードバック票(JSON)の保存と標準出力、保存先の表示 | 0=保存した、2=入力・保存の誤り |
| `make_change_report.py` | 利用者が、使った後の変化の記録を求めたときだけ([change-report.md](change-report.md)) | change-report.md を参照 | 本文を含まない選択式の記録(JSON)の保存と標準出力、保存先の表示 | 0=保存した、2=入力・保存の誤り |
| `feedback_storage.py` | `make_feedback.py` と `make_change_report.py` の保存処理。直接実行しない | - | 新規の JSON ファイル | - |
| `skill_info.py` | 版や実行環境を尋ねられたとき、問題の報告票を作るとき(通常の依頼では実行しない) | `skill_info.py --model <モデル名>` | 版・OS・アプリ・モデル・日付の JSON(標準出力)と、保存先 `~/.agents/skill-env/<スキル名>.json`(標準エラーの `save_to`)。JSON を保存するのは実行した側。`--version` は1行 | 0=出した |
| `validate_kokugo_rules.py` | 規則データを変えた後の検証。通常の依頼では使わない | `validate_kokugo_rules.py` | 検証結果。`--json` あり | 0=問題なし、1=問題あり、2=実行できず |
| `kokugo_engine.py` | `check_kokugo.py` と `validate_kokugo_rules.py` の部品。実行も読むこともしない | - | - | - |

## 書き換えの照合(compare_rewrite.py)

スクリプトを実行できる環境では、書き換える前の文章を、対象と別のディレクトリ(一時ディレクトリなど)へ保存しておき、下のコマンドで照合の候補を挙げる。終わったら、その保存先を削除する。この Skill のコマンドは `python3` で書いている。動かなければ `python` で実行する(Windows など)。コマンドの `scripts/` などの相対パスは、この Skill のフォルダ(`SKILL.md` があるフォルダ)からの相対パスで、作業ディレクトリからのものではない。実行するときは、Skill のフォルダの絶対パスを前に付ける。

```bash
python3 scripts/compare_rewrite.py before.md after.md
```

数値・URL・コード・用語の増減、対応する元の文がない文、否定・推量・可能・依頼などの表現の増減、文体の変化を示す。判定ではないので、挙がった箇所を上の観点で元の文と見比べる。SudachiPy が入っていれば、否定と文の対応をより正確に判定する。

出力の `tokenizer` が `regex` なら、SudachiPy が入っていない。利用者の手元ではない、クラウドの実行環境(ChatGPT や Claude のアプリなど)では、SudachiPy を入れて、照合をやり直す。入れるコマンドは `python3 -m pip install sudachipy sudachidict-small` である。

コマンドのネットワークが制限されていれば、ネットワークを使える権限で実行する(承認が要るなら求める)。一度試して入らなければ、`regex` の結果を使う。利用者の手元の環境(Codex、Claude Code など)には、断りなく入れない。

## 計測(measure.py)

```bash
python3 scripts/measure.py --locate README.md
```

段落と文の長さの候補を、ファイル名・行番号・長さ・冒頭で示す。`--json` で機械可読な出力になる。`--extras` を加えると、連続漢字、名詞と「の」の3連、二重否定、表示されない太字を指摘する。

読み取り専用であり、修正の要否と方法は自分で判断する。実行できない環境では、長さを目視で見積もる。
