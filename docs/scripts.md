# スクリプト

Skill に同梱したスクリプトを、直接使う方法です。Agent は、Skill の指示でこれらを実行します。計測の `measure.py`、保存の検証の `verify_preservation.py`、書き換えの照合の `compare_rewrite.py`、国語の表記の検査の `check_kokugo.py` と `validate_kokugo_rules.py` があります。`kokugo_engine.py` は後の2つが使う部品で、単独では実行しません。

## 実行する

Python 3.10 以上が必要です。どのスクリプトも標準ライブラリだけで動き、ネットワーク通信とファイルの書き込みをしません。国語の表記の検査(`check_kokugo.py`)も、ネットワークなしで動きます。公式資料を取り直す処理は、Skill の外の `tools/update_kokugo_sources.py` に分けています([国語の表記・用法の検査](kokugo.md#規則を更新する))。`compare_rewrite.py` は、SudachiPy が入っていれば使います。Windows では、`python3` ではなく `python` で実行する場合があります([Python のコマンド名](installation.md#python-のコマンド名))。

次のコマンドは、Skill のディレクトリで実行する場合の例です。ディレクトリは、`skill/japanese-readability-editor/` か、配置先の `japanese-readability-editor/` です。

```bash
python3 scripts/measure.py README.md
python3 scripts/measure.py --locate README.md
python3 scripts/measure.py --json README.md
python3 scripts/measure.py --locate docs/*.md
python3 scripts/measure.py --locate --extras README.md
python3 scripts/verify_preservation.py before.md after.md
python3 scripts/verify_preservation.py --strict before.md after.md
python3 scripts/compare_rewrite.py before.md after.md
python3 scripts/compare_rewrite.py --json before.md after.md
python3 scripts/check_kokugo.py README.md --profile general-tech
python3 scripts/check_kokugo.py README.md --profile official --json
python3 scripts/validate_kokugo_rules.py
```

## measure.py

`measure.py` は、次の指標を出します。

- 総文字数、漢字率、ひらがな率
- 段落数、平均段落長、200字以上の段落数
- 文数、平均文長、46字以上の文数、20字未満の文が3文以上続く箇所の数、1文あたりの平均読点数

短い文の連続は、細切れの手がかりです。20字未満で、句点・感嘆符・疑問符で終わる文が、同じ段落の中で3文以上続く箇所を数えます。句点のない箇条書きは短い文に含めず、箇条書きの項目をまたいでは数えません。文の長さは `--short-threshold`、連続の文数は `--short-run` で変えられます。

`--locate` を付けると、候補のファイル名、行番号、長さ、冒頭を示します。件数を `--max-locate` で絞るときは、長い文は長い順に、短い文の連続は文数の多い順に残します。

計測では、`--locate` の有無にかかわらず、次のものを可能な範囲で解析から除きます。

- fenced code block と YAML frontmatter
- URL そのもの(Markdown のリンクは表示テキストだけを残す)
- Markdown の記号、見出し、表、水平線

英文の ASCII のピリオドは、文の区切りとして扱いません。日本語の文章を主な対象にしているためです。

`--extras` を付けると、長さとは別に、読み流すと見落としやすい4種類の箇所を、指摘として挙げます。

- 漢字が7字以上続く箇所(その場で作られた圧縮漢語など)
- 名詞と「の」が3回以上つながる箇所
- 「ないわけではない」「否定できない」のような二重否定
- 太字にならず、`**` がそのまま表示される箇所(Markdown のファイルのみ)

これらは判定ではなく、直すかどうかは読んで決めます。「〜ないと動かない」(必要条件)や「〜なければならない」「〜ざるを得ない」(義務)は、二重否定として拾いません。

太字は、`**` のすぐ内側が記号で、すぐ外側が文字だと表示されません。`次に**「用語」**を` や `**必須です。**次に` が、その例です。

## verify_preservation.py

`verify_preservation.py` は、空白を除いた文字列が一致すれば終了コード 0、しなければ 1 を返します(読み込みに失敗すると 2)。

> **注意**: このスクリプトが保証するのは「空白以外の文字列が変更されていないこと」だけです。意味の保存は保証しません。英単語の間の空白など、空白が意味を持つ箇所の変更も検出できません。空白全般を無視するので、文と文のあいだの空白の削除、タブの置換、既存の改行の削除も、合格にしてしまいます。

`--strict` を付けると、改行以外のすべての文字(半角・全角スペース、タブ、不可分スペースを含む)が同一で、改行が減っていないときだけ、終了コード 0 を返します。モード C の「改行と空行の挿入のみ」を確かめるときに使います。CRLF と LF の違いは、改行の種類を変えただけなので区別しません。

## compare_rewrite.py

`compare_rewrite.py` は、書き換えの前後を比べ、意味が変わったかもしれない箇所を挙げます。

- 数値、URL、コード、用語の候補が、消えたか、増えたか
- 書き換え後の文に、対応する元の文がないか(原文にない情報の候補)
- 元の文に、対応する書き換え後の文がないか(削除の候補)
- 否定、推量、可能、義務、依頼、勧誘、強調、限定、残余の条件の表現が、対応する文のあいだで増減したか
- 敬体と常体のどちらが多いかが変わったか

数値、URL、コードは、出る回数も比べます。用語は、文書に出るかどうかだけで比べ、出る回数の増減は挙げません。重複を減らす書き換えでは、用語の回数が自然に減るためです。

これらも判定ではありません。正しい言い換えも拾います。

SudachiPy と辞書が入っていれば、形態素解析を使います。否定を品詞で数え、文の対応を内容語の重なりで推定し、カタカナ語の表記ゆれ(サーバとサーバー)を同じ語とみなします。`--tokenizer regex` を付けると、使いません。

uv があれば、次のコマンドで、SudachiPy を自動で入れて実行できます。スクリプトの先頭に、依存関係を宣言しています(PEP 723)。

```bash
uv run scripts/compare_rewrite.py before.md after.md
```

## check_kokugo.py

`check_kokugo.py` は、国語の表記・用法の規則(文化庁の公式資料に基づく)を文章へ当て、規則 ID、位置、該当表記、区分、理由、候補、出典 ID を出します。読み取り専用で、ネットワークを使いません。適用設定(`--profile`)、判定区分、終了コード、JSON の形式、用語集、保護対象、検査していないものは、[国語の表記・用法の検査](kokugo.md)にあります。

```bash
python3 scripts/check_kokugo.py document.md --profile official
```

```text
document.md  (profile: official, rules: 2026-10-10)
  1:1  [error]  KOKUGO-OKURI-003  申し込み → 申込み
      公用文の活用のない複合の語のうち、読み間違えるおそれのない186語は、通則6の許容を適用して送り仮名を省くものとする(訓令 別紙2(1)ただし書)。許容形を用いてよい場合(同2(2))にも、このただし書の語は含まれない。
      出典: NAIKAKU-KUNREI-2010, BUNKA-GUIDE-2022, NAIKAKU-OKURIGANA-1973  [primary-source-derived]
```

## validate_kokugo_rules.py

規則データ(`data/*.json`)を検証します。検査項目は、[国語の表記・用法の検査](kokugo.md#規則データ)にあります。終了コードは、同じ文書の[終了コード](kokugo.md#終了コード)にあります。

## 限界

- 国語の表記の検査の限界は、[国語の表記・用法の検査](kokugo.md#検査していないもの限界)にあります。
- 計測は、日本語の文章を対象にしたヒューリスティックです。文の区切りは、句点、感嘆符、疑問符と、括弧や引用の対応から推定します。Markdown の解析は簡易で、入れ子の引用、インデントされたコードブロック、HTML の複雑な構造は正確に扱えません。
- `compare_rewrite.py` の文の対応は、語の重なりによる推定です。大きく言い換えた文は、意味が同じでも、対応がないと出ることがあります。否定以外の表現の検出は、正規表現による近似です。
- `--extras` は正規表現による指摘で、形態素解析を使いません。漢字の連続は、固有名詞や法令用語も拾います。「の」の連鎖は、漢字、カタカナ、英数字の名詞に限ります。
- 表示されない太字は、`**` を出現順に2つずつ組にして、CommonMark の区切りの規則で調べます。何を記号とみなすかは実装で違うため、GitHub と、CommonMark 0.31 に従う実装(pandoc など)のどちらか一方で表示されない箇所を拾います。そのため、GitHub では表示される `**★重要**` も指摘します。
