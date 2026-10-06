# japanese-readability-editor

生成AIが出力する日本語や、既存の日本語文書を、意味・精度・必要な情報量を保ったまま読みやすくする Agent Skill です。

一つの共通 `SKILL.md` を正本にします。次の環境で使えます。

- Codex、Claude Code、GitHub Copilot
- Gemini CLI、Antigravity(IDE と CLI)
- ChatGPT Work、Claude Cowork、Gemini Apps

環境ごとの差は、配置先、ZIP、README、生成物で吸収します。Skill 本文の複製はありません。

## 目的

次のような問題を検出し、直します。

- 長すぎる段落、長すぎる文
- 主語・述語や論理関係の追いにくさ、次の展開の予測しにくさ
- 見出しだけでは中身が分からない構成
- 冗長、直訳調、翻訳調の比喩、抽象的な言い回し、AI特有の決めぜりふ、内容のない結び

目的は、日本語を短くすることではありません。数値、条件、例外、因果関係、主体、固有名詞、技術用語、API名、コマンド、コード、URL、引用、出典を、読みやすさのために削ったり簡略化したりしません。

## 共通 Skill の使い方

Skill は、依頼の内容が `description` に合うと自動で使われます。名前を指定して呼ぶこともできます。

| 環境 | 明示的に呼ぶ方法 |
|---|---|
| Codex | `$japanese-readability-editor` |
| ChatGPT Work | `@japanese-readability-editor`(暗黙起動は不安定。8 節) |
| Claude Code | `/japanese-readability-editor` |
| GitHub Copilot | `/japanese-readability-editor`(CLI。依頼文の中に書く) |
| Antigravity | `/japanese-readability-editor`(`agy -p` では、指定として扱われなかった) |
| Gemini CLI | 公式資料に、明示的に呼ぶ方法の記載がない。依頼に Skill 名を書く |
| Gemini Apps | `/`(今後 `@`)に続けて Skill 名 |

3つのモードがあります。

- **A. 新規生成**: 読者、必要な情報、結論などを整理してから書きます。
- **B. Rewrite**: 意味を保ちながら書き換えます。
- **C. Paragraph-only**: 文章を変えずに、改行と空行だけで段落を分けます。

通常は完成した文章だけを返します。「レビューして」「問題点を挙げて」「計測して」「before/after を比べて」と頼んだときだけ、診断情報を示します。

### モードを指定する

モードは、依頼の中で、記号か名前を挙げて指定できます。指定したときは、依頼の言い回しからの推測より、指定が優先されます。

| モード | 指定の例 |
|---|---|
| A. 新規生成 | `モード A`、`新規生成モードで` |
| B. Rewrite | `モード B`、`Rewrite モードで` |
| C. Paragraph-only | `モード C`、`paragraph-only モードで` |

Skill を呼ぶ名前と同じメッセージに書きます。確かめたのは、呼び出しと同じ行に書く形です。`$japanese-readability-editor` の部分は、上の表の、使う環境の呼び方に替えてください。

```text
$japanese-readability-editor モード C
docs/design.md に適用して。
```

`mode: paragraph-only` のような英語の書き方も、Skill に例として書いてあります。ただし、確かめたのは、上の表の書き方だけです(下の「動作の確認」)。

### 使用例

```text
この設計書の日本語を japanese-readability-editor を使って校正して。
技術用語、数値、コード、URL、出典は変更しないこと。
```

```text
この調査結果を技術レポートとしてまとめて。
最終稿に japanese-readability-editor を適用すること。
```

```text
japanese-readability-editor を paragraph-only モードで適用。
文章自体は変更せず、長すぎる段落だけ分割すること。
```

## 制約と非対応

- Skill は文章の意味を検証しません。意味の保存を保証するのは、Agent の判断と、利用者の確認です。
- ChatGPT での実機確認では、二重否定の意味の反転、残余の条件の言い換え、文体の変更が起きました。`SKILL.md` に対策を入れましたが、誤りを完全には防げません。
- ChatGPT の暗黙起動は、実測では不安定でした。確実に使うには、`@` で指定してください(8 節)。
- モードの指定は、Skill の指示です。環境の機能による強制ではなく、守られるかどうかは、環境とモデルによります(6 節)。Codex(Medium)では、貼り付けた文章の中に「モード C」があると、指定と取り違える回がありました。Antigravity、ChatGPT Work、Claude Cowork、Gemini CLI、Gemini Apps では、確かめていません。

## ドキュメント

- [インストール](docs/installation.md)
- [環境別の対応](docs/environments.md)
- [使い方の詳細](docs/usage.md)
- [スクリプト](docs/scripts.md)
- [設計](docs/design.md)
- [開発](docs/development.md)
- [ChatGPT Work の実機確認](docs/chatgpt-work-checks.md)
- [ChatGPT Work の暗黙起動の実測](docs/chatgpt-implicit-invocation.md)
- [モードの指定の動作確認](docs/mode-specification-checks.md)
