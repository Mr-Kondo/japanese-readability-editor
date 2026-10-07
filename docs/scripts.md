# スクリプト

Skill に同梱した3つのスクリプトを、直接使う方法です。Agent は、Skill の指示でこれらを実行します。

## 実行する

Python 3.10 以上が必要です。どのスクリプトも標準ライブラリだけで動き、ネットワーク通信とファイルの書き込みをしません。`compare_rewrite.py` は、SudachiPy が入っていれば使います。Windows では、`python3` ではなく `python` で実行する場合があります([Python のコマンド名](installation.md#python-のコマンド名))。

次のコマンドは、Skill のディレクトリで実行する場合の例です。ディレクトリは、`skill/japanese-readability-editor/` か、配置先の `japanese-readability-editor/` です。

```bash
python3 scripts/measure.py README.md
python3 scripts/measure.py --locate README.md
python3 scripts/measure.py --json README.md
python3 scripts/measure.py --locate docs/*.md
python3 scripts/measure.py --locate --extras README.md
python3 scripts/verify_preservation.py before.md after.md
python3 scripts/compare_rewrite.py before.md after.md
python3 scripts/compare_rewrite.py --json before.md after.md
```

## measure.py

`measure.py` は、次の指標を出します。

- 総文字数、漢字率、ひらがな率
- 段落数、平均段落長、200字以上の段落数
- 文数、平均文長、80字以上の文数、1文あたりの平均読点数

`--locate` を付けると、候補のファイル名、行番号、長さ、冒頭を示します。

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

> **注意**: このスクリプトが保証するのは「空白以外の文字列が変更されていないこと」だけです。意味の保存は保証しません。英単語の間の空白など、空白が意味を持つ箇所の変更も検出できません。

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

## 限界

- 計測は、日本語の文章を対象にしたヒューリスティックです。文の区切りは、句点、感嘆符、疑問符と、括弧や引用の対応から推定します。Markdown の解析は簡易で、入れ子の引用、インデントされたコードブロック、HTML の複雑な構造は正確に扱えません。
- `compare_rewrite.py` の文の対応は、語の重なりによる推定です。大きく言い換えた文は、意味が同じでも、対応がないと出ることがあります。否定以外の表現の検出は、正規表現による近似です。
- `--extras` は正規表現による指摘で、形態素解析を使いません。漢字の連続は、固有名詞や法令用語も拾います。「の」の連鎖は、漢字、カタカナ、英数字の名詞に限ります。
- 表示されない太字は、`**` を出現順に2つずつ組にして、CommonMark の区切りの規則で調べます。何を記号とみなすかは実装で違うため、GitHub と、CommonMark 0.31 に従う実装(pandoc など)のどちらか一方で表示されない箇所を拾います。そのため、GitHub では表示される `**★重要**` も指摘します。
