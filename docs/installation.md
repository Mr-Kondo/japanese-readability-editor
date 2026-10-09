# インストール

取得から、動作確認、更新、削除までを、順に説明します。手早く入れるだけなら、README の「[クイックスタート](../README.md#クイックスタート)」で足ります。

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

問題がなければ、`--dry-run` を外して実行します。使う環境に合わせて、次の表から引数を選び、`python3 tools/install.py` に続けて指定します。

| 使う環境 | ユーザー全体に入れる | 特定のプロジェクトに入れる |
|---|---|---|
| Codex、Copilot、Gemini CLI | `--scope user --target common` | `--scope workspace --target common` |
| Claude Code | `--scope user --target claude-code` | `--scope workspace --target claude-code` |
| Antigravity(IDE と CLI) | `--scope user --target antigravity` | `--scope workspace --target common` |
| すべて | `--scope user --target all` | `--scope workspace --target all` |

たとえば、Codex と Claude Code をユーザー全体で使う場合は、次のとおりです。

```bash
python3 tools/install.py --scope user --target codex
python3 tools/install.py --scope user --target claude-code
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
| `all` | `.agents/skills/` と `.claude/skills/` | `common`、`claude-code`、`antigravity-ide`、`antigravity-cli` の配置先 |

各製品が Skill を探す場所は、ほかにもあります。一覧は、[環境別の対応](environments.md#対応表)にあります。

### 安全な挙動

- 既にある場合は、何もしません(`--on-conflict skip`、既定)。
- `--on-conflict backup` は、既存のものを `skills.bak/` へ退避してから配置します。退避先は Skill の探索先の外です。
- `--on-conflict overwrite` は、既存のものを削除して配置します。`SKILL.md` を持たないディレクトリは、削除を拒否します。
- 配置は、複製が終わってから所定の場所へ移すので、途中で失敗しても中途半端なものを残しません。
- 既定はコピーです。`--link` でシンボリックリンクにできます。Windows では権限が必要な場合があります。

## 動作を確認する

環境ごとに、Skill が読み込まれたかを確認します。表示されない場合は、セッションを開き直してください。

| 環境 | 確認方法 |
|---|---|
| Codex | `/skills` の一覧に出る。`$japanese-readability-editor` で呼べる |
| Claude Code | `/` のメニューに `japanese-readability-editor` が出る |
| Gemini CLI | `/skills list`、または端末で `gemini skills list`。追加した直後は `/skills reload` |
| Antigravity | `/japanese-readability-editor` で呼べる |
| GitHub Copilot | 公式資料に確認方法の記載を見つけられなかったため、次の依頼で試す |

どの環境でも、実際に依頼して確かめられます。

```text
次の文章を japanese-readability-editor で校正して。
「このシステムは、ユーザーから入力されたデータを受け取り、それを検証したうえで、問題がなければデータベースに保存し、問題があればエラーとして呼び出し元に返す。」
```

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

## SudachiPy を入れる(任意)

`compare_rewrite.py` は、SudachiPy と辞書が入っていれば、否定と文の対応をより正確に判定します。入っていなければ、標準ライブラリだけで動きます。どちらで動いたかは、出力の `tokenizer` で分かります。

国語の表記の検査(`check_kokugo.py`)は、SudachiPy を使いません。形態素解析の有無で出力が変わらないようにするためで、品詞が決まらない語は要確認に下げます([限界](kokugo.md#検査していないもの限界))。

Skill は、利用者の手元の環境には、SudachiPy を断りなく入れません。実行中に入れるのは、利用者の手元ではない、クラウドの実行環境だけです。

| 環境 | 入れ方 |
|---|---|
| Codex、Claude Code、GitHub Copilot(CLI とエディタ)、Gemini CLI、Antigravity | 先に、手元の Python に入れておく(下のコマンド) |
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

辞書は、core と small のどちらでも動きます。インストール後の大きさは、core が約190MB、small が約110MBです。`skill/japanese-readability-editor/assets/examples.md` の18組の修正例では、どちらも同じ指摘になりました。クラウドの実行環境では、入れる時間を短くするために、Skill は small を使います。

SudachiPy と辞書は、ZIP には含めません。小さい small の辞書でも、配布用のファイルが約42MBあり、ChatGPT のアップロードの上限(1ファイルあたり25MB)を超えるためです。アップロード型の環境では、エージェントが実行中に small を入れます。入らなければ、標準ライブラリの経路で動きます。

注: Claude のアプリでは、まだ確かめていません。

- Claude のアプリでは、組織のネットワークの設定によります([Claude Help Center](https://support.claude.com/en/articles/12111783-create-and-edit-files-with-claude))。Team の既定は、パッケージ管理ツール(PyPI など)だけを許可します。Enterprise の新しい組織では、既定で無効です。Cowork での扱いは、確認できていません。
- Copilot のクラウドエージェントでは、既定の許可リストに、Python のパッケージ置き場が含まれます([GitHub Docs](https://docs.github.com/en/copilot/how-tos/use-copilot-agents/coding-agent/customize-the-agent-firewall))。
- Codex のクラウド環境では、setup script がネットワークを使えます。エージェントの実行中は、既定では使えません([Codex: Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environment))。

## 更新する

リポジトリを更新してから、`--on-conflict` を付けて配置し直します。`backup` は、以前のものを退避してから配置します。

```bash
git pull
python3 tools/install.py --scope user --target all --on-conflict backup
```

`--link` でインストールした場合は、複製ではなく正本へのリンクなので、`git pull` だけで反映されます。ただし、リポジトリを移動すると、リンクが切れます。

複製で入れたものをリンクに切り替える場合は、`--on-conflict backup` を付けます。付けないと、既にある複製を残したまま、何もせずに終わります。

```bash
python3 tools/install.py --scope user --target all --link --on-conflict backup
```

アップロード型の環境では、新しい ZIP を、もう一度アップロードします。ZIP は、Release からダウンロードするか、`python3 tools/package.py` で作ります。

ChatGPT では、同じ名前の Skill があると、置き換えの確認(Skill already exists)が出ます。「Replace existing」を選ぶと、同じ Skill が更新されます。重複はしません。置き換えた後の表示は、[実機確認](chatgpt-work-checks.md#同じ名前の-skill-の置き換え)にあります。

Claude のアプリでは、Skill の詳細画面から置き換えます。2026-10-07 に、Pro プランのアカウントで確かめました。

1. Customize → Skills で、`japanese-readability-editor` を開きます。
2. 右上の「⋮」から「Replace」を選びます。
3. 新しい ZIP を選び、「Upload」を押します。アップロードのときに、セキュリティスキャンが走ります。

置き換えると、同じ Skill の版が1つ上がります(v1 から v2 など)。有効のままです。一覧の行の「⋮」には、「Replace」がありません。置き換えた直後は、前の版の内容が表示されることがあります。ページを再読み込みすると、新しい版が表示されます。

Claude Code のプラグインとして入れた場合は、マーケットプレースを更新してから、プラグインを更新します。

```bash
claude plugin marketplace update japanese-readability-editor
```

```bash
claude plugin update japanese-readability-editor@japanese-readability-editor
```

`claude plugin update` だけでは、更新されません。手元に取得したマーケットプレースが古いままなので、「already at the latest version」と表示されます。更新した後は、Claude Code を再起動します。

プラグインの版は、コミットの短いハッシュで表示されます。`claude plugin list` の `Version` で確かめられます。

## 削除する

`tools/uninstall.py` で、配置先の `japanese-readability-editor/` を削除できます。配置先の指定は、インストーラと同じです(`--scope`、`--target`、`--workspace`、`--home`)。インストールしたときと同じ値を指定してください。

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
