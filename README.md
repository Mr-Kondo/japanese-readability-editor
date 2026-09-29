# japanese-readability-editor

生成AIが出力する日本語や、既存の日本語文書を、意味・精度・必要な情報量を保ったまま読みやすくする Agent Skill です。

一つの共通 `SKILL.md` を正本にします。次の環境で使えます。

- Codex、Claude Code、GitHub Copilot
- Gemini CLI、Antigravity(IDE と CLI)
- ChatGPT Work、Claude Cowork、Gemini Apps

環境ごとの差は、配置先、ZIP、README、生成物で吸収します。Skill 本文の複製はありません。

仕様の確認日は 2026-09-29 です。各製品の仕様は変わりやすいので、下の「環境別の対応表」は公式資料で確認できた範囲だけを書き、確認できなかった項目は「未確認」としています。

## 1. 目的

次のような問題を検出し、直します。

- 長すぎる段落、長すぎる文
- 主語・述語や論理関係の追いにくさ、次の展開の予測しにくさ
- 冗長、直訳調、抽象的な言い回し、AI特有の決めぜりふ

目的は、日本語を短くすることではありません。数値、条件、例外、因果関係、主体、固有名詞、技術用語、API名、コマンド、コード、URL、引用、出典を、読みやすさのために削ったり簡略化したりしません。

## 2. 設計思想

