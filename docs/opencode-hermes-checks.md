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
| モデルを介した動作(Skill が選ばれ、依頼のスクリプトが実行される) | 実施(手元のローカルモデルで)。結果は下の「モデルを介した動作」 |
| Docker、SSH、Modal、Daytona、Singularity の backend | **未実施**。ソースの読み取りだけ |
| Windows、ゲートウェイ(メッセージング) | **未実施** |

**モデルを介した動作(Ollama のローカルモデル)**

モデルは、手元で動いている Ollama の `gemma4-12b-64k` と `qwen3-coder:30b` です。Hermes の設定は、隔離した `HERMES_HOME` の `config.yaml` に、`provider: custom` と Ollama の `base_url` だけを書きました。利用者の設定と認証情報は、使っていません。`sandbox-exec` で、書き込みを作業用ディレクトリだけ、通信を `localhost` だけに絞りました。実行は `hermes chat -Q -q "..."` で、標準入力を閉じ、外から時間制限を付けました。作業用ディレクトリは、空白と日本語を含むパスです。対象の `sample.md` は、数値・単位・URL・コードを含む 2 段落です。

| モデル | 依頼 | 結果 |
|---|---|---|
| `gemma4-12b-64k` | 「`japanese-readability-editor` スキルを使って、`sample.md` の段落と文の長さを計測して」(通常の依頼、1回) | **失敗**。`skill_view` で Skill を読んだ。結果に `skill_dir` が入っていたが使わず、`python3 scripts/measure.py` を作業ディレクトリで実行して失敗した。探索を繰り返し、結果が出ないまま止まった(外から終了させるまで約 55 分) |
| `gemma4-12b-64k` | 「`sample.md` の段落と文の長さを計測して」に、`-s japanese-readability-editor` を付けた(3回) | **2回成功、1回失敗**。成功した回は、`[Skill directory]` の絶対パスで `measure.py` を実行した。結果は、独立に実行した値と一致した(235字、2段落、4文、46字以上の文が2つ)。失敗した回は、相対パスで実行して失敗し、結果が出なかった |
| `gemma4-12b-64k` | `-q` に `/japanese-readability-editor sample.md の段落と文の長さを計測して。`(1回) | Skill は起動しなかった。`-q` に書いたスラッシュコマンドは展開されず、Skill を読まないまま、文字数を推定で答えた。実測と合わない(46字以上の文は、146字と46字) |
| `gemma4-12b-64k` | `-s` を付けて、「モード C で `sample.md` に適用して。文章は変えず、改行と空行だけで」(1回) | 文言は保たれた(返信を `verify_preservation.py --strict` にかけて合格)。ただし、改行は足さず、ファイルにも書かなかった |
| `gemma4-12b-64k` | `-s` を付けて、「モード B で `sample.md` を読みやすく書き換えて。そのまま上書きしてよい」(1回) | ファイルは書き換わらず、返信に書き換え案が出た。`compare_rewrite.py` では、数値・URL・コードの欠落はなかった。「義務」の表現が 1 から 0 に減った。返信にあった「検証結果」は、スクリプトを実行したものではない |
| `qwen3-coder:30b` | 最初の依頼と同じ(通常の依頼、1回) | **誤り**。`skill_view` の後、`python3 scripts/measure.py` を相対パスで実行して失敗し、自前の計算に切り替えた。「すべての文が 30〜45 字で、修正不要」と答えたが、実測では 146字と46字の文がある |
| `qwen3-coder:30b` | `-s` を付けて、計測(1回) | **誤り**。`measure.py` を絶対パスで実行するところまでは正しかった。その後、`sample.md` を作り直して、行番号(`1\|`)つきの別ファイル(386字)を計測し、「修正不要」と答えた。`sample.md` は書き換わらなかった |
| `qwen3-coder:30b` | `-s` を付けて、モード C(2回) | **守られなかった**。1回は、ツール呼び出しが文字のまま出力された。もう1回は、行番号(`1\|`)を含む `sample_formatted.md` を作り、自分で `verify_preservation.py --strict` を実行して失敗を報告した。ただし同じ返信で、「文字列は変更していない」とも述べた。独立に実行した `--strict` も失敗した。どちらの回も、`sample.md` は書き換わらなかった |

