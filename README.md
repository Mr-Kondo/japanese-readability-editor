# japanese-readability-editor

生成AIが出力する日本語や、既存の日本語文書を、意味・精度・必要な情報量を保ったまま読みやすくする Agent Skill です。

一つの共通 `SKILL.md` を正本にします。次の環境で使えます。

- Codex、Claude Code、GitHub Copilot
- Gemini CLI、Antigravity(IDE と CLI)
- ChatGPT Work、Claude Cowork、Gemini Apps
- OpenCode、Hermes Agent(モデルを介したスクリプトの実行とモード指定は、確かめた範囲が限られる。[注意](#注意))

環境ごとの差は、配置先、ZIP、生成物、ドキュメントで吸収します。Skill 本文の複製はありません。

## 目的

次のような問題を検出し、直します。

- 長すぎる段落、長すぎる文
- 主語・述語や論理関係の追いにくさ、次の展開の予測しにくさ
- 見出しだけでは中身が分からない構成
- 冗長、直訳調、翻訳調の比喩、抽象的な言い回し、AI特有の決めぜりふ、内容のない結び
- 国語の表記・用法の基準(文化庁の常用漢字表、現代仮名遣い、送り仮名の付け方、外来語の表記、公用文作成の考え方など)に照らした表記の確認

目的は、日本語を短くすることではありません。数値、条件、例外、因果関係、主体、固有名詞、技術用語、API名、コマンド、コード、URL、引用、出典を、読みやすさのために削ったり簡略化したりしません。

## クイックスタート

### Codex、Claude Code などに入れる

Python 3.10 以上が必要です。リポジトリを取得し、`--dry-run` で配置先を確かめます。何も書き込みません。

```bash
git clone https://github.com/Mr-Kondo/japanese-readability-editor.git
cd japanese-readability-editor
python3 tools/install.py --scope user --target all --dry-run
```

Windows では、`python3` ではなく `python` で実行する場合があります。その場合は、コマンドの `python3` を `python` に読み替えてください([Python のコマンド名](docs/installation.md#python-のコマンド名))。

問題がなければ、`--dry-run` を外して実行します。`all` の代わりに、使う環境の target だけを指定することもできます。環境ごとの `--target` は、[インストール](docs/installation.md#インストールする)の表にあります。

### OpenCode、Hermes Agent に入れる

`--target all` には含みません。`--target opencode` か `--target hermes` を指定します。配置先は、環境変数やプロファイルで変わるので、先に `--dry-run` で、実際の配置先と決め方を確かめます。配置先の決め方、プロジェクトへの導入、重複の確認、検証は、[インストール](docs/installation.md#opencode-と-hermes-agent-に入れる)にあります。

### ChatGPT Work、Claude Cowork、Gemini Apps に入れる

これらの環境は、配置先のディレクトリを持ちません。[最新の Release](https://github.com/Mr-Kondo/japanese-readability-editor/releases/latest) から生成物をダウンロードし、各製品の画面からアップロードします。環境ごとにアップロードするものと手順は、[インストール](docs/installation.md#アップロード型の環境に入れる)にあります。

### そのほかの手順

- [特定のプロジェクトに入れる](docs/installation.md#特定のプロジェクトに入れる)
- [更新する](docs/installation.md#更新する)
- [動作を確認する](docs/installation.md#動作を確認する)。どの環境でも、実際に依頼して確かめられます。
- [削除する](docs/installation.md#削除する)。`tools/uninstall.py` が、`tools/install.py` で配置したものを削除します。インストールしたときと同じ `--scope` と `--target` を指定し、まず `--dry-run` で、削除するものを確かめます(何も削除しません)。
- [Claude Code のプラグインとして入れる](docs/environments.md#プラグインとして入れる)

## 使い方

Skill は、依頼の内容が `description` に合うと自動で使われます。名前を指定して呼ぶこともできます。

| 環境 | 明示的に呼ぶ方法 |
|---|---|
| Codex | `$japanese-readability-editor` |
| ChatGPT Work | `@japanese-readability-editor`(暗黙起動は不安定) |
| Claude Code | `/japanese-readability-editor` |
| GitHub Copilot | `/japanese-readability-editor`(CLI。依頼文の中に書く) |
| Antigravity | `/japanese-readability-editor`(`agy -p` では、指定として扱われなかった) |
| Gemini CLI | 公式資料に、明示的に呼ぶ方法の記載がない。依頼に Skill 名を書く |
| Gemini Apps | `/`(今後 `@`)に続けて Skill 名 |
| OpenCode | 明示的に呼ぶ構文は、公式資料に見つからなかった。依頼に Skill 名を書く([OpenCode](docs/environments.md#opencode)) |
| Hermes Agent | `/japanese-readability-editor`、または `hermes chat -s japanese-readability-editor -q "..."`([Hermes Agent](docs/environments.md#hermes-agent)) |

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

指定がないときや、指定と依頼が食い違うときの扱いは、[使い方の詳細](docs/usage.md)にあります。

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

計測と照合のスクリプトを直接使う方法は、[スクリプト](docs/scripts.md)にあります。

### 国語の表記・用法の検査

文化庁の公式資料に基づく表記・用法の規則を、適用設定(モードとは独立)に応じて文章へ当てられます。適用設定は、`general-tech`(既定)、`public-explanation`、`official` の3つです。規則には出典があり、公式資料の規定と、この skill の運用判断を区別しています。

実行方法、適用設定の使い分け、指摘の区分、終了コード、限界は、[国語の表記・用法の検査](docs/kokugo.md)にあります。

## 注意

- 国語の表記の検査は、規則に登録した語・表記を探すだけです。『指摘なし』は『規則に違反していない』ことを意味しません([限界](docs/kokugo.md#検査していないもの限界))。
- Skill は文章の意味を検証しません。意味の保存を保証するのは、Agent の判断と、利用者の確認です。返ってきた文章は、元の文と突き合わせて確認してください。
- ChatGPT での実機確認では、二重否定の意味の反転、残余の条件の言い換え、文体の変更が起きました。`SKILL.md` に対策を入れましたが、誤りを完全には防げません。
- ChatGPT の暗黙起動は、実測では不安定でした。確実に使うには、`@` で指定してください([実測](docs/chatgpt-implicit-invocation.md))。
- モードの指定は、Skill の指示です。環境の機能による強制ではなく、守られるかどうかは、環境とモデルによります。Codex(Medium)では、貼り付けた文章の中に「モード C」があると、指定と取り違える回がありました。Antigravity、Claude Cowork、Gemini CLI、Gemini Apps では、確かめていません([動作の確認](docs/usage.md#動作の確認))。
- Claude のアプリでは、モデルによって結果が違いました。Haiku 4.5 では、Skill を読み込んでも、文体を敬体に変えるなど、規則が守られない回がありました。回数は少なく、確かめた Skill は古い版です。モデルごとの結果は、[モデルを選ぶ](docs/environments.md#モデルを選ぶ)にあります。
- OpenCode と Hermes Agent は、モデルを介した動作を、十分には確かめていません。手元のローカルモデルでは、Skill の発見と読み込みを確かめました。ただし、スクリプトが動かない回と、モード C が守られない回がありました。ホスト型の主要モデルと、Hermes のターミナルが Docker や SSH の場合は、確かめていません([確認の記録](docs/opencode-hermes-checks.md))。
- 各製品の仕様は、[環境別の対応](docs/environments.md)に書いた確認日以降に変わる可能性があります。確認できなかった項目は、同じ文書で「未確認」としています。

## ドキュメント

| ファイル | 内容 |
|---|---|
| [docs/installation.md](docs/installation.md) | インストール、配置先、OpenCode と Hermes Agent の導入と検証、SudachiPy の入れ方、更新、削除 |
| [docs/environments.md](docs/environments.md) | 環境ごとの対応表と注意、参照した公式資料 |
| [docs/usage.md](docs/usage.md) | モードの指定の扱いと、動作の確認 |
| [docs/scripts.md](docs/scripts.md) | 計測と照合のスクリプトの使い方と限界 |
| [docs/kokugo.md](docs/kokugo.md) | 国語の表記・用法の検査。適用設定、区分、終了コード、JSON の形式、用語集、規則の更新、限界 |
| [docs/design.md](docs/design.md) | 設計の考え方と、参考にした記事とプロジェクト |
| [docs/development.md](docs/development.md) | ディレクトリ構成、パッケージ生成、検証、テスト |

実測の記録は、次の4つです。

- [ChatGPT Work の実機確認](docs/chatgpt-work-checks.md)
- [ChatGPT Work の暗黙起動の実測](docs/chatgpt-implicit-invocation.md)
- [モードの指定の動作確認](docs/mode-specification-checks.md)
- [OpenCode と Hermes Agent の対応確認](docs/opencode-hermes-checks.md)

## 参考とライセンス

日本語可読性の設計原則は、3つの記事と3つのリポジトリを参考にしました。記事とリポジトリの一覧(ライセンスを含む)と、何を取り入れたかは、[設計](docs/design.md)にあります。

ライセンスは [MIT](LICENSE) です。
