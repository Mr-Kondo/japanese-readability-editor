# OpenCode と Hermes Agent の対応確認

OpenCode と Hermes Agent に対応したときの、仕様の確認と実機確認の記録です。導入の手順は[インストール](installation.md)、環境ごとの注意は[環境別の対応](environments.md)にあります。

確認日は 2026-10-10 です。公式文書は、取得した時点の内容です。ソースは、次のコミットの内容です。

| 対象 | 確認したもの | 版 |
|---|---|---|
| OpenCode | [Agent Skills](https://opencode.ai/docs/skills/)、[Config](https://opencode.ai/docs/config/) | 2026-10-10 に取得 |
| OpenCode | [sst/opencode](https://github.com/sst/opencode) のソース | `055d95bb7e27`(2026-10-09) |
| OpenCode | 手元の実機 | `opencode 2.0.20`(Homebrew) |
| Hermes Agent | [Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)、[Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles) | 2026-10-10 に取得 |
| Hermes Agent | [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) のソースと文書 | `46d7718a52ff`(2026-10-09) |
| Hermes Agent | 手元の実機 | `Hermes Agent v0.21.0 (2026.8.31)` |

公式文書は、ページ取得ツールの要約を通して読みました。文書に記載のない項目や、実装に頼る項目は、ソースを読んで確かめ、根拠を分けて書いています。ソースの版と実機の版は、一致するとは限りません(OpenCode のソースは `packages/opencode` が 1.18.35、実機は 2.0.20)。ソースだけが根拠の項目は、実機では確かめていません。

## 公式資料で確認した仕様

### OpenCode

| 項目 | 内容 | 根拠 |
|---|---|---|
| ファイルの形式 | スキル名のフォルダの直下に、全大文字の `SKILL.md`。先頭に YAML frontmatter が要る | 文書 |
| メタデータ | `name` と `description` が必須。`license`、`compatibility`、`metadata` は任意。未知のフィールドは無視される | 文書 |
| 名前 | 1〜64字。`^[a-z0-9]+(-[a-z0-9]+)*$`。`SKILL.md` を含むディレクトリ名と一致 | 文書 |
| `description` | 1〜1024字 | 文書 |
| 探索先(プロジェクト) | `.opencode/skills/<name>/`、`.claude/skills/<name>/`、`.agents/skills/<name>/`。作業ディレクトリから git の worktree まで、親へたどる | 文書 |
| 探索先(ユーザー共通) | `~/.config/opencode/skills/<name>/`、`~/.claude/skills/<name>/`、`~/.agents/skills/<name>/` | 文書 |
| 設定ディレクトリの変更 | `OPENCODE_CONFIG_DIR` のディレクトリも、`.opencode` と同じように探索される | 文書(Config) |
| `XDG_CONFIG_HOME` | 文書にはない。実装は `xdg-basedir` で `$XDG_CONFIG_HOME/opencode` を使う | ソース `packages/core/src/global.ts` |
| 探索の無効化 | `OPENCODE_DISABLE_EXTERNAL_SKILLS`(`.claude` と `.agents` を読まない)、`OPENCODE_DISABLE_CLAUDE_CODE`、`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS`(`.claude` だけ) | ソース `packages/opencode/src/effect/runtime-flags.ts`(v1) |
| 同名の Skill | 文書は「名前を一意にする」とだけ書く。v1 のソースは、警告をログに出し、あとから登録した方が残る。読み込みが並列なので、順序は保証されない。v2 のソースは、あとのソースが前のものを上書きする | ソース `packages/opencode/src/skill/index.ts`、`packages/core/src/skill.ts` |
| 読み込み | `skill` ツールに `name` を渡す。`<available_skills>` に名前と説明が並ぶ | 文書 |
| 権限 | `permission.skill` の `allow`、`deny`、`ask`。`tools.skill: false` でツールを無効にできる | 文書 |
| 資料とスクリプトへの到達 | 文書にはない。`skill` ツールの出力に `Base directory for this skill: <絶対パス>` と、`scripts/` などの相対パスはそこからの相対という注記が入る | ソース `packages/opencode/src/tool/skill.ts`、`packages/core/src/tool/skill.ts` |
| 設定による追加 | `skills.paths`、`skills.urls`。文書にはなく、v1 のソースにある | ソース(v1) |
| v2 の注意 | skills ディレクトリの直下の `*.md` も Skill として読む実装になっている。`.claude/skills` と `.agents/skills` を読む処理は、v2 の `packages/core` では見つからなかった | ソース `packages/core/src/skill.ts`、`packages/core/src/config/plugin/skill.ts` |

### Hermes Agent

| 項目 | 内容 | 根拠 |
|---|---|---|
| ファイルの形式 | `SKILL.md` に YAML frontmatter。例は `name`、`description`、`version`、`platforms`、`metadata.hermes.*`。必須のフィールドは明記されていない | 文書 |
| 名前の制約 | 探索側の制約は文書にない。Agent が作る Skill には `^[a-z0-9][a-z0-9._-]*$`、64字、`description` 1024字の制約がある | ソース `tools/skill_manager_tool.py` |
| 置き場所 | `~/.hermes/skills/`(Hermes のホームの `skills/`)。カテゴリのフォルダで入れ子にできる | 文書 |
| ホームとプロファイル | プロファイルは別のホームで、`~/.hermes/profiles/<名前>`。既定のプロファイルは `~/.hermes` 自身。`HERMES_HOME` で切り替わり、`hermes -p <名前>` で指定する。Skill はプロファイルごとに独立 | 文書(Profiles) |
| ホームの決まり方 | 文書には優先順位がない。ソースでは、(1) `-p` の指定、(2) `HERMES_HOME` が `profiles/<名前>` ならそれ、(3) `<根>/active_profile` の `hermes profile use`、(4) `HERMES_HOME`、(5) 既定の `~/.hermes`(Windows は `%LOCALAPPDATA%\hermes`) | ソース `hermes_constants.py`、`hermes_cli/main.py`、`hermes_cli/profiles.py` |
| プロジェクト単位の探索 | 文書にある。`<プロジェクトの根>/.hermes/skills/` と `.agents/skills/`。根は `.git` を持つ最も近い祖先。`hermes skills trust` で信頼するまで読み込まない。`skills.project_discovery: false` で無効 | 文書 |
| 外部ディレクトリ | `config.yaml` の `skills.external_dirs`。書き込み保護の境界ではない。Agent の更新は、見つけた場所をそのまま書き換える | 文書 |
| 同名の Skill | `project`、プロファイル、`skills.create_dir`、`external_dirs` の順で、上位が勝つ。下位は隠れて、警告がログに出る。同じ階層の別物は、曖昧としてエラーになる | 文書 |
| 読み込み | `skills_list()`、`skill_view(name)`、`skill_view(name, path)`、`/skill-name`、`hermes -s <名前>`、`hermes chat -s <名前> -q "..."`、`hermes skills list` | 文書と CLI の `--help` |
| 資料とスクリプトへの到達 | Skill を読み込んだときのメッセージに `[Skill directory: <絶対パス>]` と、相対パスをその場所から解決する指示が入る。`${HERMES_SKILL_DIR}` も使えるが、この Skill は使わない | 文書(developer-guide)、ソース `agent/skill_commands.py` |
| コンテナとリモート | Docker と Singularity は bind mount、SSH、Modal、Daytona は `~/.hermes` の状態(Skill を含む)を送る。Skill は、ホームの `skills/`、`external_dirs`、信頼したプロジェクトの Skill が対象。シンボリックリンクは送られない | 文書(configuration)、ソース `tools/credential_files.py` |
| `hermes skills install` | 受け付けるのは Hub の識別子か、`SKILL.md` の URL。取り込むのは、`SKILL.md` と、そこから参照された `references/`、`templates/`、`scripts/`、`assets/`、`examples/` のファイルだけ | 文書、ソース `tools/skills_hub_models.py` |

## 判断

- **共通の `SKILL.md` を変えない。** どちらの環境も、必須は `name` と `description` で、この Skill はすでに満たす。名前は `^[a-z0-9]+(-[a-z0-9]+)*$` に合い、ディレクトリ名と一致する。環境ごとに frontmatter を足す必要はなかった。
- **導入は `tools/install.py` のコピーにする。** Hermes の `hermes skills install` は、この Skill では使えない。取り込む範囲に `data/` が入らず、`SKILL.md` から参照されない `scripts/kokugo_engine.py` も落ちる。手元の Hermes v0.21.0 で `SKILL.md` に対して取り込み対象を調べたところ、18ファイルのうち11ファイルだけが対象で、`data/` はなかった。国語の検査は、`data/` と `kokugo_engine.py` がないと動かない。
- **Hermes のコンテナとリモートの backend には、コピーで入れる。** シンボリックリンクは送られないので、`--link` は警告する。
- **`all` に OpenCode と Hermes を入れない。** 使っていない製品の設定ディレクトリを、利用者のホームに作らないため。既存の `all` の挙動も変えない。
- **`.opencode/skills/` と `~/.config/opencode/skills/` を OpenCode の配置先にする。** OpenCode は `.agents/skills/` と `.claude/skills/` も読むので、`--target common` や `claude-code` で入れた Skill も見える。両方に置くと重複する。重複は検出して警告し、削除はしない。
- **`skills.external_dirs`(Hermes)と `skills.paths`(OpenCode)は、既定では使わない。** 正本のリポジトリを指すと、Agent が正本を書き換えうる。Hermes の `external_dirs` は、書き込み保護の境界ではないと文書が書く。
- **プロジェクト単位の Hermes の探索には対応した。** 公式文書に記載があり、手元で動作を確認した。`hermes skills trust` は、利用者が判断することなので、このツールは実行しない。

## 実機確認

実機の確認は、隔離した環境で行いました。OpenCode は `HOME` と `XDG_*` を、Hermes は `HOME` と `HERMES_HOME` を、一時ディレクトリへ向けています。利用者の設定ディレクトリと認証情報は、読み書きしていません。Hermes は、手元にインストールされた本体のプログラム(`~/.hermes/hermes-agent`)を読み込んで実行しました。版の表示(`--version`)だけは、隔離せずに実行しています。空白と日本語を含むパスで実施しました。

### Hermes Agent v0.21.0

| 確認 | 結果 |
|---|---|
| `tools/install.py --scope user --target hermes` が、`HERMES_HOME` の `skills/` に置く | 実施。`$HERMES_HOME/skills/japanese-readability-editor/` に置いた |
| `hermes skills list` で Skill が見つかる | 実施。`local`、`enabled` で表示された |
| `skills_list()`、`skill_view(name)`、`skill_view(name, path)` で本文と参照資料を読み込める | 実施(Hermes 本体の関数を直接呼んだ)。本文 7391 字、`references/readability-rules.md` 17011 字を取得できた |
| スラッシュコマンドと、読み込みメッセージの `[Skill directory: ...]` | 実施。`/japanese-readability-editor` が登録され、メッセージに絶対パスが入った |
| そのパスで、Skill の外のディレクトリから `scripts/` を実行する | 実施。`measure.py` と `check_kokugo.py` が終了コード 0 |
| プロジェクト単位の探索 | 実施。`.hermes/skills/` に置いた Skill は、`hermes skills trust` の前は一覧に出ず、後に出た。スキャンによる隔離はされなかった |
| `hermes skills install` の取り込み範囲 | 実施(Hermes 本体の `_referenced_support_paths` を、この Skill の `SKILL.md` に対して呼んだ)。11ファイルで、`data/` を含まない |
| モデルを介した動作(Skill が選ばれ、依頼のスクリプトが実行される) | **未実施**。隔離環境にモデルの認証情報がなく、利用者の認証情報は使っていない |
| Docker、SSH、Modal、Daytona、Singularity の backend | **未実施**。ソースの読み取りだけ |
| Windows、ゲートウェイ(メッセージング) | **未実施** |

### OpenCode 2.0.20

| 確認 | 結果 |
|---|---|
| `tools/install.py --scope user --target opencode` が、`$XDG_CONFIG_HOME/opencode/skills/` に置く | 実施 |
| `opencode debug paths` の設定ディレクトリが、インストーラの解決と一致する | 実施。隔離した `XDG_CONFIG_HOME` で、`config` が `$XDG_CONFIG_HOME/opencode` だった |
| Skill が発見される | **未実施** |
| 本文と参照資料の読み込み(`skill` ツール) | **未実施** |
| サンプル依頼でスクリプトが実行される | **未実施** |

未実施の理由は 2 つです。`opencode run` はローカルのサーバを起動しますが、この環境ではローカルポートの待ち受けが許可されておらず、`Failed to start server` で終わりました。隔離環境にはモデルの認証情報もありません。2.0.20 には、Skill を一覧する `debug skill` もありません(ソースの 1.x 系にはあります)。

構造検証、`tools/verify_install.py`、ソースの読み取りは、この未実施の代わりにはなりません。OpenCode の実機での動作は、確認できていません。

## 確認できなかったこと

- OpenCode 2.0.20 が、`.claude/skills` と `.agents/skills` を読むか。文書は読むと書くが、v2 のソースでは処理を見つけられなかった
- OpenCode で、同名の Skill が複数あるときに、どれが使われるか
- 両環境で、`モード A`、`モード B`、`モード C` の指定が守られるか
- Hermes の `hermes skills install` が、GitHub の識別子で取り込む範囲。URL の経路は手元の版で確かめたが、GitHub の経路は、文書の記述とソースの読み取りだけ

## 今回の作業で見つけた、既存の限界

今回の対応には必要がないので、直していません。別に扱います。

- `compare_rewrite.py` の数値の抽出は、単位を 1 文字の列挙と英字に限る。`100ミリ秒` を `100マイクロ秒` に変えても、数値の変化として挙がらない(`terms` にカタカナ語の追加が出るだけ)。`100ミリ秒` を `100秒` に変えると、挙がる。