- **発見と読み込みは、モデルを介しても動いた。** モデルが自分で `skill_view` を呼び、本文を読んだ。
- **スクリプトの実行は、`-s` を付けた gemma4 の 3 回中 2 回だけ成功した。** 通常の依頼(2回)では、実行できなかった。qwen3-coder は、実際のファイルを計測して正しく答えた回がなかった。
- **失敗の多くは、相対パスだった。** `skill_view` の結果には、Skill の絶対パス(`skill_dir`)が入るが、モデルは使わなかった。SKILL.md の `python3 scripts/...` を、作業ディレクトリのまま実行した。`-s` やスラッシュコマンドの読み込みメッセージには、`[Skill directory: <絶対パス>]` と、相対パスをそこから解決する注記が付く(ソース `agent/skill_commands.py`)。
- **`read_file` の出力には、行番号(`1|`)が付く。** モデルがそれをファイルの内容として書いた回が、3回あった(いずれも qwen3-coder)。1回は、Hermes が書き込みを拒否して、ファイルは書き換わらなかった。
- **モデルの自己申告は、実測と合わなかった。** 「検証結果」(モード B)、「修正不要」(計測が2回)、「文字列は変更していない」(モード C)が、スクリプトの結果と食い違った。モードの指定が守られたかは、`verify_preservation.py --strict` などで、独立に確かめる必要がある。
- **1回目の実行は、止まったまま終わらなかった。** `--run-budget 900` を付けていたが効かず、約 55 分後に外から終了させた。止まった原因は、調べていない。自動で実行するときは、外から時間制限を付ける。
- **隔離の影響がある。** 隔離が `/tmp` への書き込みを拒否したため、qwen3-coder の 2 回(`-s` での計測と、モード C の 1 回目)は、一時ファイルを `/tmp` に作ろうとして失敗した場面が混ざっている。
- **回数は、条件ごとに 1〜3 回です。** 割合は目安です。モデルは、小型・中型のローカルモデルだけです。Claude や GPT などのホスト型の主要モデルでは、確かめていません。

### OpenCode 2.0.20

隔離は、`HOME` と `XDG_*` を一時ディレクトリへ向けて行いました。Skill の一覧は、`opencode serve`(`127.0.0.1` だけ)を一時的に起動し、`opencode api` で `GET /api/skill` を呼んで取りました。サンドボックスの外で実行しています。モデルは、手元で動いている Ollama(ローカル推論)です。

**発見**

| 配置先 | 結果 |
|---|---|
| `<プロジェクト>/.opencode/skills/` | 発見された |
| `$XDG_CONFIG_HOME/opencode/skills/` | 発見された |
| `<プロジェクト>/.agents/skills/` と `<プロジェクト>/.claude/skills/` | 発見された |
| `~/.agents/skills/` と `~/.claude/skills/` | 発見された |
| 何も置かない(対照) | 発見されない(組み込みの 2 件だけ) |

- `name`、`description`、本文は、`SKILL.md` と一致しました。
- 一覧は遅延して読み込まれます。サーバの起動後、最初の 1〜2 回の `GET /api/skill` は、空か組み込みの 2 件だけで、3 回目以降に Skill が出ました。起動直後に空でも、故障ではありません。
- 同名があるとき、プロジェクトの `.opencode/skills/` が、ユーザーの設定ディレクトリに勝ちました。ユーザーの設定ディレクトリは、`.agents/skills/` と `.claude/skills/`(プロジェクトとユーザー)に勝ちました。確かめたのは、この組み合わせだけです。
- `OPENCODE_CONFIG_DIR` に置いた場合は、確かめていません。

**読み込み**

プロジェクトの `.opencode/skills/` に置いた Skill について、`skill` ツールを `{"id": "japanese-readability-editor"}` で呼ぶと、`SKILL.md` の本文がそのまま返りました。ほかの配置先では、読み込みまでは確かめていません。出力には、`Base directory for this skill: <絶対パス>` と、相対パスはそこからの相対だという注記、サンプリングしたファイル一覧(`data/` を含む)が付いていました。API の `skills: [{"id": ...}]` で明示した場合も、同じ文章が注入されました。

**モデルを介した動作(Ollama のローカルモデル)**

OpenCode の無料のホスト型モデルは、「OpenCode の中からだけ使える」という制限で、403 を返しました(`opencode run` でも同じ)。提供側の利用条件なので、迂回していません。

