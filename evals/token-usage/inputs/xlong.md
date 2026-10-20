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

## 更新する

入れた方法に合わせて、[更新手順](docs/installation.md#更新する)を選んでください。

| 入れた方法 | 更新方法 |
|---|---|
| `tools/install.py` でコピー | リポジトリを `git pull` し、同じ配置先へ `--on-conflict backup` を付けて再配置する |
| `tools/install.py --link` | `git pull` で正本を更新する |
| ZIP・生成物のアップロード | [最新の Release](https://github.com/Mr-Kondo/japanese-readability-editor/releases/latest) の生成物に置き換える |
| Claude Code のプラグイン | マーケットプレースを更新してから、プラグインを更新する |

## クイックスタート

### Codex、Claude Code などに入れる

Python 3.10 以上と Git が必要です。まずリポジトリを取得します。

```bash
git clone https://github.com/Mr-Kondo/japanese-readability-editor.git
cd japanese-readability-editor
```

Windows では、`python3` を `python` に読み替える場合があります([Python のコマンド名](docs/installation.md#python-のコマンド名))。

使う環境の `--target` を選びます。

| 環境 | `--target` |
|---|---|
| Codex、GitHub Copilot、Gemini CLI | `common` |
| Claude Code | `claude-code` |
| Antigravity(IDE と CLI) | `antigravity` |
| OpenCode | `opencode` |
| Hermes Agent | `hermes` |

次は Codex などの共通配置に入れる例です。`common` を上の表の値に替えてください。複数なら `common,claude-code` のように指定できます。

```bash
python3 tools/install.py --scope user --target common --dry-run
```

表示された配置先を確認し、問題がなければ実行します。

```bash
python3 tools/install.py --scope user --target common
```

既に入っている場合は、[更新手順](docs/installation.md#更新する)を使います。特定のプロジェクトへの導入や、複数環境にまとめて入れる方法は、[インストールの詳細](docs/installation.md#インストールする)にあります。

### OpenCode、Hermes Agent に入れる

上の手順で `--target opencode` または `--target hermes` を指定します。環境変数やプロファイルによって配置先が変わるため、`--dry-run` の出力を確認してください。既存の共通配置との重複や、プロジェクトへの導入条件は、[環境固有の設定](docs/installation.md#opencode-と-hermes-agent-に入れる)にあります。

### ChatGPT Work、Claude Cowork、Gemini Apps に入れる

[最新の Release](https://github.com/Mr-Kondo/japanese-readability-editor/releases/latest) の生成物を、各製品の画面からアップロードします。リポジトリの取得は不要です。[アップロードするものと手順](docs/installation.md#アップロード型の環境に入れる)を確認してください。

### そのほかの手順

- [特定のプロジェクトに入れる](docs/installation.md#特定のプロジェクトに入れる)
- [動作を確認する](docs/installation.md#動作を確認する)
- [削除する](docs/installation.md#削除する)
- [Claude Code のプラグインとして入れる](docs/environments.md#プラグインとして入れる)
- [gh skill（GitHub CLI）で入れる](docs/installation.md#github-cligh-skillで入れる)（v0.15.0 以降。名前だけで入り、`gh skill update` で更新を確かめられます）

## 使い方

コピーして使える依頼例と、結果を確認する手順は、[実践ガイド](docs/user-guide.md)にあります。

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

4つのモードがあります。

- **A. 新規生成**: 読者、必要な情報、結論などを整理してから書きます。
- **B. Rewrite**: 意味を保ちながら書き換えます。
- **C. Paragraph-only**: 文章を変えずに、既存の空白・改行を保ち、改行と空行だけを挿入します。
- **D. 小説モード**: `plan`(構想)、`draft`(新規)、`continue`(続き)、`revise`(推敲)、`critique`(批評)を使い分け、作者の語り口と物語の効果を守ります。

通常は完成した文章だけを返します。「レビューして」「問題点を挙げて」「計測して」「before/after を比べて」と頼んだときだけ、診断情報を示します。

### モードを指定する

モードは、依頼の中で、記号か名前を挙げて指定できます。指定したときは、依頼の言い回しからの推測より、指定が優先されます。

| モード | 指定の例 |
|---|---|
| A. 新規生成 | `モード A`、`新規生成モードで` |
| B. Rewrite | `モード B`、`Rewrite モードで` |
| C. Paragraph-only | `モード C`、`paragraph-only モードで` |
| D. 小説モード | `モード D`、`小説モード`、`fiction mode` |

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

### 小説モードの依頼例

- 「小説モードで、この設定から冒頭の一場面を書いて」
- 「小説モードで続きを。視点人物が知っている情報だけで描写して」
- 「小説モードで推敲。出来事と口調、比喩、結末は変えないで」
- 「小説モードで批評だけ。本文は書き換えないで」
- 「モードC。この小説は文言を変えず、改行だけ加えて」

小説には短文化・比喩の説明化・時制統一を一律に適用しません。通常 `draft`/`continue`/`revise` は完成本文だけ、`critique` は本文を変えない批評です。指定の扱い(小説という語だけでは D にしない、操作が不明なら最小変更の `revise` など)は[使い方の詳細](docs/usage.md#小説モード-d)にあります。[小説の契約](skills/japanese-readability-editor/references/fiction-writing.md)、任意の [文脈メモ](skills/japanese-readability-editor/assets/fiction-context-template.md)、[補助検査](skills/japanese-readability-editor/references/fiction-checks.md)、[設計参考と限界](docs/fiction-design.md)を参照できます。

D のモデル挙動・評価の実施範囲は [評価ケース](evals/README.md)に記録します。既存製品の確認記録を、D の検証結果としては扱いません。

### 国語の表記・用法の検査

文化庁の公式資料に基づく表記・用法の規則を、適用設定(モードとは独立)に応じて文章へ当てられます。適用設定は、`general-tech`(既定)、`public-explanation`、`official` の3つです。規則には出典があり、公式資料の規定と、この skill の運用判断を区別しています。

実行方法、適用設定の使い分け、指摘の区分、終了コード、限界は、[国語の表記・用法の検査](docs/kokugo.md)にあります。

## 注意

- 国語の表記の検査は、規則に登録した語・表記を探すだけです。『指摘なし』は『規則に違反していない』ことを意味しません([限界](docs/kokugo.md#検査していないもの限界))。
- Skill は文章の意味を検証しません。意味の保存を保証するのは、Agent の判断と、利用者の確認です。返ってきた文章は、元の文と突き合わせて確認してください。
- ChatGPT での実機確認では、二重否定の意味の反転、残余の条件の言い換え、文体の変更が起きました。`SKILL.md` に対策を入れましたが、誤りを完全には防げません。
- ChatGPT の暗黙起動は、実測では不安定でした。確実に使うには、`@` で指定してください([実測](docs/chatgpt-implicit-invocation.md))。
- モードの指定は、Skill の指示です。環境の機能による強制ではなく、守られるかどうかは、環境とモデルによります。Codex(Medium)では、貼り付けた文章の中の「モード C」を、指定と取り違える回がありました。Antigravity、Claude Cowork、Gemini CLI、Gemini Apps では、確かめていません([動作の確認](docs/usage.md#動作の確認))。
- Claude のアプリでは、モデルによって結果が違いました。Haiku 4.5 では、Skill を読み込んでも、文体を敬体に変えるなど、規則が守られない回がありました。回数は少なく、確かめた Skill は古い版です。モデルごとの結果は、[モデルを選ぶ](docs/environments.md#モデルを選ぶ)にあります。
- OpenCode と Hermes Agent は、手元のローカルモデルでしか確かめていません。Skill の発見と読み込みは動きましたが、スクリプトが動かない回と、モード C が守られない回がありました。ホスト型の主要モデルは未確認です([確認の記録](docs/opencode-hermes-checks.md))。
- 各製品の仕様は、[環境別の対応](docs/environments.md)に書いた確認日以降に変わる可能性があります。確認できなかった項目は、同じ文書で「未確認」としています。

## ドキュメント

| ファイル | 内容 |
|---|---|
| [docs/installation.md](docs/installation.md) | インストール、配置先、OpenCode と Hermes Agent の導入と検証、SudachiPy の入れ方、更新、削除 |
| [docs/environments.md](docs/environments.md) | 環境ごとの対応表と注意、参照した公式資料 |
| [docs/user-guide.md](docs/user-guide.md) | コピーして使える依頼例、ファイルの編集・レビュー、小説の5操作、結果の確認、困ったときの対処 |
| [docs/user-guide-validation.md](docs/user-guide-validation.md) | 実践ガイドの実行結果、Claude Codeの繰り返し試験、環境設定の確認と未完了の範囲 |
| [docs/usage.md](docs/usage.md) | モードの指定の扱いと、動作の確認 |
| [docs/scripts.md](docs/scripts.md) | 計測と照合のスクリプトの使い方と限界 |
| [docs/kokugo.md](docs/kokugo.md) | 国語の表記・用法の検査。適用設定、区分、終了コード、JSON の形式、用語集、規則の更新、限界 |
| [docs/design.md](docs/design.md) | 設計の考え方と、参考にした記事とプロジェクト |
| [docs/feedback.md](docs/feedback.md) | 結果の問題を報告する手順と、メンテナーが改良に使う手順。同意、送付、保管、効果の根拠と限界 |
| [docs/upstream-watch.md](docs/upstream-watch.md) | 参考にしたリポジトリの更新を、定期的に確認して解析・Issue・改良へつなぐ仕組み。登録簿、自動化の段階、信頼できない入力の扱い、他のプロジェクトでの使い方 |
| [docs/development.md](docs/development.md) | ディレクトリ構成、パッケージ生成、検証、テスト。評価用ツール（[文章評価](docs/human-evaluation.md)、[公開文書](docs/public-document-evaluation.md)、[Ragas](docs/ragas-evaluation.md)）への入口 |

実測の記録は、次の4つです。

- [ChatGPT Work の実機確認](docs/chatgpt-work-checks.md)
- [ChatGPT Work の暗黙起動の実測](docs/chatgpt-implicit-invocation.md)
- [モードの指定の動作確認](docs/mode-specification-checks.md)
- [OpenCode と Hermes Agent の対応確認](docs/opencode-hermes-checks.md)

## 参考とライセンス

日本語可読性の設計原則は、3つの記事と3つのリポジトリを参考にしました。記事とリポジトリの一覧(ライセンスを含む)と、何を取り入れたかは、[設計](docs/design.md)にあります。

ライセンスは [MIT](LICENSE) です。
# インストール

既に使っている場合は「[更新する](#更新する)」へ進んでください。初めて入れる場合は、使う環境に合わせて手順を選びます。

- [Codex、Claude Code などにインストールする](#必要なもの)
- [ChatGPT Work、Claude Cowork、Gemini Apps にアップロードする](#アップロード型の環境に入れる)
- [gh skill（GitHub CLI）で入れる](#github-cligh-skillで入れる)
- [動作を確認する](#動作を確認する)
- [OpenCode と Hermes Agent の配置先・重複を確認する](#opencode-と-hermes-agent-に入れる)
- [削除する](#削除する)
- [SudachiPy を入れる（任意）](#sudachipy-を入れる任意)

手早く入れる場合は、README の「[クイックスタート](../README.md#クイックスタート)」を使ってください。

## 更新する

入れている版は、`python3 scripts/skill_info.py --version` で確かめられます(Skill のフォルダで実行します。例: `japanese-readability-editor 0.17.0`)。最新の版は、[Releases のページ](https://github.com/Mr-Kondo/japanese-readability-editor/releases)にあります。

### コピーで入れた場合

取得済みリポジトリのディレクトリで `git pull` し、`--on-conflict backup` を付けて配置し直します。以前の版は退避されます。

`--scope`、`--target` と、配置先を指定する引数は、インストール時と同じ値にしてください。以下は `--target all` で入れた場合の例です。

```bash
git pull
python3 tools/install.py --scope user --target all --on-conflict backup
```

内容が変わっていなければ、`--on-conflict backup` を付けても、退避は作りません。変わったときだけ、以前のものを `skills.bak/` へ退避して、置き直します。

OpenCode と Hermes も、同じです。配置先を指定した引数は、インストールしたときと同じにします。

```bash
python3 tools/install.py --scope user --target opencode --on-conflict backup
python3 tools/install.py --scope user --target hermes --on-conflict backup
```

### リンクで入れた場合

`--link` でインストールした場合は、複製ではなく正本へのリンクなので、`git pull` だけで反映されます。ただし、リポジトリを移動すると、リンクが切れます。

複製で入れたものをリンクに切り替える場合は、`--on-conflict backup` を付けます。付けないと、既にある複製を残したまま、何もせずに終わります。

```bash
python3 tools/install.py --scope user --target all --link --on-conflict backup
```

### アップロードで入れた場合

アップロード型の環境では、新しい ZIP を、もう一度アップロードします。ZIP は、Release からダウンロードするか、`python3 tools/package.py` で作ります。

ChatGPT では、同じ名前の Skill があると、置き換えの確認(Skill already exists)が出ます。「Replace existing」を選ぶと、同じ Skill が更新されます。重複はしません。置き換えた後の表示は、[実機確認](chatgpt-work-checks.md#同じ名前の-skill-の置き換え)にあります。

Claude のアプリでは、Skill の詳細画面から置き換えます。2026-10-07 に、Pro プランのアカウントで確かめました。

1. Customize → Skills で、`japanese-readability-editor` を開きます。
2. 右上の「⋮」から「Replace」を選びます。
3. 新しい ZIP を選び、「Upload」を押します。アップロードのときに、セキュリティスキャンが走ります。

置き換えると、同じ Skill の版が1つ上がります(v1 から v2 など)。有効のままです。一覧の行の「⋮」には、「Replace」がありません。置き換えた直後は、前の版の内容が表示されることがあります。ページを再読み込みすると、新しい版が表示されます。

### Claude Code のプラグインで入れた場合

Claude Code のプラグインとして入れた場合は、マーケットプレースを更新してから、プラグインを更新します。

```bash
claude plugin marketplace update japanese-readability-editor
claude plugin update japanese-readability-editor@japanese-readability-editor
```

`claude plugin update` だけでは、更新されません。手元に取得したマーケットプレースが古いままなので、「already at the latest version」と表示されます。更新した後は、Claude Code を再起動します。

プラグインの版は、コミットの短いハッシュで表示されます。`claude plugin list` の `Version` で確かめられます。

### gh skill で入れた場合

v0.15.0 以降（`skills/` の配置）で入れたものは、`gh skill update` で更新を確かめられます。入れ先を `--dir` で指定したときは、`gh skill update --dry-run --dir <入れ先>` で確かめます。

- gh は、Skill のディレクトリ（`skills/japanese-readability-editor/`）の内容の差（tree sha）で判定します。**docs や tools だけが変わったリリースは、更新として検出されません**（v0.15.0 から v0.15.1 で、「All skills are up to date.」を確認しました）。
- 更新の検出は、`github-tree-sha` を変えて版が古い入れ方を模擬して確かめました（「1 update(s) available」）。実際の更新（`--all`）は、Skill の内容が変わる次のリリースで確かめます。

v0.14.0 以前の `skill/` の配置で入れたものは、`gh skill update` が見つけられません（「no skills found」と出して飛ばし、「All skills are up to date.」と表示します）。[GitHub CLI（gh skill）で入れる](#github-cligh-skillで入れる)のコマンドで、入れ直してください。

### 退避した版へ戻す

退避したものは、元の場所へ戻せば復元できます。インストーラの出力に、退避先の名前(`japanese-readability-editor-<日時>`)が出ます。置き直したものを消してから、退避したものを戻します。

```bash
rm -r ~/.hermes/skills/japanese-readability-editor
mv ~/.hermes/skills.bak/japanese-readability-editor-20261010-120000 ~/.hermes/skills/japanese-readability-editor
```

## 必要なもの

- Python 3.10 以上
- Git(リポジトリを取得する場合)
- SudachiPy と辞書(任意。`compare_rewrite.py` の判定を正確にする)

インストーラも検証ツールも、Python の標準ライブラリだけで動きます。SudachiPy は、入っていなくても動きます。入れ方は、環境によって違います(「[SudachiPy を入れる](#sudachipy-を入れる任意)」)。

### Python のコマンド名

この文書のコマンドは、`python3` で書いています。Windows では、`python3` ではなく `python` で実行する場合があります。その場合は、`python3` を `python` に読み替えてください。

```bash
python --version
```

`Python 3.10` 以上と表示されれば、使えます。このリポジトリの CI も、Windows を含む全 OS で `python` を使っています。

## 取得する

```bash
git clone https://github.com/Mr-Kondo/japanese-readability-editor.git
cd japanese-readability-editor
```

リポジトリの公開範囲によっては、GitHub の認証が必要です。認証済みの `gh` があれば、次のコマンドでも取得できます。

```bash
gh repo clone Mr-Kondo/japanese-readability-editor
```

## Skill を検証する

```bash
python3 tools/validate_skill.py
```

`OK:` と表示されれば、配置できる状態です。

## インストールする

まず `--dry-run` で、配置先を確認します。何も書き込みません。

```bash
python3 tools/install.py --scope user --target all --dry-run
```

使う環境だけに入れる場合は、次の表から引数を選びます。`--dry-run` を付けて配置先を確認し、問題がなければ外して実行してください。

| 使う環境 | ユーザー全体に入れる | 特定のプロジェクトに入れる |
|---|---|---|
| Codex、Copilot、Gemini CLI | `--scope user --target common` | `--scope workspace --target common` |
| Claude Code | `--scope user --target claude-code` | `--scope workspace --target claude-code` |
| Antigravity(IDE と CLI) | `--scope user --target antigravity` | `--scope workspace --target common` |
| OpenCode | `--scope user --target opencode` | `--scope workspace --target opencode` |
| Hermes Agent | `--scope user --target hermes` | `--scope workspace --target hermes`(使う前に `hermes skills trust` が要る) |
| OpenCode・Hermes 以外をまとめて | `--scope user --target all` | `--scope workspace --target all` |

`all` に、OpenCode と Hermes Agent は含みません。使っていない製品の設定ディレクトリを、ホームに作らないためです。OpenCode と Hermes の導入は、「[OpenCode と Hermes Agent に入れる](#opencode-と-hermes-agent-に入れる)」にあります。

たとえば、Codex と Claude Code をユーザー全体で使う場合は、次のとおりです。

```bash
python3 tools/install.py --scope user --target common,claude-code
```

`--target` は、繰り返しても、カンマ区切りでも指定できます。同じ場所になる target は、1回だけ配置します。

配置先に同名の Skill が既にある場合は、何も変更しません。上書きするときの選び方は、「[安全な挙動](#安全な挙動)」にあります。

### 特定のプロジェクトに入れる

`--workspace` に、そのプロジェクトのパスを指定します。省くと、カレントディレクトリが対象です。

```bash
python3 tools/install.py --scope workspace --target all --workspace /path/to/project
```

共通配置の `.agents/skills/` に置くと、Codex、Copilot、Gemini CLI、Antigravity が読みます。Claude Code だけは `.claude/skills/` が必要です。

`--target all` は、`.agents/skills/` と `.claude/skills/` の2か所に配置します。Copilot は両方を読むので、同じ Skill が2つ見える可能性があります。Copilot を使うプロジェクトでは、必要な環境だけを指定してください。

### 配置先

| target | workspace scope の配置先 | user scope の配置先 |
|---|---|---|
| `common`、`codex`、`copilot`、`gemini-cli` | `.agents/skills/` | `~/.agents/skills/` |
| `claude-code` | `.claude/skills/` | `~/.claude/skills/` |
| `antigravity-ide` | `.agents/skills/` | `~/.gemini/config/skills/` |
| `antigravity-cli` | `.agents/skills/` | `~/.gemini/antigravity-cli/skills/` |
| `antigravity` | `.agents/skills/` | 上の2つ(IDE と CLI) |
| `opencode` | `.opencode/skills/` | `$OPENCODE_CONFIG_DIR`、`$XDG_CONFIG_HOME/opencode`、`~/.config/opencode` の `skills/`([詳細](#opencode-の配置先)) |
| `hermes` | `.hermes/skills/` | Hermes のホームの `skills/`(`HERMES_HOME`、プロファイル、`~/.hermes`。[詳細](#hermes-agent-の配置先)) |
| `all` | `.agents/skills/` と `.claude/skills/` | `common`、`claude-code`、`antigravity-ide`、`antigravity-cli` の配置先。`opencode` と `hermes` は含まない |

各製品が Skill を探す場所は、ほかにもあります。一覧は、[環境別の対応](environments.md#対応表)にあります。

### 安全な挙動

- 配置先の内容が正本と同じなら、何もしません。`--on-conflict` の値によらず、再実行しても退避や書き込みは起きません(`up to date` と表示します)。
- 内容が違うものが既にある場合も、何もしません(`--on-conflict skip`、既定)。違うファイルの名前(`missing`、`extra`、`changed`)を表示します。
- `--on-conflict backup` は、内容の違う既存のものを `skills.bak/` へ退避してから配置します。退避先は Skill の探索先の外で、退避したものは、そのまま元の場所へ戻せます。
- `--on-conflict overwrite` は、内容の違う既存のものを削除して配置します。`SKILL.md` を持たないディレクトリは、削除を拒否します。
- 配置は、複製が終わってから所定の場所へ移すので、途中で失敗しても中途半端なものを残しません。
- 既定はコピーです。`--link` でシンボリックリンクにできます。Windows では権限が必要な場合があります。Hermes の Docker や SSH などの backend には、リンクは送られません(Hermes のソースの読み取り。実機では未確認)。
- コピーで配置した直後(`--link` のときを除く)に、構造、メタデータ、参照先、正本との一致を確かめます(`verify   OK`)。スクリプトまで実行して確かめるには、「[配置した Skill を検証する](#配置した-skill-を検証する)」を使います。

## アップロード型の環境に入れる

ChatGPT Work、Claude Cowork、Gemini Apps は、配置先のディレクトリを持ちません。生成物を用意して、各製品の画面からアップロードします。

生成物は、次のどちらかで用意します。

- [最新の Release](https://github.com/Mr-Kondo/japanese-readability-editor/releases/latest) からダウンロードする(リポジトリの取得は不要)
- 手元で作る

Release からダウンロードするコマンドは、次のとおりです。ダウンロード後に、SHA-256 を照合できます。

```bash
gh release download --repo Mr-Kondo/japanese-readability-editor --pattern 'japanese-readability-editor.*'
shasum -a 256 -c japanese-readability-editor.sha256
```

`--pattern` は、タグを指定しないときに必須です。

手元で作るコマンドは、次のとおりです。

```bash
python3 tools/package.py
```

Release に添付されるのは、ZIP、SHA-256、Gemini Apps 向けの指示文(`gemini-apps-instructions.md`)です。Gemini Apps 向けのフォルダは添付されないので、必要なら手元で作ります。

| 環境 | アップロードするもの | 手順 |
|---|---|---|
| ChatGPT Work | `dist/japanese-readability-editor.zip` | [ChatGPT Work](environments.md#chatgpt-work) |
| Claude Cowork | `dist/japanese-readability-editor.zip` | [Claude Cowork](environments.md#claude-cowork) |
| Gemini Apps | `dist/gemini-apps/japanese-readability-editor/`、または `dist/gemini-apps-instructions.md` の貼り付け | [Gemini Apps](environments.md#gemini-apps) |

## GitHub CLI（gh skill）で入れる

`gh skill`（GitHub CLI のプレビュー機能。予告なく変わる）で入れられます。確かめたのは、gh 2.102.0、macOS、2026-10-19 です。

```bash
gh skill install Mr-Kondo/japanese-readability-editor japanese-readability-editor --dir <入れ先の skills ディレクトリ>
```

- **名前だけで入ります。** `skills/japanese-readability-editor/SKILL.md` という配置が、gh の探す場所（`skills/*/SKILL.md`）に当たるためです。`--pin <タグまたはコミット>` で版を固定できます。
- 版を指定しないと、最新のタグ付きリリースが入ります。
- **v0.14.0 以前のタグは、`skill/`（単数）の配置です。** 名前だけでは見つからないので、そのときは `skill/japanese-readability-editor/SKILL.md` のパスを指定してください。
- 入った内容は、`SKILL.md`、`scripts/`（8 本）、`references/`、`assets/`、`data/` です。
- gh は `SKILL.md` の frontmatter に、`metadata:`（`github-repo`、`github-ref`、`github-path`、`github-tree-sha`）を足します。このリポジトリの `tools/validate_skill.py` は、frontmatter の複数行の値を認めないので、gh で入れたものには使えません（エラーになります）。
- `--agent` と `--scope` で入れ先を選ぶ形は、`gh skill install --help` にありますが、確かめていません。確かめたのは `--dir` だけです。
- `npx skills add` は、確かめていません。

## 動作を確認する

環境ごとに、Skill が読み込まれたかを確認します。表示されない場合は、セッションを開き直してください。

| 環境 | 確認方法 |
|---|---|
| Codex | `/skills` の一覧に出る。`$japanese-readability-editor` で呼べる |
| Claude Code | `/` のメニューに `japanese-readability-editor` が出る |
| Gemini CLI | `/skills list`、または端末で `gemini skills list`。追加した直後は `/skills reload` |
| Antigravity | `/japanese-readability-editor` で呼べる |
| GitHub Copilot | 公式資料に確認方法の記載を見つけられなかったため、次の依頼で試す |
| OpenCode | 一覧するコマンドは、手元の 2.0.20 には見つけられなかった。`opencode serve` を起動し、`OPENCODE_PASSWORD` に起動時のパスワードを設定して `opencode api --server <URL> GET /api/skill` を 3 回以上呼ぶと、一覧が取れた。`python3 tools/verify_install.py --scope user --target opencode` で配置を確かめ、依頼して試す |
| Hermes Agent | `hermes skills list` の一覧に出る。セッションで `/japanese-readability-editor` を呼べる。プロファイルを使うなら、同じ `-p` を付ける |

どの環境でも、実際に依頼して確かめられます。

```text
次の文章を japanese-readability-editor で校正して。
「このシステムは、ユーザーから入力されたデータを受け取り、それを検証したうえで、問題がなければデータベースに保存し、問題があればエラーとして呼び出し元に返す。」
```

## OpenCode と Hermes Agent に入れる

どちらも、先に `--dry-run` で、配置先と決め方を確かめます。何も書き込みません。

```bash
python3 tools/install.py --scope user --target opencode --dry-run
python3 tools/install.py --scope user --target hermes --dry-run
```

出力の `decided by:` に、配置先をどう決めたかが出ます。問題がなければ、`--dry-run` を外します。

```bash
python3 tools/install.py --scope user --target opencode
python3 tools/install.py --scope user --target hermes
```

配置先のパスは、空白や日本語を含んでいてもかまいません。

### OpenCode の配置先

| 範囲 | 配置先 | 読まれる条件 |
|---|---|---|
| プロジェクト | `<プロジェクト>/.opencode/skills/japanese-readability-editor/` | OpenCode を、そのプロジェクトの中(git の worktree の中)で起動したとき |
| ユーザー全体 | 下の順で決まる `skills/japanese-readability-editor/` | 常に |

ユーザー全体の配置先は、次の順に決めます。先に当てはまったものを使います。

1. `--opencode-config-dir PATH` の `PATH/skills/`
2. 環境変数 `OPENCODE_CONFIG_DIR` の `skills/`
3. 環境変数 `XDG_CONFIG_HOME` の `opencode/skills/`
4. `~/.config/opencode/skills/`

OpenCode は、`XDG_CONFIG_HOME` の設定ディレクトリと `OPENCODE_CONFIG_DIR` の両方を探します。どちらに置いても読まれます(`OPENCODE_CONFIG_DIR` は公式文書、`XDG_CONFIG_HOME` と両方を探す点は OpenCode 1.x 系のソースによる。手元の 2.0.20 では、`XDG_CONFIG_HOME` の設定ディレクトリに置いた Skill が読まれることを確かめました。`OPENCODE_CONFIG_DIR` は確かめていません)。

OpenCode は、`.agents/skills/` と `.claude/skills/` も読みます(公式文書)。`--target common` や `claude-code` で入れた Skill も、OpenCode から見えます。そこに入れてあるなら、OpenCode のために入れ直す必要はありません。両方に置くと、同名の Skill が重複します。

### Hermes Agent の配置先

ユーザー全体の配置先は、実際に使われる Hermes のホームの `skills/` です。ホームは、次の順に決めます。先に当てはまったものを使います。Hermes 本体の決め方に合わせています。

1. `--hermes-home PATH` の `PATH/skills/`
2. `--profile NAME` のプロファイル(`<根>/profiles/NAME/skills/`。`default` は根)。プロファイルが存在しないときは、何も書かずに終わります
3. 環境変数 `HERMES_HOME` が `profiles/<名前>` を指しているなら、そのプロファイル
4. `<根>/active_profile` に `default` 以外の名前があれば(`hermes profile use` で決めたもの)、そのプロファイル
5. 環境変数 `HERMES_HOME`
6. `~/.hermes/skills/`(Windows は `%LOCALAPPDATA%\hermes\skills\`)

`--home` を指定したときは、`HERMES_HOME` と `XDG_CONFIG_HOME` などの環境変数を使いません。別のホームを丸ごと指定したものとして扱います。配置先は、実行のたびに表示します。

プロファイルは、別の Skill の置き場を持ちます。使っているプロファイルとは別のプロファイルに入れた Skill は、そのプロファイルで Hermes を起動するまで見えません。

プロジェクトに入れるときは、`--scope workspace --target hermes` で、`<プロジェクト>/.hermes/skills/` に置きます。Hermes は、`.git` を持つ最も近い祖先を、プロジェクトの根とします。リポジトリを信頼するまで、読み込みません。信頼は利用者の判断なので、このツールは実行しません。

```bash
cd /path/to/project
hermes skills trust
```

Hermes のターミナルが Docker、SSH、Modal、Daytona のときも、Skill は複製で入れます。`hermes skills install` では入れられません。取り込む範囲に `data/` が入らず、国語の検査が動かなくなるためです。手元の v0.21.0 で確かめたのは URL 経由の取り込みで、GitHub の識別子を使う経路は、文書の記述によります([確認の記録](opencode-hermes-checks.md#判断))。

### 配置先を直接指定する

`--dest DIR` は、skills ディレクトリを直接指定します。`DIR/japanese-readability-editor/` に置きます。`--scope` の代わりに使います。

```bash
python3 tools/install.py --dest "/path with spaces/skills" --target opencode
```

`--target` は、`opencode` か `hermes` を付けたときだけ、検証と重複の確認の基準になります。

### 重複を確かめる

同じ Skill が、その製品の別の探索先でも見つかると、`warn` で知らせます。内容が正本と同じか違うかも示します。何も削除しません。どれを残すかは、利用者が決めます。

- OpenCode: `.claude/skills/`、`.agents/skills/`、`.opencode/skills/`、設定ディレクトリの `skills/`。プロジェクトは、作業ディレクトリから git の根まで見ます。OpenCode は、同名のうち 1 つしか使いません。どれが使われるかは、当てになりません。
- Hermes: ホームの `skills/`、`config.yaml` の `skills.external_dirs` と `skills.create_dir`、信頼したプロジェクトの `.hermes/skills/` と `.agents/skills/`。Hermes は、プロジェクト、プロファイル、`create_dir`、`external_dirs` の順で上位を使い、下位を隠します。同じ階層に内容の違うものが 2 つあると、曖昧としてエラーになります。

### 配置した Skill を検証する

`tools/verify_install.py` は、配置した Skill を検証します。何も変更せず、何もインストールしません。

```bash
python3 tools/verify_install.py --scope user --target opencode
python3 tools/verify_install.py --scope user --target hermes --profile coder
python3 tools/verify_install.py "/path/to/skills/japanese-readability-editor" --target hermes
```

| 検証 | 内容 |
|---|---|
| 構造とメタデータ | `SKILL.md` の名前と形式、`name` とディレクトリ名の一致、`SKILL.md` が参照するファイルの存在、公式仕様の制約(名前の形式、`description` の長さ) |
| 内容 | 正本との差。ファイルの欠け、余分なファイル、内容の違い |
| 実行 | カレントディレクトリが Skill でもリポジトリでもない、空白と日本語を含むディレクトリから、5 つのスクリプト(`measure.py`、`verify_preservation.py`〈通常と `--strict`〉、`compare_rewrite.py`、`check_kokugo.py`、`validate_kokugo_rules.py`)を実行する。`--no-run` で省く |
| 依存 | Python 3.10 以上か。SudachiPy が入っているか(`tokenizer` で分かる)。入れはしない |
| 重複 | 同じ Skill が別の探索先にないか |

終了コードは、問題なしなら 0、誤りがあれば 1、引数が不正なら 2 です。警告(古い版、重複)では、1 にしません。正本との比較を省くときは、`--no-source` を付けます。正本との差を誤りとして扱うときは、`--strict-source` を付けます。実行するスクリプトの Python は、`verify_install.py` を動かした Python です。エージェントが使う Python で実行してください。

### リポジトリなしで入れる

`python3 tools/package.py` は、`dist/opencode/` と `dist/hermes/` に、配布物を作ります。どちらも、Skill のフォルダ(正本の完全な複製)と、配置先とコマンドを書いた `INSTALL.md` からなります。作ったあとに、`verify_install.py` で検証します。

```text
dist/opencode/
├── INSTALL.md
└── japanese-readability-editor/
dist/hermes/
├── INSTALL.md
└── japanese-readability-editor/
```

リポジトリを取得している別の場所で配布物を作り、フォルダごと、対象のマシンの skills ディレクトリへコピーします。`INSTALL.md` は、skills ディレクトリに置きません。

## 削除する

`tools/uninstall.py` で、配置先の `japanese-readability-editor/` を削除できます。配置先の指定は、インストーラと同じです(`--scope`、`--target`、`--workspace`、`--home`、`--dest`、`--hermes-home`、`--profile`、`--opencode-config-dir`)。インストールしたときと同じ値を指定してください。

まず `--dry-run` で、削除するものを確認します。何も削除しません。

```bash
python3 tools/uninstall.py --scope user --target all --dry-run
```

問題がなければ、`--dry-run` を外して実行します。

```bash
python3 tools/uninstall.py --scope user --target all
```

- 削除するのは、配置先の `japanese-readability-editor/` だけです。`skills/` ディレクトリと、ほかの Skill は残します。
- `--link` で入れた場合は、リンクだけを削除します。リンクの先にある正本は消えません。
- `SKILL.md` を持たないディレクトリと、このリポジトリの正本そのものは、削除を断ります。断った配置先があっても、ほかの配置先は処理します。終了コードは 1 になります。
- 配置先がなければ、何もしません。
- `--on-conflict backup` で退避したものは、`skills.bak/` に残ります。既定では削除しません。`--include-backups` を付けると、`japanese-readability-editor-<日時>/` を削除します。`skills.bak/` が空になれば、それも削除します。

次の環境で入れたものは、このスクリプトでは削除できません。

| 入れ方 | 削除の方法 |
|---|---|
| Claude Code のプラグイン | `claude plugin uninstall japanese-readability-editor@japanese-readability-editor` |
| ChatGPT Work、Claude Cowork、Gemini Apps | 各製品の画面から、アップロードしたものを削除する(手順は、この文書では確かめていません) |

## SudachiPy を入れる(任意)

`compare_rewrite.py` は、SudachiPy と辞書が入っていれば、否定と文の対応をより正確に判定します。入っていなければ、標準ライブラリだけで動きます。どちらで動いたかは、出力の `tokenizer` で分かります。

国語の表記の検査(`check_kokugo.py`)は、SudachiPy を使いません([限界](kokugo.md#検査していないもの限界))。

Skill は、利用者の手元の環境には、SudachiPy を断りなく入れません。実行中に入れるのは、利用者の手元ではない、クラウドの実行環境だけです。

| 環境 | 入れ方 |
|---|---|
| Codex、Claude Code、GitHub Copilot(CLI とエディタ)、Gemini CLI、Antigravity | 先に、手元の Python に入れておく(下のコマンド) |
| OpenCode、Hermes Agent(ターミナルが手元) | 先に、手元の Python に入れておく(下のコマンド)。入っていなければ、標準ライブラリで動く |
| Hermes Agent(ターミナルが Docker、SSH、Modal、Daytona) | その環境の Python が対象。入っていなければ、標準ライブラリで動く。入れるかどうかは、利用者が決める(未確認) |
| ChatGPT Work | Skill の指示で、エージェントが実行中に入れる。ネットワークを使える権限が必要([実機確認](chatgpt-work-checks.md#sudachipy-の導入)) |
| Claude のアプリ(Cowork を含む) | Skill の指示で、エージェントが実行中に入れる。入らなければ、標準ライブラリで動く(未確認。下の注) |
| Copilot のクラウドエージェント | `.github/workflows/copilot-setup-steps.yml` で、先に入れておく |
| Codex のクラウド環境 | 環境の setup script で、先に入れておく |
| Claude API | 入れられない。標準ライブラリで動く |
| Gemini Apps | スクリプトを実行しないので、関係しない |

手元の環境では、エージェントが呼ぶ Python に入れます。コマンド名は、`python3` です。Windows では、`python` の場合があります(「[Python のコマンド名](#python-のコマンド名)」)。

```bash
python3 -m pip install sudachipy sudachidict-core
```

Homebrew や Debian・Ubuntu の Python では、`externally-managed-environment` のエラーで断られます。その場合は、`--user --break-system-packages` を付けて、ユーザーの領域に入れます。Python 本体の領域には書き込みません。

```bash
python3 -m pip install --user --break-system-packages sudachipy sudachidict-core
```

ユーザーの領域は、Python の版ごとに分かれています。Python を 3.14 から 3.15 に上げたときなどは、もう一度入れてください。

Codex のサンドボックスでは、ネットワークを使えないので、エージェントが実行中に入れることはできません。先に入れておけば、サンドボックスの中でも使えます。macOS の Codex CLI 0.155.1 で、読み取り専用と workspace-write の両方を確認しました(2026-10-06)。

辞書は、core と small のどちらでも動きます。インストール後の大きさは、core が約190MB、small が約110MBです。2026-10-06 の測定では、当時の `assets/examples.md` の18組の修正例で、どちらも同じ指摘になりました。以降に増えた例では測っていません。クラウドの実行環境では、入れる時間を短くするために、Skill は small を使います。

SudachiPy と辞書は、ZIP には含めません。小さい small の辞書でも、配布用のファイルが約42MBあり、ChatGPT のアップロードの上限(1ファイルあたり25MB)を超えるためです。アップロード型の環境では、エージェントが実行中に small を入れます。入らなければ、標準ライブラリの経路で動きます。

注: Claude のアプリでは、まだ確かめていません。

- Claude のアプリでは、組織のネットワークの設定によります([Claude Help Center](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude))。Team の既定は、パッケージ管理ツール(PyPI など)だけを許可します。Enterprise の新しい組織では、既定で無効です。Cowork での扱いは、確認できていません。
- Copilot のクラウドエージェントでは、既定の許可リストに、Python のパッケージ置き場が含まれます([GitHub Docs](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-firewall))。
- Codex のクラウド環境では、setup script がネットワークを使えます。エージェントの実行中は、既定では使えません([Codex: Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment))。
# 実践ガイド：依頼例と結果の確認

`japanese-readability-editor` で日本語の文章を扱う実践ガイドです。新規作成、推敲、段落分け、小説の執筆を、コピーして使える依頼例で説明します。

Skill を導入済みの環境を前提にします。未導入なら、先に [インストール](installation.md)を済ませてください。このガイドは、リポジトリ内の [SKILL.md](../skills/japanese-readability-editor/SKILL.md)と[小説モードの操作契約](../skills/japanese-readability-editor/references/fiction-writing.md)に基づきます。

## まず短い文章で試す

Codex では、次の依頼をチャットへ貼り付けます。

```text
$japanese-readability-editor モード B
以下の文章を、意味と常体を保ったまま読みやすくして。
完成した文章だけを返して。

【対象本文】
ログ出力の確認を行うことができる。保存期間は30日である。
```

意味を保った書き換えの一例は、次のとおりです。モデルの出力が、この文と完全に一致する必要はありません。

```text
ログ出力を確認できる。保存期間は30日である。
```

確認するのは、「確認できる」という可能の意味、保存期間の「30日」、常体が残っていることです。「ログ出力を確認する」へ変わった場合は、可能の意味が失われています。

以下の依頼例も Codex の呼び方で書いています。他の環境では、先頭の `$japanese-readability-editor` を [README の呼び方](../README.md#使い方)に替えてください。Skill 名とモードを、同じメッセージの先頭に書きます。

## 目的からモードを選ぶ

| やりたいこと | 指定 | 渡すもの | 得られるもの |
|---|---|---|---|
| 説明書や案内を新しく書く | モード A | 読者、目的、伝える事実、希望する形式 | 新しい文章 |
| 既存文を読みやすくする | モード B | 原文、保つ情報、変更してよい範囲 | 意味を保った書き換え |
| 文言を変えずに段落を分ける | モード C | 原文 | 改行と空行を挿入した文章 |
| 小説の構想・本文・批評を作る | モード D ＋操作 | 設定、必要な本文、視点や変更範囲 | 操作に応じた構想・本文・批評 |

モードは、編集できる範囲を指定するものです。国語の表記を確認する `general-tech` などの適用設定とは別です。通常は完成した文章だけを返し、レビューや計測を依頼した場合は指摘を示します。

## モード A：事実を渡して新しく書く

読者と用途を指定し、文章に入れる事実を箇条書きで渡します。分からない内容を補ってほしくない場合は、その条件も書きます。

```text
$japanese-readability-editor モード A
社内の開発者向けに、検索APIの運用案内を書いて。
見出しと短い段落でまとめ、敬体にして。
以下の事実だけを使い、不明な仕様は補わないで。

【伝える事実】
- タイムアウトは5秒。
- 再試行は最大3回。
- 認証エラーでは再試行しない。
- タイムアウトが続く場合は、当番の担当者へ連絡する。
```

結果では、5秒・最大3回・認証エラーの例外が残っているかを確認します。接続先や連絡手段など、渡していない仕様が追加されていないかも見ます。

## モード B：意味を保って推敲する

### 貼り付けた文章を直す

依頼と対象本文を分けて書きます。数値だけでなく、条件、例外、断定の強さ、文体も保持対象として指定できます。

```text
$japanese-readability-editor モード B
以下の運用説明を読みやすくして。
数値、条件、例外、技術用語、常体は保って。
原文にない仕様や手順は追加しないで。
完成した文章だけを返して。

【対象本文】
検索APIがタイムアウトした場合には、最大3回まで再試行を行うことができる。
ただし、認証エラーが発生した場合には、再試行は行わない。
それ以外の場合は、当番の担当者による判断を必要とする。
```

「再試行できる」を「再試行する」に変えると、可能が実行の指示へ変わります。「それ以外の場合」を推測で具体化すると、条件の範囲が変わるおそれがあります。読みやすくなったかと、意味が残ったかを分けて確認します。

### プロジェクトのファイルを直接編集する

ファイルを読み書きできる環境では、対象パスと保存方法を指定します。次の `docs/report.md` は例です。実在する対象パスに替えてください。

```text
$japanese-readability-editor モード B
docs/report.md を読んで、日本語を推敲し、同じファイルへ保存して。
数値、条件、例外、固有名詞、コード、URL、引用、出典、常体を保って。
編集前の内容を一時ディレクトリに退避し、編集後に照合して。
照合が終わったら、一時ファイルは片付けて。
編集、照合、後片付けは別々に実行して。編集にはファイル編集ツールを使い、削除は今回作った退避ファイルだけに限定して。
最後に、変更した箇所と確認結果を短く報告して。
```

ファイルにアクセスできない環境では、本文を貼り付けるかファイルを添付し、「書き換えた本文を返して」と指定します。返された文章を保存する場合は、保存先と原文を確かめます。

### 問題点だけを確認する

修正前に判断したい場合は、本文を書き換えないことを指定します。

```text
$japanese-readability-editor モード B
docs/report.md の日本語をレビューして。ファイルは編集しないで。
重要度の高い順に、該当行、読みにくい理由、修正案を示して。
原文にない情報が必要な箇所は、補わずに要確認と示して。
```

この依頼では指摘と修正案が成果物です。ファイルへの反映を求める場合は、続けて対象と採用する修正を指定します。

## モード C：改行と空行だけを挿入する

文言、語順、句読点、既存の空白・タブ・改行を残して、段落の境界だけを加えるときに使います。

```text
$japanese-readability-editor モード C
以下の文章に、話題の境界で改行と空行を挿入して。
文言、句読点、空白、既存の改行は変えないで。
完成した文章だけを返して。

【対象本文】
検索APIの応答が遅くなった。原因は夜間バッチとの競合だった。対策として専用のレプリカを追加した。ただし、月額費用は約2万円増える。
```

挿入だけを行った一例です。

```text
検索APIの応答が遅くなった。原因は夜間バッチとの競合だった。

対策として専用のレプリカを追加した。

ただし、月額費用は約2万円増える。
```

ファイルを編集する場合は、対象パスを指定します。編集前の退避と、編集後の `verify_preservation.py --strict` による確認も依頼します。改行コードと BOM も保持するよう伝えます。BOM は、UTF-8 ファイルの先頭に付くことがある印です。

C と一緒に「誤字も直して」と頼んでも、C の変更範囲では誤字を直しません。表現の修正も必要なら、モード B に切り替えて依頼します。

## モード D：小説の操作を指定する

「小説モード」に加え、構想、新規、続き、推敲、批評のどれを求めるかを書きます。短い一場面なら、必要な設定を依頼に添えるだけで使えます。

| 操作 | 用途 | 本文の扱い |
|---|---|---|
| `plan`（構想） | 場面やプロットの案を作る | 提案は案として示す |
| `draft`（新規） | 設定から本文を書く | 新しい場面を書く |
| `continue`（続き） | 直前の本文につなげる | 続きだけを書くのが通常 |
| `revise`（推敲） | 既存の本文を整える | 標準は最小変更 |
| `critique`（批評） | 不整合や読解上の問題を示す | 本文を書き換えない |

### 構想を相談する

```text
$japanese-readability-editor 小説モードで構想（plan）
海沿いの無人駅で、帰れない二人が話す場面の案を二つ出して。
静かな雰囲気にしたい。二人の関係はまだ未確定。
本文は書かず、各案の展開と違いを示して。
提案を確定設定として扱わないで。
```

### 設定から新しい場面を書く

```text
$japanese-readability-editor 小説モードで新規（draft）
雨の無人駅を舞台に、冒頭の一場面を200〜300字で書いて。
語り手の一人称は「僕」。手に持っているのは切符だけ。
静かな雰囲気で、相手の正体はまだ明かさないで。
本文だけを返して。
```

### 直前の本文から続きを書く

```text
$japanese-readability-editor 小説モードで続き（continue）
次の本文に続く一場面を200〜300字で書いて。続きだけを返して。
空白・改行を除いて数え、200〜300字に収まることを確認してから返して。
一人称「僕」を保ち、川の向こうの人物の正体はまだ明かさないで。

【直前の本文】
夕方、橋の下。僕は左手で赤い傘を持ち、右足を水へ入れた。
```

続きでは、場所、時点、傘の色と持つ手、足の動きがつながっているかを確認します。視点人物が知らない相手の正体が、説明として追加されていないかも見ます。

### 語り口を保って推敲する

```text
$japanese-readability-editor 小説モードで推敲（revise）
以下の本文の誤字だけを直して。
比喩、反復、時制、一人称、結末、「……」は保って。
完成した本文だけを返して。

【対象本文】
夜が肺に溜まる。吐いても、吐いても。窓の外に雨。
僕は鍵をを握った。もう帰らない……。
```

この例で直すのは「鍵をを」の重複です。比喩を説明へ変えたり、文末や時制を一律にそろえたりしません。大幅な改稿を求める場合は、変更してよい要素と守る設定を指定します。

### 本文を書き換えずに批評する

```text
$japanese-readability-editor 小説モードで批評（critique）
以下の本文を批評して。本文は書き換えないで。
確定設定との不整合と、作風の好みを分けて示して。

【確定設定】
前の場面で鍵を机に置き、その後は取りに戻っていない。

【対象本文】
僕はポケットの鍵を握った。夜が肺に溜まる。
```

鍵の所在は、示された設定との不整合です。一方、比喩の好みは、それだけで設定の誤りにはなりません。長編では、[任意の小説メモ](../skills/japanese-readability-editor/assets/fiction-context-template.md)を使い、確定設定・未確定の案・人物の誤解を分けて渡せます。

小説にも、文言の完全保持を求めるならモード C を使います。モード A・B・C の明示指定は、「小説」という語があるだけでは D に切り替わりません。

## 国語の表記も確認する

通常の技術・業務文書には `general-tech` を使います。一般向けの案内には `public-explanation`、公用文の基準へ合わせると明示された文書には `official` を選びます。

```text
$japanese-readability-editor モード B
docs/report.md を推敲し、国語の表記は general-tech で確認して。
組織の用語集 glossary.txt を参照して。
専門用語、引用、コード、URLは保って。
文脈によって判断が変わる表記は、確定した誤りとして直さないで。
編集前の内容を一時ディレクトリに退避し、編集にはファイル編集ツールを使って。
表記検査、編集、照合、再検査、後片付けは別々に実行して。
削除は今回作った退避ファイルだけに限定し、権限が拒否されたら未完了の操作を報告して。
```

`docs/report.md` と `glossary.txt` は、実在するファイルに替えます。用語集がなければ、その指定を外します。用語集の形式と指摘の区分は、[国語の表記・用法の検査](kokugo.md)にあります。

## スクリプトで結果を確認する

文章の書き換えは Agent が行います。同梱のスクリプトは、確認候補を示すための読み取り専用ツールで、文章を自動修正しません。

以下は、リポジトリのルート（`README.md` と `tools/` がある場所）から実行する例です。Python 3.10 以上を使います。Windows などで `python3` が使えない場合は、`python` に読み替えてください。

### 同梱サンプルで確認方法を試す

次の入力は、リポジトリに含まれるテスト用文書です。そのまま実行できます。

```bash
python3 skills/japanese-readability-editor/scripts/measure.py --locate --extras tests/fixtures/before.md
python3 skills/japanese-readability-editor/scripts/compare_rewrite.py tests/fixtures/before.md tests/fixtures/after_split.md
python3 skills/japanese-readability-editor/scripts/verify_preservation.py --strict tests/fixtures/before.md tests/fixtures/after_split.md
```

`measure.py` は文や段落の長さなどの候補を示します。`compare_rewrite.py` は数値・用語・否定などの変化候補を示します。最後の検証は、改行だけを挿入したサンプルなので、`OK (strict)` と終了コード 0 を返します。

文言を変えたサンプルも確かめられます。

```bash
python3 skills/japanese-readability-editor/scripts/verify_preservation.py --strict tests/fixtures/before.md tests/fixtures/after_changed_char.md
```

「ことである」が「ことだ」に変わっているため、`FAIL (strict)` と終了コード 1 を返します。これは、検証が変更を検出した結果です。

自分の文章を検証するときは、上の入力パスを編集前・編集後のファイルに替えます。モード B には `compare_rewrite.py`、モード C には `verify_preservation.py --strict` を使います。

### 表記と小説の補助検査を試す

```bash
python3 skills/japanese-readability-editor/scripts/check_kokugo.py tests/fixtures/kokugo/has_error.md --profile general-tech
python3 skills/japanese-readability-editor/scripts/check_fiction.py tests/fixtures/before.md --json
```

最初のコマンドは、サンプルの `こんにちわ` と `そうゆう` を `error` として示します。終了コードは 1 です。後のコマンドは、文字数と括弧の対応などを JSON で返します。このサンプルには括弧の不整合がなく、終了コードは 0 です。物語としての評価はしません。

作品で避けたい表記を追加で検査する場合は、UTF-8 の `work-checks.json` を作ります。

```json
{
  "forbidden": ["アオイー"],
  "required": ["アオイ"]
}
```

原稿を UTF-8 の `manuscript.md` として用意し、次を実行します。

```bash
python3 skills/japanese-readability-editor/scripts/check_fiction.py manuscript.md --settings work-checks.json --json
```

`forbidden` は出現すると候補、`required` はファイルに一度も出ないと候補です。文字列の部分一致なので、「アオイー」にも「アオイ」が含まれます。必須語があることだけでは、表記や人物の整合性を確認できません。

### 終了コードと指摘を読む

| スクリプト | 0 | 1 | 2 |
|---|---|---|---|
| `verify_preservation.py --strict` | 改行の挿入だけと判定 | 文言・空白の変更や既存改行の削除を検出 | 入力や引数の不備 |
| `check_kokugo.py`（既定の設定） | `error` なし | `error` あり | 検査を完了できず |
| `check_fiction.py` | 指定した検査で候補なし | 確認候補あり | 検査を完了できず |

`compare_rewrite.py` は、変化候補があっても、正常に照合できれば終了コード 0 です。0 を意味保存の合格判定として扱わず、表示された候補を原文と見比べます。`tokenizer: regex` は、SudachiPy を使わずに照合したことを示します。任意の導入方法は、[インストールの SudachiPy の説明](installation.md#sudachipy-を入れる任意)にあります。

`verify_preservation.py --strict` は、CRLF と LF の違いを区別せず、先頭の BOM も除いて比較します。モード C では、元の改行コードと BOM の保持も別途確認します。各ツールの詳しい仕様と限界は、[スクリプト](scripts.md)と[小説の補助検査](../skills/japanese-readability-editor/references/fiction-checks.md)を参照してください。

## 意図した結果にならないとき

| 状況 | 確認する点と再依頼の例 |
|---|---|
| Skill が使われたか分からない | 環境に合う呼び方で、Skill 名とモードを明示する。導入は[動作確認](installation.md#動作を確認する)で確かめる |
| モード C で文言が変わった | 「モード C。原文からやり直し、改行と空行の挿入だけにして」と依頼し、編集前と再照合する |
| モード B で意味が変わった | 「『再試行できる』は可能の意味です。この意味を残して該当文を直して」のように、原文の意味を示す |
| 解説が付いた | 「完成した本文だけを返して」と出力形式を指定する |
| 小説の口調や比喩が変わった | 「小説モードで推敲。原文の口調・比喩を保ち、誤字だけ直して」と変更範囲を限定する |
| B・C や小説の続きで対象を求められた | 対象本文または読めるファイルを渡す。続きには直前の本文と必要な設定を添える |
| `No such file or directory` などで検査できない | 実行する場所と入力パスを確認する。空白を含むパスは引用符で囲む |

モード指定は Skill の指示で、製品側が編集範囲を強制する機能ではありません。完成稿は、数値、条件、否定、断定の強さ、文体、設定を原文と突き合わせます。文の長さの指摘や検査の終了コードだけでは、意味の保存や小説の品質は判断できません。

## 詳細を参照する

- [モード指定の扱いと動作確認](usage.md)
- [計測・照合スクリプトの詳細](scripts.md)
- [国語の表記・用法の検査](kokugo.md)
- [小説の操作契約](../skills/japanese-readability-editor/references/fiction-writing.md)
- [小説の修正例・保持例](../skills/japanese-readability-editor/assets/fiction-examples.md)

このガイドで実行した例と未確認の範囲は、[実践ガイドの検証記録](user-guide-validation.md)にあります。製品の仕様は[環境別の対応](environments.md)、小説モード全体の確認は[小説モードの検証記録](fiction-validation.md)を参照してください。依頼例は使い方を示すもので、各製品・各モデルで同じ出力を保証するものではありません。
