# 環境別の対応

各環境での Skill の扱いと、環境ごとの注意をまとめます。インストールのコマンドは、[インストール](installation.md)にあります。

仕様の確認日は 2026-09-29 です。OpenCode と Hermes Agent は 2026-10-10 で、確認した版と範囲は[OpenCode と Hermes Agent の対応確認](opencode-hermes-checks.md)にあります。各製品の仕様は変わりやすく、確認日以降に変わる可能性があります。このため、公式資料で確認できた範囲だけを書き、確認できなかった項目は「未確認」としています。

## 対応表

`Native Agent Skill` は、その環境が Agent Skills 形式(`SKILL.md` を含むフォルダ)を直接扱えるかを表します。表の path は、各製品が Skill を探す場所です。インストーラが置く場所は、[インストール](installation.md#配置先)にあります。

| Environment | Native Agent Skill | Workspace path | User/global path | ZIP upload | Notes |
|---|---|---|---|---|---|
| ChatGPT Work | あり。Plus プランのアカウントで、アップロードと呼び出しを確認した(2026-09-29)※1 | 未確認 | 未確認 | 可。Plugins → Skills → Add → Upload from your computer。ZIP を取り込めた | `@skill-name` で呼べる(確認済み)。暗黙起動は不安定([ChatGPT Work](#chatgpt-work))。取り込み時に、ChatGPT が `agents/openai.yaml` を自動生成する ※1 |
| Codex | あり | `.agents/skills/`(カレントから repo root まで探索) | `$HOME/.agents/skills/` | 不要 | `$CODEX_HOME/skills` は旧仕様。管理者向けに `/etc/codex/skills` もある。変更は自動検出、出なければ再起動。symlink 可 |
| Claude Cowork | あり | 非対応(アップロード方式) | 非対応 | 可。Customize → Skills。ZIP の最上位にフォルダ | コード実行の有効化が必要。プランの記載は公式ページ間で異なる。`description` に200字の上限があるという記載あり |
| Claude Code | あり | `.claude/skills/` | `~/.claude/skills/` | 不要 | `.agents/skills` は読まない。未知の frontmatter は無視される。symlink 可 |
| GitHub Copilot | あり(cloud agent、code review、CLI、app、VS Code / JetBrains の agent mode) | `.agents/skills/`、`.github/skills/`、`.claude/skills/` | `~/.agents/skills/`、`~/.copilot/skills/` | 不要 | 利用できるプランは未確認 |
| Gemini Apps | あり(Skills。Gems は 2026-11 以降 Skills へ移行) | 非対応 | 非対応(アカウントに保存) | `SKILL.md` またはフォルダをアップロード。ZIP の可否は未確認 | `scripts/` の扱いは未確認。生成物は [Gemini Apps](#gemini-apps) |
| Gemini CLI | あり | `.agents/skills/`、`.gemini/skills/` | `~/.agents/skills/`、`~/.gemini/skills/` | 不要 | 同じ階層では `.agents/skills` が優先。`/skills list` で確認 |
| Antigravity IDE | あり | `.agents/skills/`(旧 `.agent/skills/` も互換) | `~/.gemini/config/skills/`(旧 `~/.gemini/antigravity/skills/`) | 不要 | `/<skill-name>` で呼べる |
| Antigravity CLI | あり | `.agents/skills/` | `~/.gemini/antigravity-cli/skills/` | 不要 | `~/.agents/skills` は自動では読まれないとする記述あり(Codelab)。未確認 |
| OpenCode | あり | `.opencode/skills/`、`.claude/skills/`、`.agents/skills/`(作業ディレクトリから git の根まで探索) | `~/.config/opencode/skills/`(`$OPENCODE_CONFIG_DIR` も探索)、`~/.claude/skills/`、`~/.agents/skills/` | 不要 | `skill` ツールで読み込む。検出は、2.0.20 の実機で確認済み(`.opencode`、XDG の設定、`.agents`、`.claude`)。`skill` ツールでの読み込みは、`.opencode` に置いた場合を確認済み。スクリプトの実行とモード指定は、モデルしだい([OpenCode](#opencode)) |
| Hermes Agent | あり | `.hermes/skills/`、`.agents/skills/`(`hermes skills trust` が要る) | `$HERMES_HOME/skills/`(既定 `~/.hermes/skills/`。プロファイルごとに別) | 不要 | `/<skill-name>`、`hermes -s`。検出、本文と参照資料の読み込み、同梱スクリプトの実行を、Hermes 本体の CLI と関数で確認済み。手元のローカルモデルでは、`-s` を付けると計測のスクリプトが動く回が多かったが、安定はしなかった([Hermes Agent](#hermes-agent)) |

※1 2026-09-29 に、Plus プランのアカウントで、実際に確認しました。

二次資料では、対象は Business / Enterprise / Healthcare / Edu とされていました。Free / Plus / Pro は対象外という記述もありました。今回の確認とは一致しません。

OpenAI ヘルプセンターの記事は、自動取得できませんでした。提供状況は、プラン、workspace の設定、リリース状況によって変わります。管理者による有効化が必要な場合もあります。利用前に、各自の画面で確認してください。

### 未確認の項目

次の項目は、公式資料で確認できていません。

- ChatGPT Work のプラン条件と、管理者の設定(Plus プランでの動作は確認済み)
- Gemini Apps の `scripts/` の扱いと、ZIP の可否
- Copilot のプラン条件
- Antigravity の `~/.agents/skills`
- Hermes Agent の、ホスト型の主要モデルでの動作(確かめたのはローカルモデルだけ)と、対話セッションでの `/japanese-readability-editor`
- OpenCode の、ホスト型の主要モデルでの動作(確かめたのはローカルモデルだけ)と、`OPENCODE_CONFIG_DIR` に置いた Skill が読まれるか
- Hermes Agent の Docker、SSH、Modal、Daytona、Singularity での動作

## ChatGPT Work

ChatGPT のワークスペースに Skill をアップロードする方式です。`dist/japanese-readability-editor.zip` を使います。

1. ZIP を用意します。最新の Release からダウンロードするか、`python3 tools/package.py` で作ります。
2. ChatGPT の Plugins → Skills を開き、Add → Upload from your computer で、ZIP を選びます。

アップロードできるのは、`.zip`、`.skill`、`SKILL.md` で、最大サイズは1ファイルあたり25MBです。

SudachiPy は、Skill の指示で、エージェントが実行中に入れます(「[SudachiPy を入れる](installation.md#sudachipy-を入れる任意)」)。

Skill 機能がプラン、workspace の設定、管理者の許可に依存する点に注意してください。Enterprise と Edu では、管理者が有効化するまで表示されない場合があります。アップロード画面の名称と手順は、変わる可能性があります。

Plus プランのアカウントで、取り込み、呼び出し、SudachiPy の導入、置き換えを確かめました。記録は、[ChatGPT Work の実機確認](chatgpt-work-checks.md)にあります。

### 暗黙起動の実測

`@` で指定しない場合に、Skill が自動で使われるかを調べました(2026-09-30)。使うべき依頼6件のうち、使われたのは1件でした。その依頼も、3回測り直すと、3回とも使われませんでした。`description` を変えても、増えませんでした。

暗黙起動は、この条件では不安定でした。確実に使うには、`@japanese-readability-editor` で指定してください。

測定の条件、結果、限界は、[ChatGPT Work の暗黙起動の実測](chatgpt-implicit-invocation.md)にあります。

## Codex

Codex は `.agents/skills/` を、カレントディレクトリから repo root まで順にたどって探します。ユーザー全体の配置先は `$HOME/.agents/skills/` です。

従来の `${CODEX_HOME:-~/.codex}/skills/` は、現行の公式ドキュメントに記載がありません。旧仕様として非推奨になったと報告されています。

このリポジトリは、現行の `$HOME/.agents/skills/` を使います。旧版の Codex を使う場合は、手動で `$CODEX_HOME/skills/` へコピーしてください。

## Claude Cowork

Claude のアプリ(Cowork を含む)には、ZIP をアップロードします。ChatGPT Work と同じ ZIP を再利用します。

1. ZIP を用意します。最新の Release からダウンロードするか、`python3 tools/package.py` で作ります。
2. Customize → Skills から、`dist/japanese-readability-editor.zip` を追加します。

新しい版に置き換える手順は、「[更新する](installation.md#更新する)」にあります。

ZIP は、Skill のフォルダが最上位にある構造です。コード実行の有効化が必要です。Claude Code の `~/.claude/skills/` は、Cowork のセッションでは読み込まれません。

この Skill の `description` は、Claude のヘルプ記事にある「200字以内」の記載に合わせて、200字以内に収めています。Agent Skills の仕様と Claude API の文書は、1024字までを許しています。

### モデルを選ぶ

Claude のアプリで確かめたモデルは、Sonnet 5.5、Haiku 4.5、Haiku 5.5 です。Haiku 4.5 では、Skill の規則が守られない回がありました。Haiku 5.5 では、文体と用語は保たれました。ただし、頼んでいない解説が付いた回がありました。

2026-10-07 に、Pro プランのアカウントで、v0.3.0 を確かめました。ブラウザの claude.ai のチャットで、252字の1段落を処理させました。依頼の1行目には、`/japanese-readability-editor` とモードを書きました。Cowork では、確かめていません。

Haiku 5.5 は、2026-10-10 に、同じアカウント、同じ文章、同じ書式で確かめました。回数は、モード C が1回、モード B が2回です。そのとき claude.ai に入っていた Skill は、1文の目安が80字の版(v0.5.0 より前)で、v0.3.0 そのものとは限りません。この測定のために、Skill は入れ替えていません。

| モデル | モード C(1回) | モード B(2回) |
|---|---|---|
| Haiku 4.5(Extended) | 文言は変わらなかった。頼んでいない「区切った理由」が付いた | 2回とも、常体を敬体に変え、「ログファイル」を「ログ」にした。1回目は Skill を読み込まず、「呼び出し元に」も消えた |
| Sonnet 5.5(Medium) | 文言は変わらなかった | 2回とも、常体のまま、用語と条件を保った。言い切りを変えた1回は、その旨を返答に書いた |
| Haiku 5.5(Medium) | 文言は変わらなかった。3段落に分けただけで、解説は付かなかった。改行以外の全文字が同一だった(`verify_preservation.py --strict` で確認) | 2回とも、常体のまま、用語と条件を保った。`compare_rewrite.py` では、数値、用語、文体の変化は挙がらなかった。1回目は、頼んでいない「主な変更点」と「確認してほしい点」が付いた。2回目は、解説は付かず、「なお」を「また」に替えた |

Haiku 4.5 の2回目は、Skill を読み込んだうえで、「敬体に統一」と書いて文体を変えました。Skill を読み込んでも、規則が守られるとは限りません。

## Claude Code

Claude Code は `.agents/skills/` を読みません。配置先は、プロジェクトでは `.claude/skills/`、ユーザー全体では `~/.claude/skills/` です。Codex などと同じプロジェクトで使う場合は、`--target all` で両方に配置します。複製を避けたい場合は、`--link` でシンボリックリンクを作れます。

### プラグインとして入れる

Claude Code のプラグインとしても、入れられます。

```text
/plugin marketplace add Mr-Kondo/japanese-readability-editor
/plugin install japanese-readability-editor@japanese-readability-editor
```

プラグインの Skill は、プラグイン名を前に付けて呼びます。たとえば、`/japanese-readability-editor:japanese-readability-editor` です。

定義ファイル(`.claude-plugin/`)は、`skill/` を指すだけです。Skill は複製していません。`version` を設定していないので、更新はコミットに追従します。更新の手順は、「[更新する](installation.md#更新する)」にあります。

プラグインの定義は、`claude plugin validate` で検証しました。

プラグインのインストールと更新は、マーケットプレースの追加を含めて、`claude plugin` のコマンドで確かめました。確認日は 2026-10-05、Claude Code は 2.1.285 です。手元の設定に影響しないよう、一時的な設定ディレクトリ(`CLAUDE_CONFIG_DIR`)を使いました。対話画面の `/plugin` での操作は、検証していません。

## GitHub Copilot

Copilot は、次の場所から Skill を読みます。

- プロジェクト: `.agents/skills/`、`.github/skills/`、`.claude/skills/`
- 個人: `~/.agents/skills/`、`~/.copilot/skills/`

この repo は共通配置の `.agents/skills/` を使い、`.github/skills/` へは複製しません。

Copilot には、Skill のほかに指示ファイルがあります。今回の用途は、常に適用するルールではなく、必要なときに読み込む手順なので、Agent Skill を使います。

| 仕組み | 置き場所 | 適用のされ方 |
|---|---|---|
| Agent Skills | `.agents/skills/<name>/SKILL.md` など | 関連するときに読み込まれる。詳細な手順向き |
| リポジトリ全体の指示 | `.github/copilot-instructions.md` | 常に適用される。プロジェクト全体の方針向き |
| パス別の指示 | `.github/instructions/*.instructions.md` | `applyTo` に合うファイルを扱うときに適用される |
| エージェント向けの指示 | `AGENTS.md`(`CLAUDE.md`、`GEMINI.md` も) | エージェントが参照する。ディレクトリ木で最も近いものが優先される |

## Gemini Apps

Gemini CLI とは別の製品です。

Gemini Apps では、Gems が 2026-11-17 から Skills に移行します。これは個人の Google アカウントの日程です。Workspace の business / enterprise は 2027-03、education は 2027-06です。

Skills は、`SKILL.md` またはそれを含むフォルダをアップロードして作れます。公式資料が挙げるファイルの種類は、テキスト、PDF、画像です。`scripts/` にある `.py` を扱えるかは、記載がありません。

このため、`tools/package.py` は、共通 Skill から次の2つを生成します。どちらも共通 Skill から機械的に作る出力で、別実装ではありません。

| 生成物 | 使い方 |
|---|---|
| `dist/gemini-apps/japanese-readability-editor/` | `scripts/` を除いたコピー。Skills へフォルダごとアップロードする |
| `dist/gemini-apps-instructions.md` | Gem の指示、または Custom Instructions に貼り付ける |

指示文は、Part 1(`SKILL.md` の本文)と Part 2(詳細ルール)からなります。文字数の上限で貼れない場合は、Part 2 を省いてください。上限は公式資料で確認できていません。Gemini Apps では `scripts/` を実行できないので、計測と検証は Agent が手作業で近似します。

## Gemini CLI

`.agents/skills/` は `.gemini/skills/` の別名で、同じ階層では優先されます。適用順は、ワークスペース、ユーザー、拡張機能、組み込みの順です。確認と管理には、次の機能を使えます。

- 対話中: `/skills list`、`/skills reload`、`/skills enable <name>`、`/skills disable <name>`、`/skills link <path>`
- 端末: `gemini skills list`

Skill が有効になるときは、名前と参照するディレクトリを示す確認画面が出ます。

## Antigravity IDE

ワークスペースは `.agents/skills/` です。旧称の `.agent/skills/` は互換のために読まれますが、新しい `.agents/skills/` を優先します。グローバルは `~/.gemini/config/skills/` で、旧配置の `~/.gemini/antigravity/skills/` も互換のために読まれます。

## Antigravity CLI

ワークスペースは、IDE と同じ `.agents/skills/` です。グローバルは `~/.gemini/antigravity-cli/skills/` で、IDE とは異なります。IDE と CLI の両方に入れる場合は `--target antigravity` を使います。

## OpenCode

OpenCode は、`skill` ツールで Skill を読み込みます。ツールの説明に、Skill の名前と `description` が並びます。Agent が必要と判断したときに、本文が読み込まれます。

配置先は、プロジェクトでは `.opencode/skills/`、ユーザー全体では `~/.config/opencode/skills/` です。`XDG_CONFIG_HOME` と `OPENCODE_CONFIG_DIR` で変わります。導入、更新、検証のコマンドと配置先の決め方は、[インストール](installation.md#opencode-と-hermes-agent-に入れる)にあります。

OpenCode は、`.agents/skills/` と `.claude/skills/` も読みます(公式文書)。そこにも同じ Skill があると、重複します。OpenCode は、同名のうち 1 つしか使いません。

### 呼び出す

明示的に Skill を呼ぶ構文は、公式資料に見つけられませんでした。依頼に Skill の名前を書きます。`permission.skill` が `deny` だと、Skill は Agent から見えません。`ask` だと、読み込むときに承認を求められます。

モードの指定は、依頼に書きます。次の依頼は、書き方の例です。

モデルによっては、Skill を読み込んでも、スクリプトを実行しません。実行させるには、依頼に「`scripts/measure.py` を、Skill の Base directory を基準にした絶対パスで実行して」のように書きます。パスに空白があると、引用符で囲まずに失敗するモデルがありました。モード C は、返ってきた文章を、`verify_preservation.py --strict` で確かめてください。

```text
japanese-readability-editor を使って、モード A で、この調査結果を技術レポートにまとめて。
```

```text
japanese-readability-editor を使って、モード B で、README.md を読みやすく直して。
```

```text
japanese-readability-editor を使って、モード C で、docs/design.md の段落だけ分けて。
```

### Python と依存

Python 3.10 以上が必要です。標準ライブラリだけで動きます。SudachiPy は任意で、入っていなければ標準ライブラリの経路で動きます([SudachiPy を入れる](installation.md#sudachipy-を入れる任意))。Skill は、手元の Python に SudachiPy を断りなく入れません。

### うまくいかないとき

| 症状 | 確かめること |
|---|---|
| Skill が見つからない | `python3 tools/verify_install.py --scope user --target opencode` で、配置先と中身を確かめる。`opencode debug paths` の `config` が、配置先の親と一致するか。OpenCode を開き直す。プロジェクトに入れたなら、そのプロジェクトの中で起動しているか。`permission.skill` が `deny` でないか。`OPENCODE_DISABLE_EXTERNAL_SKILLS` を設定していると、`.claude/skills/` と `.agents/skills/` の Skill は読まれない |
| 一覧が空、または組み込みの 2 件だけ | `opencode serve` の起動直後は、Skill の読み込みが遅れる。`GET /api/skill` を 3 回以上呼ぶと出る。サーバは、起動したディレクトリに固定される |
| `name` が合わない | `name` は `japanese-readability-editor` で、ディレクトリ名と一致しなければならない。ディレクトリ名を変えない |
| 重複の警告が出る | `verify_install.py` が、重複する場所を示す。残す 1 か所を決め、ほかは利用者が削除する。ツールは削除しない |
| 参照資料やスクリプトに届かない | `skill` ツールの出力にある `Base directory for this skill` を確かめる。`scripts/` などの相対パスは、そこからの相対になる。Agent がプロジェクトのディレクトリで相対パスのまま実行して失敗するなら、基準のディレクトリの絶対パスを使うよう頼む |
| スクリプトが実行できない | `python3 --version` が 3.10 以上か(Windows は `python`)。`verify_install.py` が、スクリプトを外のディレクトリから実行して、失敗した理由を示す。Agent のシェルの権限(`bash` ツール)が許可されているか |
| skills ディレクトリに別の `.md` が Skill になる | v2 のソースは、skills ディレクトリの直下の `.md` も Skill として読む。配布物の `INSTALL.md` を、skills ディレクトリに置かない |

### 確認した版と未検証

2026-10-10 に、公式文書と `sst/opencode` のソース(`055d95bb7e27`)を確認しました。手元の `opencode 2.0.20` では、`.opencode/skills/`、XDG の設定ディレクトリ、`.agents/skills/`、`.claude/skills/`(プロジェクトとユーザー)に置いた Skill が発見されることを確かめました。`.opencode/skills/` に置いた Skill は、`skill` ツールで本文が読み込まれることも確かめました。手元のローカルモデルでは、スクリプトの実行は、手順を明示した依頼の 1 回だけ成功しました。普通の依頼では実行しないモデルがあり、`モード C` は守られませんでした。ホスト型の主要モデルと `OPENCODE_CONFIG_DIR` は、確かめていません。詳しくは[確認の記録](opencode-hermes-checks.md#opencode-2020)にあります。

## Hermes Agent

Hermes Agent は、Skill をホーム(`~/.hermes`)の `skills/` に置きます。Agent は `skills_list()` で一覧を、`skill_view(name)` で本文を、`skill_view(name, path)` で参照資料を読みます。

配置先は、ホームの決まり方で変わります。`HERMES_HOME`、プロファイル(`hermes -p`、`hermes profile use`)、既定の `~/.hermes` の順に、実際に使われるホームを解決して、表示します。解決の順番と、プロジェクトに入れるときの `hermes skills trust` は、[インストール](installation.md#hermes-agent-の配置先)にあります。

Hermes は、同名の Skill が複数あると、プロジェクト、プロファイル、`skills.create_dir`、`skills.external_dirs` の順で上位を使い、下位を隠します。

### 呼び出す

セッションの中では、`/japanese-readability-editor` で呼べます。メッセージの先頭に Skill を書くと、残りが依頼になります。端末からは、`-s` で Skill を読み込んで開始できます。

```text
/japanese-readability-editor モード C
docs/design.md に適用して。
```

```bash
hermes chat -s japanese-readability-editor -q "モード B で README.md を読みやすく直して"
```

モード A の依頼は、`モード A で、この調査結果を技術レポートにまとめて` のように書きます。手元のローカルモデルで試した結果は、[確認の記録](opencode-hermes-checks.md#hermes-agent-v0210)にあります。`-s` で読み込んだ回は、`[Skill directory]` の絶対パスで、スクリプトが動きました。依頼に Skill の名前を書くだけの場合は、モデルが `skill_view` で Skill を読んでも、`scripts/` を作業ディレクトリの相対パスで実行して失敗する回がありました。`hermes chat -q` に `/japanese-readability-editor` と書いても、Skill は起動しませんでした(非対話のため。対話セッションでは確かめていません)。非対話で使うときは、`-s` を使います。

Skill を読み込んだときのメッセージに、`[Skill directory: <絶対パス>]` が入ります。`scripts/` などの相対パスは、その場所からの相対です。

### Python と依存

Python 3.10 以上が必要です。標準ライブラリだけで動きます。SudachiPy は任意です。ターミナルが Docker、SSH、Modal、Daytona のときは、スクリプトはその環境で動くので、Python もその環境のものが対象です。

### ターミナルが手元ではないとき

Docker と Singularity は、`~/.hermes` の Skill を bind mount します。SSH、Modal、Daytona は、セッションの間に `~/.hermes` の状態を送ります。どれも、ソースの読み取りです。実機では確かめていません。

- Skill は、複製で入れます。シンボリックリンクは送られません。
- 確かめるには、その環境の中で、`[Skill directory: ...]` のパスに、`SKILL.md`、`scripts/`、`data/` があるかを見ます。`python3 --version` が 3.10 以上かも、その環境で確かめます。
- SSH、Modal、Daytona では、Hermes は終了時に、送った状態の変更を手元へ戻します(文書による)。Agent がリモートで Skill を書き換えると、手元のファイルが変わることがあります。

### うまくいかないとき

| 症状 | 確かめること |
|---|---|
| Skill が見つからない | `hermes skills list` に出るか。プロファイルを使っているなら、同じ `-p` を付ける。`python3 tools/verify_install.py --scope user --target hermes` が、解決したホームを示す。`hermes profile use` で選んだプロファイルは、`active_profile` に従う。セッションを開き直す |
| プロジェクトの Skill が出ない | `hermes skills trust` を、そのリポジトリの中で実行したか。プロジェクトの根は、`.git` を持つ最も近い祖先。`skills.project_discovery: false` にしていないか |
| 同名の Skill が隠れている | 上位の Skill が下位を隠す。同じ階層に内容の違う同名が 2 つあると、曖昧としてエラーになる。`verify_install.py` が重複を示す |
| `hermes skills install` で入れたら検査が動かない | `data/` と `scripts/kokugo_engine.py` が入らない。`tools/install.py` で入れ直す |
| 参照資料やスクリプトに届かない | 読み込みメッセージの `[Skill directory: ...]` を確かめる。ターミナルが手元でなければ、その環境の中で、パスが存在するか。複製で入れているか |
| スクリプトが実行できない | `terminal` のツールセットが有効か(`hermes chat --toolsets` で確かめる)。`python3 --version` が 3.10 以上か。`verify_install.py` が、スクリプトを外のディレクトリから実行して、失敗した理由を示す。モデルが `scripts/` を相対パスで実行して失敗するときは、`-s japanese-readability-editor` を付ける(絶対パスが渡される)。それでも失敗する回がある |
| 計測やモードの結果が、スクリプトの出力と合わない | モデルが、スクリプトを実行せずに答えた可能性がある。`measure.py` や `verify_preservation.py --strict` を自分で実行して、確かめる |
| ファイルに `1\|` のような行番号が入った | モデルが、`read_file` の出力の行番号を、内容として書いた。Hermes が拒否する場合もあるが、防げるとは限らない。`verify_preservation.py --strict` で確かめる |

### 確認した版と未検証

2026-10-10 に、公式文書と `NousResearch/hermes-agent` のソース(`46d7718a52ff`)を確認しました。手元の `Hermes Agent v0.21.0 (2026.8.31)` では、`hermes skills list`、`hermes skills trust`、Skill の読み込み、参照資料の読み込み、`[Skill directory]` のパスからのスクリプトの実行を、隔離した `HERMES_HOME` で確かめました。手元のローカルモデルでは、モデルを介した動作も試しました。`-s` を付けた計測は、gemma4 で 3 回中 2 回動き、通常の依頼では動かず、qwen3-coder で `モード C` は守られませんでした。ホスト型の主要モデルと、手元ではないターミナルの backend は、確かめていません。詳しくは[確認の記録](opencode-hermes-checks.md#hermes-agent-v0210)にあります。

## 参照した公式資料

- [Agent Skills specification](https://agentskills.io/specification)
- [Codex / ChatGPT: Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code: Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Claude: Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Claude Help Center: How to create custom skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)
- [GitHub Docs: About agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- [GitHub Docs: Custom instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)
- [GitHub Docs: Copilot CLI の agent skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)
- [Gemini CLI: Agent Skills](https://geminicli.com/docs/cli/skills/)
- [Antigravity: Agent Skills](https://antigravity.google/docs/skills)
- [Gemini Apps Help: The transition from Gems to skills](https://support.google.com/gemini/answer/18560919?hl=en)
- [OpenCode: Agent Skills](https://opencode.ai/docs/skills/)
- [OpenCode: Config](https://opencode.ai/docs/config/)
- [Hermes Agent: Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [Hermes Agent: Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- [sst/opencode](https://github.com/sst/opencode)