| モデル | 依頼 | 結果 |
|---|---|---|
| `qwen2.5:7b` | 「`japanese-readability-editor` スキルを使って、`sample.md` の段落と文の長さを計測して」(3回) | 3回とも `skill` を呼んだ。スクリプトは実行できなかった。1回はコマンドを文章で出力して止まり、1回は空白を含むパスを引用符で囲まず失敗し、1回は `execute`(JavaScript の実行環境)に `python3 ...` を渡して構文エラー |
| `gpt-oss:20b` | 同じ依頼(2回) | `skill` を呼ばず、`glob` と `read` で自分で答えた |
| `gpt-oss:20b` | 同じ依頼に、API で Skill を明示(1回) | 本文は注入された。`python3 scripts/measure.py` をカレントからの相対パスで実行して失敗し、「スクリプトは存在しない」と結論した |
| `qwen3-coder:30b` | 同じ依頼(1回) | `skill` を呼び、`sample.md` を読んだ。スクリプトは実行せず、本文をそのまま返した |
| `qwen3-coder:30b` | 「`scripts/measure.py` を `--locate` 付きで実行し、Base directory を基準にした絶対パスで」と明示(1回) | **成功**。`skill` を呼び、`execute` で失敗した後、`shell` ツールで `measure.py --locate` を実行し、実際の計測結果(84字、46字以上の文が1つ)が返った |
| `qwen3-coder:30b` | 「モード C で `sample.md` に適用して。文章は変えず、改行と空行だけで」(1回。別の1回は、モデルが利用できず無効) | **守られなかった**。`skill` を呼び、`sample.md` を読んだ後、原文と無関係な文章を書き込み、「文言は一切変更せず」と報告した。独立に実行した `verify_preservation.py --strict` が失敗した |

つまり、Skill の発見と読み込みは確認できました。スクリプトの実行は、依頼で手順を明示した 1 回だけ成功しました。普通の依頼で、自発的に実行したモデルはありませんでした。モード C は、守られませんでした。これは、確かめたモデル(いずれも小型・中型のローカルモデル)の結果です。Claude や GPT などのホスト型の主要モデルでは、確かめていません。

**ほかに分かったこと**

- v2 で、シェルを実行するツールの名前は `shell` です。`execute` は JavaScript の実行環境で、`python3 ...` の文字列を渡すと構文エラーになります。
- `opencode run` は、標準入力が端末でないと、入力が閉じるまで待ちます。自動化するときは、`< /dev/null` で閉じます。
- 権限の規則は、最後に一致したものが勝ちます。`"bash": {"python3 *scripts/*": "allow", "*": "deny"}` のように、`"*": "deny"` を最後に書くと、そのツールが無効になります(今回、実際に起きました)。検証用に書いた `bash` と `shell` の規則が、効いたかどうかは確かめていません。この検証でのモデルのシェルは、実質的に制限されていませんでした。
- 利用者の認証情報と、ホームの設定は、読み書きしていません。検証後に、サーバを止め、Ollama のモデルを解放しました。

## 確認できなかったこと

- OpenCode の `OPENCODE_CONFIG_DIR` に置いた Skill が読まれるか(文書にはある。実機では確かめていない)
- OpenCode で、ホスト型の主要モデル(Claude、GPT など)が、普通の依頼で Skill のスクリプトを実行するか。モード C が守られるか
- Hermes で、ホスト型の主要モデル(Claude、GPT など)が、普通の依頼で Skill のスクリプトを実行するか。`モード A` が守られるか(`モード B` と `モード C` は、ローカルモデルで各 1〜2 回だけ)
- Hermes の対話セッションで、`/japanese-readability-editor` が Skill を起動するか(今回は非対話の `-q` だけ。そこでは起動しなかった)
- Hermes の `hermes skills install` が、GitHub の識別子で取り込む範囲。URL の経路は手元の版で確かめたが、GitHub の経路は、文書の記述とソースの読み取りだけ

## 今回の作業で見つけた、既存の限界

今回の対応には必要がないので、直していません。別に扱います。

- `compare_rewrite.py` の数値の抽出は、単位を 1 文字の列挙と英字に限る。`100ミリ秒` を `100マイクロ秒` に変えても、数値の変化として挙がらない(`terms` にカタカナ語の追加が出るだけ)。`100ミリ秒` を `100秒` に変えると、挙がる。
