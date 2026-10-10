# check_fiction.py の仕様

標準ライブラリだけで動く読み取り専用の補助検査。入力原稿・設定を書き換えず、API や LLM を呼び出さない。

## CLI

```bash
python3 scripts/check_fiction.py manuscript.md
python3 scripts/check_fiction.py chapter1.md chapter2.md --json
python3 scripts/check_fiction.py manuscript.md --settings work-checks.json --json
python3 scripts/check_fiction.py - --json
```

入力は UTF-8。`-` は標準入力で一度だけ指定できる。設定ファイルは任意。作品メモの代替ではなく、明示された文字列検査だけを追加する。

| 終了コード | status | 意味 |
|---|---|---|
| 0 | no_candidates | 実行に成功し、指定した検査で候補なし |
| 1 | candidates | 実行に成功し、確認候補あり |
| 2 | execution_failed | CLI、設定、入力読み込みなどの失敗。部分的に読めたファイルがあっても検査完了とはしない |

候補なしは「小説として合格」でも、未検査の項目に問題がない証明でもない。通常出力はファイル・行・列・検査 ID を示す。必要な文字列がファイル全体にない場合は、存在する行を特定できないため位置は null（通常出力では位置なし）になる。

## 文字数の定義

`counts.codepoints` は復号した入力の Unicode コードポイント総数。空白・改行・先頭の BOM も数える。CRLF は二つのコードポイントだが一つの改行として `newline_sequences` に数える。単独 CR/LF も改行として数える。

`whitespace_codepoints` は Python の `str.isspace()` が真になる文字の数。`non_whitespace_codepoints` はその数を総数から引いた値。空の入力は各値が0で、候補がなければ終了コード0。

コードポイント数は見た目の文字数と完全には一致しない。結合文字、異体字セレクター、複数コードポイントの絵文字などを一文字と数える処理はしていない。長さの合否・文体の優劣は決めない。

行・列は1始まり。CRLF は行位置の計算では一つの改行。列はコードポイント単位であり、画面上の表示幅ではない。

## 括弧の候補

対象は `()`、`[]`、`{}`、`（）`、`［］`、`｛｝`、`「」`、`『』`、`【】`、`〈〉`、`《》`、`〔〕`、`〖〗`。入れ子と複数行を一つのスタックで確認する。

| 検査 ID | 候補 |
|---|---|
| FICTION-BRACKET-UNEXPECTED | 対応する開始括弧のない終了括弧 |
| FICTION-BRACKET-ORDER | 入れ子の閉じる順序・種類の不整合 |
| FICTION-BRACKET-UNCLOSED | 閉じていない開始括弧 |

引用やコードも含む入力全文を走査し、文学上の意図や独自記法は判断しない。直線の引用符・アポストロフィ・ASCII の山括弧は対応検査の対象にしない。独自記法の候補は人が確認し、自動修正しない。

## 任意の文字列指定

`work-checks.json` の例：

```json
{
  "forbidden": ["アオイー", "白い傘"],
  "required": ["アオイ"]
}
```

最上位はオブジェクトで、任意キーは `forbidden` と `required` の二つだけ。各値は重複のない空でない文字列の配列。未指定のキーは空配列と同じ。未知のキー、不正な型、UTF-8 で表せない孤立サロゲートも終了コード2。

`forbidden` は使用を避けると指定した文字列の出現を FICTION-STRING-FORBIDDEN として示す。`required` は各入力ファイルに最低一回必要と指定した文字列で、存在しなければ FICTION-STRING-REQUIRED を示す。章ごとに必須名が違うなら、その章に必要な設定だけを渡す。

一致方法は、大文字小文字を区別する Unicode 文字列の単純な部分一致。正規化、正規表現、単語境界、語義、人物の同一性の推定はしない。重なる一致も数える。例えば「アオイ」は「アオイー」にも含まれ、必須検査を満たしても表記の正しさを意味しない。保護文字列の原稿間比較は実装しておらず、出現回数を意味保存とは呼ばない。

## JSON スキーマ（schema_version 1）

最上位の形は次のとおり。配列は空になり得る。

| フィールド | 型・意味 |
|---|---|
| schema_version | integer、1 |
| tool | string、check_fiction.py |
| status | string、上の3状態 |
| exit_code | integer、0/1/2 |
| definitions | object、計数・位置・一致方法・限界の説明 |
| settings | object、file（string または null）、forbidden/required（文字列配列） |
| files | array、検査できた入力の結果 |
| summary | object、files_checked/candidates/errors（integer） |
| errors | array、CLI・設定・読み込みの失敗 |

`files[]` は `file`（string）、`counts`（四つの整数）、`candidates`（配列）を持つ。候補は `file`、`line`、`column`、`check_id`、`text`、`message`、`details` を持つ。行・列は整数または null、details は検査別の補助情報。失敗 ID は FICTION-CLI、FICTION-SETTINGS-JSON、FICTION-SETTINGS、FICTION-INPUT-READ。`--json` の実行失敗も JSON と終了コード2で区別する。`--help` は通常のヘルプ出力で終了コード0。

## 保証しないこと

文体、視点、人物の知識、因果、伏線、開示順序、意味保存、物語全体の整合性や面白さは検査しない。独自記法による誤検出、文字列の文脈による見逃し・誤検出がある。人が [小説の判断基準](fiction-writing.md)で読むための候補である。
