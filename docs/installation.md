# インストール

既に使っている場合は「[更新する](#更新する)」へ進んでください。初めて入れる場合は、使う環境に合わせて手順を選びます。

- [npx skills で入れる（Codex、Claude Code、OpenCode、Hermes など）](#インストールする)
- [ChatGPT Work、Claude Cowork、Gemini Apps にアップロードする](#アップロード型の環境に入れる)
- [gh skill（GitHub CLI）で入れる](#github-cligh-skillで入れる)
- [動作を確認する](#動作を確認する)
- [OpenCode と Hermes Agent の配置先を確認する](#opencode-と-hermes-agent-の配置先)
- [削除する](#削除する)
- [SudachiPy を入れる（任意）](#sudachipy-を入れる任意)

手早く入れる場合は、README の「[クイックスタート](../README.md#クイックスタート)」を使ってください。

## 更新する

入れている版は、`python3 scripts/skill_info.py --version` で確かめられます(Skill のフォルダで実行します。例: `japanese-readability-editor 0.17.0`)。最新の版は、[Releases のページ](https://github.com/Mr-Kondo/japanese-readability-editor/releases)にあります。

### npx skills で入れた場合

入れたときと同じコマンドを、もう一度実行します。同名のものは上書きされます(2026-11-10、隔離したホームで、余分に追加したファイルも消えることを確かめました)。

```bash
npx skills add . -a claude-code -g
```

`npx skills update` は、確かめていません。上書きの前の退避は、ありません。

### 手動でコピーした場合

古い `japanese-readability-editor/` を削除してから、新しいものをコピーします。

```bash
rm -r ~/.claude/skills/japanese-readability-editor
cp -R skills/japanese-readability-editor ~/.claude/skills/
```

`ln -s` で、リポジトリの `skills/japanese-readability-editor` へのリンクにした場合は、`git pull` だけで反映されます。リポジトリを移動すると、リンクが切れます。

### tools/install.py で入れていた場合(廃止)

`tools/install.py` と `tools/uninstall.py` は、廃止しました([ADR](../adr/2026-11-10-remove-install-py.md))。`install.py` で入れたものは、`npx skills` では消えません。古い複製やリンクを削除してから、`npx skills add` で入れ直してください。同じ Skill が2か所にあると、環境によっては片方しか使われません。

```bash
rm -r ~/.agents/skills/japanese-readability-editor ~/.claude/skills/japanese-readability-editor
```

`install.py --on-conflict backup` で退避した `skills.bak/` も、不要なら削除します。

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

## 必要なもの

- Python 3.10 以上(同梱のスクリプトを動かすため)
- Node.js(`npx skills` で入れる場合)
- Git(リポジトリを取得する場合)
- SudachiPy と辞書(任意。`compare_rewrite.py` の判定を正確にする)

検証ツールは、Python の標準ライブラリだけで動きます。SudachiPy は、入っていなくても動きます。入れ方は、環境によって違います(「[SudachiPy を入れる](#sudachipy-を入れる任意)」)。

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

`npx skills add` で入れます。リポジトリを取得していれば、取得先で `.` を指定します。取得していなければ、`Mr-Kondo/japanese-readability-editor` を指定します(GitHub から実際に入れることは、確かめていません)。

```bash
npx skills add . -a claude-code -g
```

`-a` に使う環境を並べます(例: `-a claude-code codex`)。`-g` を付けるとユーザー全体、付けないと、いまのプロジェクトに入れます。一覧だけ見るときは `--list` です。

| 使う環境 | `-a` に指定する名前 | 入る場所(`-g`) |
|---|---|---|
| Codex | `codex` | `~/.agents/skills/` |
| Claude Code | `claude-code` | `~/.claude/skills/`(ほかの環境と同時に入れるときは `~/.agents/skills/` へのリンク) |
| OpenCode | `opencode` | `~/.agents/skills/`(OpenCode が読む) |
| Hermes Agent | `hermes-agent` | `~/.hermes/skills/`(ほかの環境と同時に入れるときは `~/.agents/skills/` へのリンク) |
| Antigravity | `antigravity`、`antigravity-cli` | `~/.agents/skills/`。ただし、公式資料のユーザー全体の探索先は別(下) |

2つ以上の環境へ同時に入れると、実体を `~/.agents/skills/` に1つ置き、ほかの環境からリンクします。リンクにしないときは `--copy` を付けます。Hermes の Docker や SSH などの backend には、リンクは送られません。その場合は `--copy` で入れます。

確かめた範囲は、2026-11-10、macOS、`skills` 1.7.6、隔離したホームで、ローカルのリポジトリを `-g` で入れたときです。Hermes のプロファイル(`HERMES_HOME`、`-p`)を使う場合の入れ先は、確かめていません。その場合は、手動でコピーします。

### 手動でコピーする

`npx` を使わない場合と、`npx skills` が入れない場所へ入れる場合は、`skills/japanese-readability-editor/` を、配置先へコピーします。

```bash
cp -R skills/japanese-readability-editor ~/.gemini/config/skills/
cp -R skills/japanese-readability-editor ~/.gemini/antigravity-cli/skills/
```

上の2行は、Antigravity のユーザー全体の配置先(IDE と CLI)です。`npx skills` は、ここへは入れません。プロジェクトに入れるときは、`npx skills add` が `.agents/skills/` に入れるので、そのままで読まれます。

リポジトリの `skills/japanese-readability-editor/` を開発しながら使うときは、コピーではなくリンクにします。

```bash
ln -s "$(pwd)/skills/japanese-readability-editor" ~/.claude/skills/japanese-readability-editor
```

### 配置先

| 環境 | プロジェクトの配置先 | ユーザー全体の配置先 |
|---|---|---|
| Codex、Copilot、Gemini CLI | `.agents/skills/` | `~/.agents/skills/` |
| Claude Code | `.claude/skills/` | `~/.claude/skills/` |
| Antigravity IDE | `.agents/skills/` | `~/.gemini/config/skills/` |
| Antigravity CLI | `.agents/skills/` | `~/.gemini/antigravity-cli/skills/` |
| OpenCode | `.opencode/skills/`(`.agents/skills/` も読む) | `$OPENCODE_CONFIG_DIR`、`$XDG_CONFIG_HOME/opencode`、`~/.config/opencode` の `skills/`([詳細](#opencode-の配置先)) |
| Hermes Agent | `.hermes/skills/`(使う前に `hermes skills trust` が要る) | Hermes のホームの `skills/`(`HERMES_HOME`、プロファイル、`~/.hermes`。[詳細](#hermes-agent-の配置先)) |

各製品が Skill を探す場所は、ほかにもあります。一覧は、[環境別の対応](environments.md#対応表)にあります。

### 上書きと退避

`npx skills add` は、同名のものを確認なしで上書きします。上書きの前の退避と、`--dry-run` は、ありません。別の場所にある同名の Skill(古い複製など)は、そのまま残ります。同じ Skill が複数の場所にあると、OpenCode と Hermes は、片方しか使いません。1か所にそろえてください。

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

## OpenCode と Hermes Agent の配置先

どちらも、配置先が環境変数やプロファイルで変わります。`npx skills add -a opencode`、`-a hermes-agent` が入れる場所が、下の配置先と同じかを、`verify_install.py` で確かめられます(「[配置した Skill を検証する](#配置した-skill-を検証する)」)。

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

OpenCode は、`.agents/skills/` と `.claude/skills/` も読みます(公式文書)。`~/.agents/skills/` や `~/.claude/skills/` に入れた Skill も、OpenCode から見えます。そこに入れてあるなら、OpenCode のために入れ直す必要はありません。両方に置くと、同名の Skill が重複します。

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

プロジェクトに入れるときは、`<プロジェクト>/.hermes/skills/` に置きます(`npx skills add -a hermes-agent` を、`-g` なしで実行します)。Hermes は、`.git` を持つ最も近い祖先を、プロジェクトの根とします。リポジトリを信頼するまで、読み込みません。信頼は利用者の判断なので、こちらでは実行しません。

```bash
cd /path/to/project
hermes skills trust
```

Hermes のターミナルが Docker、SSH、Modal、Daytona のときも、Skill は複製で入れます。`hermes skills install` では入れられません。取り込む範囲に `data/` が入らず、国語の検査が動かなくなるためです。手元の v0.21.0 で確かめたのは URL 経由の取り込みで、GitHub の識別子を使う経路は、文書の記述によります([確認の記録](opencode-hermes-checks.md#判断))。

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

終了コードは、問題なしなら 0、誤りがあれば 1、引数が不正なら 2 です。警告(古い版など)では、1 にしません。正本との比較を省くときは、`--no-source` を付けます。正本との差を誤りとして扱うときは、`--strict-source` を付けます。実行するスクリプトの Python は、`verify_install.py` を動かした Python です。エージェントが使う Python で実行してください。

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

`npx skills remove` で、入れたものを削除します(2026-11-10、隔離したホームで確かめました)。

```bash
npx skills remove japanese-readability-editor -g
```

手動でコピーしたものは、`japanese-readability-editor/` のフォルダだけを削除します(`skills/` ディレクトリと、ほかの Skill は残します)。リンクにしたものは、リンクだけを削除します。

```bash
rm -r ~/.claude/skills/japanese-readability-editor
```

次の環境で入れたものは、`npx skills remove` では削除できません。

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