- 診断は、内容と論点、段落、文、構造、論理関係、予測可能性、主体、直訳調、抽象語、冗長、漢字の順に行います。漢字をひらくことから始めません。
- 「200字以上の段落」「80字以上の文」は、修正候補を見つける目安です。合否の基準ではなく、数字を満たすだけの機械的な分割はしません。
- 段落が長いだけなら、まず文言を変えずに、話題の境界で段落だけを分けます。このとき、空白以外の文字が変わっていないことをスクリプトで確認できます。
- スクリプトは候補を挙げ、文字列の一致を確かめるだけです。修正の要否と方法は、Agent が判断します。
- 日本語可読性の設計原則は、次の3記事を参考に、原則と手順として再構成しました。記事の文章は転載していません。
  1. [Qiita: masakai](https://qiita.com/masakai/items/7bc5250d04c4dc8669e4)
  2. [Zenn: ncdc](https://zenn.dev/ncdc/articles/6ea029ba5ecf65)
  3. [Zenn: lotation](https://zenn.dev/lotation/articles/8520b50540b274)

## 3. ディレクトリ構成

```text
japanese-readability-editor/
├── README.md
├── skill/japanese-readability-editor/     # 正本。配布するのはここだけ
│   ├── SKILL.md
│   ├── references/readability-rules.md
│   ├── scripts/measure.py
│   ├── scripts/verify_preservation.py
│   └── assets/examples.md
├── tools/
│   ├── install.py
│   ├── package.py
│   └── validate_skill.py
├── tests/
└── dist/                                  # 生成物。Git には含めない
```

## 4. 各ファイルの責務

| ファイル | 責務 |
|---|---|
| `SKILL.md` | 頻繁に使う判断とワークフロー。3つのモード、診断の順序、変更してはならないもの |
| `references/readability-rules.md` | 各診断段階の詳しい基準。Agent が迷ったときだけ読む |
| `assets/examples.md` | 修正前後の例。必要なときだけ読む |
| `scripts/measure.py` | 段落・文の長さなどの計測と、修正候補の位置の表示(読み取り専用) |
| `scripts/verify_preservation.py` | 空白以外の文字列が同一かの検査(読み取り専用) |
| `tools/install.py` | 各環境の配置先へコピーまたはリンクする |
| `tools/package.py` | ZIP、SHA-256、Gemini Apps 向けの出力を生成する |
| `tools/validate_skill.py` | Skill の構造と互換性を検証する |

## インストール手順

取得から、動作確認、更新、削除までを、順に説明します。配置先の詳細は、15 節と 16 節にあります。

### 必要なもの

- Python 3.9 以上
- Git(リポジトリを取得する場合)

インストーラも検証ツールも、Python の標準ライブラリだけで動きます。追加のパッケージは要りません。

### 取得する

```bash
git clone https://github.com/Mr-Kondo/japanese-readability-editor.git
cd japanese-readability-editor
```

リポジトリの公開範囲によっては、GitHub の認証が必要です。認証済みの `gh` があれば、次のコマンドでも取得できます。

```bash
gh repo clone Mr-Kondo/japanese-readability-editor
```

### Skill を検証する

```bash
python3 tools/validate_skill.py
```

`OK:` と表示されれば、配置できる状態です。

### インストールする

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

特定のプロジェクトに入れる場合は、`--workspace` にそのプロジェクトのパスを指定します。省くと、カレントディレクトリが対象です。

```bash
python3 tools/install.py --scope workspace --target all --workspace /path/to/project
```

配置先に同名の Skill が既にある場合は、何も変更しません。上書きするときの選び方は、16 節の「安全な挙動」にあります。

### 動作を確認する

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

### アップロード型の環境に入れる

ChatGPT Work、Claude Cowork、Gemini Apps は、配置先のディレクトリを持ちません。次のコマンドで生成物を作り、各製品の画面からアップロードします。

```bash
python3 tools/package.py
```

| 環境 | アップロードするもの | 詳細 |
|---|---|---|
| ChatGPT Work | `dist/japanese-readability-editor.zip` | 6 節 |
| Claude Cowork | `dist/japanese-readability-editor.zip` | 8 節 |
| Gemini Apps | `dist/gemini-apps/japanese-readability-editor/`、または `dist/gemini-apps-instructions.md` の貼り付け | 11 節 |

### 更新する

リポジトリを更新してから、`--on-conflict` を付けて配置し直します。`backup` は、以前のものを退避してから配置します。

```bash
git pull
python3 tools/install.py --scope user --target all --on-conflict backup
```

`--link` でインストールした場合は、複製ではなく正本へのリンクなので、`git pull` だけで反映されます。ただし、リポジトリを移動すると、リンクが切れます。

```bash
python3 tools/install.py --scope user --target all --link
```

アップロード型の環境では、`python3 tools/package.py` で作り直した ZIP を、もう一度アップロードします。

### 削除する

インストーラは、ファイルを削除する機能を持ちません。不要になったら、配置先の `japanese-readability-editor/` ディレクトリを、自分で削除してください。`--link` で入れた場合は、リンクだけを削除します。リンクの先にある正本は消えません。

配置先は、`--dry-run` の出力で確認できます。

## 5. 共通 Skill の使い方

Skill は、依頼の内容が `description` に合うと自動で使われます。名前を指定して呼ぶこともできます。

| 環境 | 明示的に呼ぶ方法 |
|---|---|
| Codex | `$japanese-readability-editor` |
| ChatGPT Work | `@japanese-readability-editor` |
| Claude Code | `/japanese-readability-editor` |
| Antigravity | `/japanese-readability-editor` |
| Gemini Apps | `/`(今後 `@`)に続けて Skill 名 |

3つのモードがあります。

- **A. 新規生成**: 読者、必要な情報、結論などを整理してから書きます。
- **B. Rewrite**: 意味を保ちながら書き換えます。
- **C. Paragraph-only**: 文章を変えずに、改行と空行だけで段落を分けます。

通常は完成した文章だけを返します。「レビューして」「問題点を挙げて」「計測して」「before/after を比べて」と頼んだときだけ、診断情報を示します。

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

### スクリプトを直接使う

Python 3.9 以上が必要です。標準ライブラリだけを使い、ネットワーク通信もファイルの書き込みもしません。

次のコマンドは、Skill のディレクトリで実行する場合の例です。ディレクトリは、`skill/japanese-readability-editor/` か、配置先の `japanese-readability-editor/` です。

```bash
python3 scripts/measure.py README.md
python3 scripts/measure.py --locate README.md
python3 scripts/measure.py --json README.md
python3 scripts/measure.py --locate docs/*.md
python3 scripts/verify_preservation.py before.md after.md
```

`measure.py` は、次の指標を出します。

- 総文字数、漢字率、ひらがな率
- 段落数、平均段落長、200字以上の段落数
- 文数、平均文長、80字以上の文数、1文あたりの平均読点数

`--locate` を付けると、候補のファイル名、行番号、長さ、冒頭を示します。次のものは、可能な範囲で解析から除きます。

- fenced code block と YAML frontmatter
- URL そのもの(Markdown のリンクは表示テキストだけを残す)
- Markdown の記号、見出し、表、水平線

英文の ASCII のピリオドは、文の区切りとして扱いません。日本語の文章を主な対象にしているためです。

`verify_preservation.py` は、空白を除いた文字列が一致すれば終了コード 0、しなければ 1 を返します(読み込みに失敗すると 2)。

> **注意**: このスクリプトが保証するのは「空白以外の文字列が変更されていないこと」だけです。意味の保存は保証しません。英単語の間の空白など、空白が意味を持つ箇所の変更も検出できません。

## 環境別の対応表

`Native Agent Skill` は、その環境が Agent Skills 形式(`SKILL.md` を含むフォルダ)を直接扱えるかを表します。

| Environment | Native Agent Skill | Workspace path | User/global path | ZIP upload | Notes |
|---|---|---|---|---|---|
| ChatGPT Work | あり(Business / Enterprise / Healthcare / Edu。管理者による有効化が必要な場合あり)※1 | 未確認 | 未確認 | 可。Plugins → Skills → Create → Upload from your computer。フォルダまたは ZIP ※1 | `@skill-name` で呼べる(公式)。Free / Plus / Pro は現行の提供対象外という記述あり ※1 |
| Codex | あり | `.agents/skills/`(カレントから repo root まで探索) | `$HOME/.agents/skills/` | 不要 | `$CODEX_HOME/skills` は旧仕様。管理者向けに `/etc/codex/skills` もある。変更は自動検出、出なければ再起動。symlink 可 |
| Claude Cowork | あり | 非対応(アップロード方式) | 非対応 | 可。Customize → Skills。ZIP の最上位にフォルダ | コード実行の有効化が必要。プランの記載は公式ページ間で異なる。`description` に200字の上限があるという記載あり |
| Claude Code | あり | `.claude/skills/` | `~/.claude/skills/` | 不要 | `.agents/skills` は読まない。未知の frontmatter は無視される。symlink 可 |
| GitHub Copilot | あり(cloud agent、code review、CLI、app、VS Code / JetBrains の agent mode) | `.agents/skills/`、`.github/skills/`、`.claude/skills/` | `~/.agents/skills/`、`~/.copilot/skills/` | 不要 | 利用できるプランは未確認 |
| Gemini Apps | あり(Skills。Gems は 2026-11 以降 Skills へ移行) | 非対応 | 非対応(アカウントに保存) | `SKILL.md` またはフォルダをアップロード。ZIP の可否は未確認 | `scripts/` の扱いは未確認。生成物は 11 節 |
| Gemini CLI | あり | `.agents/skills/`、`.gemini/skills/` | `~/.agents/skills/`、`~/.gemini/skills/` | 不要 | 同じ階層では `.agents/skills` が優先。`/skills list` で確認 |
| Antigravity IDE | あり | `.agents/skills/`(旧 `.agent/skills/` も互換) | `~/.gemini/config/skills/`(旧 `~/.gemini/antigravity/skills/`) | 不要 | `/<skill-name>` で呼べる |
| Antigravity CLI | あり | `.agents/skills/` | `~/.gemini/antigravity-cli/skills/` | 不要 | `~/.agents/skills` は自動では読まれないとする記述あり(Codelab)。未確認 |

※1 OpenAI ヘルプセンターの記事を自動取得できなかったため、開発者向けドキュメントの記述と、検索結果の要約に基づきます。提供状況はプラン、workspace の設定、リリース状況に依存します。存在しない機能を前提にせず、利用前に各自の画面で確認してください。

## 6. ChatGPT Work

ChatGPT のワークスペースに Skill をアップロードする方式です。`dist/japanese-readability-editor.zip` を使います。

1. `python3 tools/package.py` で ZIP を作ります。
2. ChatGPT の Plugins → Skills → Create → Upload from your computer で、ZIP を選びます。

Skill 機能がプラン、workspace の設定、管理者の許可に依存する点に注意してください。Enterprise と Edu では、管理者が有効化するまで表示されない場合があります。アップロード画面の名称と手順は変わる可能性があります。

## 7. Codex

Codex は `.agents/skills/` を、カレントディレクトリから repo root まで順にたどって探します。ユーザー全体の配置先は `$HOME/.agents/skills/` です。

```bash
python3 tools/install.py --scope workspace --target codex
python3 tools/install.py --scope user --target codex
```

従来の `${CODEX_HOME:-~/.codex}/skills/` は、現行の公式ドキュメントに記載がありません。旧仕様として非推奨になったと報告されています。

このリポジトリは、現行の `$HOME/.agents/skills/` を使います。旧版の Codex を使う場合は、手動で `$CODEX_HOME/skills/` へコピーしてください。

## 8. Claude Cowork

Claude のアプリ(Cowork を含む)には、ZIP をアップロードします。ChatGPT Work と同じ ZIP を再利用します。

1. `python3 tools/package.py` で ZIP を作ります。
2. Customize → Skills から、`dist/japanese-readability-editor.zip` を追加します。

ZIP は、Skill のフォルダが最上位にある構造です。コード実行の有効化が必要です。Claude Code の `~/.claude/skills/` は、Cowork のセッションでは読み込まれません。

この Skill の `description` は、Claude のヘルプ記事にある「200字以内」の記載に合わせて、200字以内に収めています。Agent Skills の仕様と Claude API の文書は、1024字までを許しています。

## 9. Claude Code

```bash
python3 tools/install.py --scope workspace --target claude-code   # <project>/.claude/skills/
python3 tools/install.py --scope user --target claude-code        # ~/.claude/skills/
```

Claude Code は `.agents/skills/` を読みません。Codex などと同じプロジェクトで使う場合は、`--target all` で両方に配置します。複製を避けたい場合は、`--link` でシンボリックリンクを作れます。

## 10. GitHub Copilot

Copilot は、次の場所から Skill を読みます。

- プロジェクト: `.agents/skills/`、`.github/skills/`、`.claude/skills/`
- 個人: `~/.agents/skills/`、`~/.copilot/skills/`

この repo は共通配置の `.agents/skills/` を使い、`.github/skills/` へは複製しません。

```bash
python3 tools/install.py --scope workspace --target copilot
python3 tools/install.py --scope user --target copilot
```

Copilot には、Skill のほかに指示ファイルがあります。今回の用途は、常に適用するルールではなく、必要なときに読み込む手順なので、Agent Skill を使います。

| 仕組み | 置き場所 | 適用のされ方 |
|---|---|---|
| Agent Skills | `.agents/skills/<name>/SKILL.md` など | 関連するときに読み込まれる。詳細な手順向き |
| リポジトリ全体の指示 | `.github/copilot-instructions.md` | 常に適用される。プロジェクト全体の方針向き |
| パス別の指示 | `.github/instructions/*.instructions.md` | `applyTo` に合うファイルを扱うときに適用される |
| エージェント向けの指示 | `AGENTS.md`(`CLAUDE.md`、`GEMINI.md` も) | エージェントが参照する。ディレクトリ木で最も近いものが優先される |

## 11. Gemini Apps

Gemini CLI とは別の製品です。

Gemini Apps では、Gems が 2026-11-17 から Skills に移行します。これは個人の Google アカウントの日程です。Workspace の business / enterprise は 2027-03、education は 2027-06です。

Skills は、`SKILL.md` またはそれを含むフォルダをアップロードして作れます。公式資料が挙げるファイルの種類は、テキスト、PDF、画像です。`scripts/` にある `.py` を扱えるかは、記載がありません。

このため、`tools/package.py` は、共通 Skill から次の2つを生成します。どちらも共通 Skill から機械的に作る出力で、別実装ではありません。

| 生成物 | 使い方 |
|---|---|
| `dist/gemini-apps/japanese-readability-editor/` | `scripts/` を除いたコピー。Skills へフォルダごとアップロードする |
| `dist/gemini-apps-instructions.md` | Gem の指示、または Custom Instructions に貼り付ける |

指示文は、Part 1(`SKILL.md` の本文)と Part 2(詳細ルール)からなります。文字数の上限で貼れない場合は、Part 2 を省いてください。上限は公式資料で確認できていません。Gemini Apps では `scripts/` を実行できないので、計測と検証は Agent が手作業で近似します。

## 12. Gemini CLI

```bash
python3 tools/install.py --scope workspace --target gemini-cli   # <project>/.agents/skills/
python3 tools/install.py --scope user --target gemini-cli        # ~/.agents/skills/
```

`.agents/skills/` は `.gemini/skills/` の別名で、同じ階層では優先されます。適用順は、ワークスペース、ユーザー、拡張機能、組み込みの順です。確認と管理には、次の機能を使えます。

- 対話中: `/skills list`、`/skills reload`、`/skills enable <name>`、`/skills disable <name>`、`/skills link <path>`
- 端末: `gemini skills list`

Skill が有効になるときは、名前と参照するディレクトリを示す確認画面が出ます。

## 13. Antigravity IDE

```bash
python3 tools/install.py --scope workspace --target antigravity-ide   # <project>/.agents/skills/
python3 tools/install.py --scope user --target antigravity-ide        # ~/.gemini/config/skills/
```

ワークスペースは `.agents/skills/` です。旧称の `.agent/skills/` は互換のために読まれますが、新しい `.agents/skills/` を優先します。グローバルは `~/.gemini/config/skills/` で、旧配置の `~/.gemini/antigravity/skills/` も互換のために読まれます。

## 14. Antigravity CLI

```bash
python3 tools/install.py --scope workspace --target antigravity-cli   # <project>/.agents/skills/
python3 tools/install.py --scope user --target antigravity-cli        # ~/.gemini/antigravity-cli/skills/
```

グローバルの配置先が、IDE とは異なります。IDE と CLI の両方に入れる場合は `--target antigravity` を使います。

## 15. ワークスペースへのインストール

共通配置の `.agents/skills/` に置くと、Codex、Copilot、Gemini CLI、Antigravity が読みます。Claude Code だけは `.claude/skills/` が必要です。

```bash
python3 tools/install.py --scope workspace --target common --workspace /path/to/project
python3 tools/install.py --scope workspace --target all --workspace /path/to/project
```

`--workspace` を省くと、カレントディレクトリが対象です。`--target all` は、`.agents/skills/` と `.claude/skills/` の2か所に配置します。Copilot は両方を読むので、同じ Skill が2つ見える可能性があります。Copilot を使うプロジェクトでは、必要な環境だけを指定してください。

必ず先に `--dry-run` で、配置先を確認できます。

```bash
python3 tools/install.py --scope workspace --target all --dry-run
```

## 16. グローバル(ユーザー)へのインストール

```bash
python3 tools/install.py --scope user --target codex
python3 tools/install.py --scope user --target claude-code
python3 tools/install.py --scope user --target copilot
python3 tools/install.py --scope user --target gemini-cli
python3 tools/install.py --scope user --target antigravity
python3 tools/install.py --scope user --target all --dry-run
```

| target | user scope の配置先 |
|---|---|
| `common`、`codex`、`copilot`、`gemini-cli` | `~/.agents/skills/` |
| `claude-code` | `~/.claude/skills/` |
| `antigravity-ide` | `~/.gemini/config/skills/` |
| `antigravity-cli` | `~/.gemini/antigravity-cli/skills/` |
| `antigravity` | 上の2つ(IDE と CLI) |
| `all` | `common`、`claude-code`、`antigravity-ide`、`antigravity-cli` |

同じ場所になる target は、1回だけ配置します。`--target` は、繰り返しても、カンマ区切りでも指定できます。

### 安全な挙動

- 既にある場合は、何もしません(`--on-conflict skip`、既定)。
- `--on-conflict backup` は、既存のものを `skills.bak/` へ退避してから配置します。退避先は Skill の探索先の外です。
- `--on-conflict overwrite` は、既存のものを削除して配置します。`SKILL.md` を持たないディレクトリは、削除を拒否します。
- 配置は、複製が終わってから所定の場所へ移すので、途中で失敗しても中途半端なものを残しません。
- 既定はコピーです。`--link` でシンボリックリンクにできます。Windows では権限が必要な場合があります。

## 17. パッケージ生成

```bash
python3 tools/package.py
```

```text
dist/
├── japanese-readability-editor.zip          # ChatGPT Work / Claude Cowork のアップロード用
├── japanese-readability-editor.sha256
├── gemini-apps-instructions.md              # Gemini Apps の Gem / Custom Instructions 用
└── gemini-apps/japanese-readability-editor/ # Gemini Apps の Skills 用(scripts/ なし)
```

ZIP の最上位は `japanese-readability-editor/` の1フォルダです。その直下に、`SKILL.md`、`references/`、`scripts/`、`assets/` が入ります。ZIP のルートへ直接 `SKILL.md` を置く構造ではありません。

ZIP は再現可能で、同じ入力からは同じ SHA-256 になります。`--no-gemini-apps` で、Gemini Apps 向けの出力を省けます。

## 18. 検証

```bash
python3 tools/validate_skill.py
```

次を確認し、エラーがあれば終了コード 1 を返します。

- `SKILL.md` が、大文字小文字まで正確な名前で存在する
- frontmatter が先頭にあり、`name`(`japanese-readability-editor`)と `description` がある
- `name` がディレクトリ名と一致する
- 製品固有の frontmatter がない(`name` と `description` 以外は誤りとして扱う)
- 参照する `references/`、`scripts/`、`assets/` のファイルが存在する
- skill の外を指す `../` や絶対パスがない
- `scripts/` の Python が、通信、外部コマンドの実行、ファイルの削除と書き込みをしない
- ZIP にできる

frontmatter は、どのエージェントの解析器でも読める、保守的な YAML の部分集合に限ります。値は1行で書き、値の中の `: ` と ` #` は避けます。

## 19. テスト

```bash
python3 -m unittest discover -s tests -v
```

標準ライブラリの `unittest` だけを使います。対象は、次の5つです。

- `measure.py`、`verify_preservation.py`
- `validate_skill.py`、`install.py`、`package.py`

## 20. 制約と非対応

- 「未確認」と書いた項目は、公式資料で確認できていません。次の項目が該当します。
  - ChatGPT Work(ヘルプセンターを取得できませんでした)
  - Gemini Apps の `scripts/` の扱いと、ZIP の可否
  - Copilot のプラン条件
  - Antigravity の `~/.agents/skills`
- Claude のヘルプ記事は `description` を200字以内としていますが、Agent Skills の仕様は1024字です。この Skill は200字以内なので、どちらにも収まります。
- Claude Code は `.agents/skills/` を読みません。`.claude/skills/` へ別に配置します。
- Codex の `$CODEX_HOME/skills` は使いません。
- 計測は、日本語の文章を対象にしたヒューリスティックです。文の区切りは、句点、感嘆符、疑問符と、括弧や引用の対応から推定します。Markdown の解析は簡易で、入れ子の引用、インデントされたコードブロック、HTML の複雑な構造は正確に扱えません。
- Skill は文章の意味を検証しません。意味の保存を保証するのは、Agent の判断と、利用者の確認です。
- 各製品の仕様は、確認日(2026-09-29)以降に変わる可能性があります。

## 参照した公式資料

- [Agent Skills specification](https://agentskills.io/specification)
- [Codex / ChatGPT: Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code: Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Claude: Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Claude Help Center: How to create custom skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)
- [GitHub Docs: About agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- [GitHub Docs: Custom instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)
- [Gemini CLI: Agent Skills](https://geminicli.com/docs/cli/skills/)
- [Antigravity: Agent Skills](https://antigravity.google/docs/skills)
- [Gemini Apps Help: The transition from Gems to skills](https://support.google.com/gemini/answer/18560919?hl=en)
