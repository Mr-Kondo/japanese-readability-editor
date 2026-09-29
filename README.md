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
- 書き換えた後は、元の文と突き合わせます。数値、条件の範囲、否定の数、主体、文体が同じかを確かめ、違う箇所は元に戻します。
- 二重否定や「それ以外の場合」のような残余の条件は、原則として触りません。意味が変わりやすいためです。
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
├── .claude-plugin/                        # Claude Code プラグインの定義(正本を指すだけ)
├── .github/workflows/                     # CI と Release
├── LICENSE                                # MIT
└── dist/                                  # 生成物。Git には含めない
```

## 4. 各ファイルの責務

| ファイル | 責務 |
|---|---|
| `SKILL.md` | 頻繁に使う判断とワークフロー。3つのモード、診断の順序、変更してはならないもの |
| `references/readability-rules.md` | 各診断段階の詳しい基準。Agent が迷ったときだけ読む |
| `assets/examples.md` | 修正前後の例。必要なときだけ読む |
| `scripts/measure.py` | 段落・文の長さなどの計測、修正候補の位置の表示、`--extras` の指摘(読み取り専用) |
| `scripts/verify_preservation.py` | 空白以外の文字列が同一かの検査(読み取り専用) |
| `tools/install.py` | 各環境の配置先へコピーまたはリンクする |
| `tools/package.py` | ZIP、SHA-256、Gemini Apps 向けの出力を生成する |
| `tools/validate_skill.py` | Skill の構造と互換性を検証する |
| `.claude-plugin/` | Claude Code のプラグインとして入れるための定義。`skill/` を指すだけで、Skill は複製しない |
| `.github/workflows/` | CI(検証、テスト、パッケージ生成)と、タグを push したときの Release |

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

アップロード型の環境では、新しい ZIP を、もう一度アップロードします。ZIP は、Release からダウンロードするか、`python3 tools/package.py` で作ります。

ChatGPT では、同じ名前の Skill があると、置き換えの確認(Skill already exists)が出ます。「Replace existing」を選ぶと、同じ Skill が更新されます。重複はしません。

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
python3 scripts/measure.py --locate --extras README.md
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

`--extras` を付けると、長さとは別に、読み流すと見落としやすい3種類の箇所を、指摘として挙げます。

- 漢字が7字以上続く箇所(その場で作られた圧縮漢語など)
- 名詞と「の」が3回以上つながる箇所
- 「ないわけではない」のような二重否定

これらは判定ではなく、直すかどうかは読んで決めます。「〜ないと動かない」(必要条件)や「〜なければならない」(義務)は、二重否定として拾いません。

`verify_preservation.py` は、空白を除いた文字列が一致すれば終了コード 0、しなければ 1 を返します(読み込みに失敗すると 2)。

> **注意**: このスクリプトが保証するのは「空白以外の文字列が変更されていないこと」だけです。意味の保存は保証しません。英単語の間の空白など、空白が意味を持つ箇所の変更も検出できません。

## 環境別の対応表

`Native Agent Skill` は、その環境が Agent Skills 形式(`SKILL.md` を含むフォルダ)を直接扱えるかを表します。

| Environment | Native Agent Skill | Workspace path | User/global path | ZIP upload | Notes |
|---|---|---|---|---|---|
| ChatGPT Work | あり。Plus プランのアカウントで、アップロードと呼び出しを確認した(2026-09-29)※1 | 未確認 | 未確認 | 可。Plugins → Skills → Add → Upload from your computer。ZIP を取り込めた | `@skill-name` で呼べる(確認済み)。取り込み時に、ChatGPT が `agents/openai.yaml` を自動生成する ※1 |
| Codex | あり | `.agents/skills/`(カレントから repo root まで探索) | `$HOME/.agents/skills/` | 不要 | `$CODEX_HOME/skills` は旧仕様。管理者向けに `/etc/codex/skills` もある。変更は自動検出、出なければ再起動。symlink 可 |
| Claude Cowork | あり | 非対応(アップロード方式) | 非対応 | 可。Customize → Skills。ZIP の最上位にフォルダ | コード実行の有効化が必要。プランの記載は公式ページ間で異なる。`description` に200字の上限があるという記載あり |
| Claude Code | あり | `.claude/skills/` | `~/.claude/skills/` | 不要 | `.agents/skills` は読まない。未知の frontmatter は無視される。symlink 可 |
| GitHub Copilot | あり(cloud agent、code review、CLI、app、VS Code / JetBrains の agent mode) | `.agents/skills/`、`.github/skills/`、`.claude/skills/` | `~/.agents/skills/`、`~/.copilot/skills/` | 不要 | 利用できるプランは未確認 |
| Gemini Apps | あり(Skills。Gems は 2026-11 以降 Skills へ移行) | 非対応 | 非対応(アカウントに保存) | `SKILL.md` またはフォルダをアップロード。ZIP の可否は未確認 | `scripts/` の扱いは未確認。生成物は 11 節 |
| Gemini CLI | あり | `.agents/skills/`、`.gemini/skills/` | `~/.agents/skills/`、`~/.gemini/skills/` | 不要 | 同じ階層では `.agents/skills` が優先。`/skills list` で確認 |
| Antigravity IDE | あり | `.agents/skills/`(旧 `.agent/skills/` も互換) | `~/.gemini/config/skills/`(旧 `~/.gemini/antigravity/skills/`) | 不要 | `/<skill-name>` で呼べる |
| Antigravity CLI | あり | `.agents/skills/` | `~/.gemini/antigravity-cli/skills/` | 不要 | `~/.agents/skills` は自動では読まれないとする記述あり(Codelab)。未確認 |

※1 2026-09-29 に、Plus プランのアカウントで、実際に確認しました。

二次資料では、対象は Business / Enterprise / Healthcare / Edu とされていました。Free / Plus / Pro は対象外という記述もありました。今回の確認とは一致しません。

OpenAI ヘルプセンターの記事は、自動取得できませんでした。提供状況は、プラン、workspace の設定、リリース状況によって変わります。管理者による有効化が必要な場合もあります。利用前に、各自の画面で確認してください。

## 6. ChatGPT Work

ChatGPT のワークスペースに Skill をアップロードする方式です。`dist/japanese-readability-editor.zip` を使います。

1. ZIP を用意します。最新の Release からダウンロードするか、`python3 tools/package.py` で作ります。
2. ChatGPT の Plugins → Skills を開き、Add → Upload from your computer で、ZIP を選びます。

アップロードできるのは、`.zip`、`.skill`、`SKILL.md` で、最大サイズは1ファイルあたり25MBです。

Plus プランのアカウントで、次を確認しました(2026-09-29)。

- ZIP を取り込めた。`name` と `description` は、全文が保たれた。
- `@japanese-readability-editor` で呼び出せた。
- ChatGPT が `agents/openai.yaml` を自動生成した。`allow_implicit_invocation` が `true` なので、依頼内容に合えば自動でも使われる。
- 取り込み直後の `openai.yaml` は、`assets/icon.svg` を参照していたが、ZIP には含まれず、アイコンが壊れた画像として表示された。
- その後、ChatGPT が `assets/icon.svg` を追加し、`openai.yaml` の短い説明文を書き換え、アイコンが表示されるようになった。`SKILL.md` の `name` と `description` は変わらなかった。

Skill 機能がプラン、workspace の設定、管理者の許可に依存する点に注意してください。Enterprise と Edu では、管理者が有効化するまで表示されない場合があります。アップロード画面の名称と手順は、変わる可能性があります。

書き換えの結果は、モデルの出力です。返ってきた文章は、元の文と突き合わせて確認してください。

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

1. ZIP を用意します。最新の Release からダウンロードするか、`python3 tools/package.py` で作ります。
2. Customize → Skills から、`dist/japanese-readability-editor.zip` を追加します。

ZIP は、Skill のフォルダが最上位にある構造です。コード実行の有効化が必要です。Claude Code の `~/.claude/skills/` は、Cowork のセッションでは読み込まれません。

この Skill の `description` は、Claude のヘルプ記事にある「200字以内」の記載に合わせて、200字以内に収めています。Agent Skills の仕様と Claude API の文書は、1024字までを許しています。

## 9. Claude Code

```bash
python3 tools/install.py --scope workspace --target claude-code   # <project>/.claude/skills/
python3 tools/install.py --scope user --target claude-code        # ~/.claude/skills/
```

Claude Code は `.agents/skills/` を読みません。Codex などと同じプロジェクトで使う場合は、`--target all` で両方に配置します。複製を避けたい場合は、`--link` でシンボリックリンクを作れます。

### プラグインとして入れる

Claude Code のプラグインとしても、入れられます。

```text
/plugin marketplace add Mr-Kondo/japanese-readability-editor
/plugin install japanese-readability-editor@japanese-readability-editor
```

プラグインの Skill は、プラグイン名を前に付けて呼びます。たとえば、`/japanese-readability-editor:japanese-readability-editor` です。

定義ファイル(`.claude-plugin/`)は、`skill/` を指すだけです。Skill は複製していません。`version` を設定していないので、更新はコミットに追従します。

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

`v` で始まるタグを GitHub に push すると、Actions が Release を作ります(`.github/workflows/release.yml`)。Release には、ZIP、SHA-256、Gemini Apps 向けの指示文が添付されます。Release は、[Releases のページ](https://github.com/Mr-Kondo/japanese-readability-editor/releases)で公開されます。リポジトリを取得せずに、ZIP を入手できます。

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

標準ライブラリの `unittest` だけを使います。対象は、次のとおりです。

- `measure.py`、`verify_preservation.py`
- `validate_skill.py`、`install.py`、`package.py`
- `SKILL.md` の `description`(要件で挙げたトリガー語と、除外する入力を含むか、200字以内か)
- `.claude-plugin/` の定義(正本を指し、Skill を複製していないか)

CI は `.github/workflows/ci.yml` にあります。Ubuntu、macOS、Windows で、検証、テスト、パッケージ生成を実行します。

## 20. 制約と非対応

- 「未確認」と書いた項目は、公式資料で確認できていません。次の項目が該当します。
  - ChatGPT Work のプラン条件と、管理者の設定(Plus プランでの動作は確認済み)
  - Gemini Apps の `scripts/` の扱いと、ZIP の可否
  - Copilot のプラン条件
  - Antigravity の `~/.agents/skills`
- Claude のヘルプ記事は `description` を200字以内としていますが、Agent Skills の仕様は1024字です。この Skill は200字以内なので、どちらにも収まります。
- Claude Code は `.agents/skills/` を読みません。`.claude/skills/` へ別に配置します。
- Codex の `$CODEX_HOME/skills` は使いません。
- 計測は、日本語の文章を対象にしたヒューリスティックです。文の区切りは、句点、感嘆符、疑問符と、括弧や引用の対応から推定します。Markdown の解析は簡易で、入れ子の引用、インデントされたコードブロック、HTML の複雑な構造は正確に扱えません。
- `--extras` は正規表現による指摘で、形態素解析を使いません。漢字の連続は、固有名詞や法令用語も拾います。「の」の連鎖は、漢字とカタカナの名詞に限ります。
- Claude Code のプラグイン定義は、`claude plugin validate` で検証しました。`/plugin install` の実際の操作は、検証していません。
- Skill は文章の意味を検証しません。意味の保存を保証するのは、Agent の判断と、利用者の確認です。
- ChatGPT での実機確認では、二重否定の意味の反転、残余の条件の言い換え、文体の変更が起きました。`SKILL.md` に対策を入れましたが、誤りを完全には防げません。
- 各製品の仕様は、確認日(2026-09-29)以降に変わる可能性があります。

## 参考にしたプロジェクト

[coji/natural-japanese](https://github.com/coji/natural-japanese)(MIT)を参考に、次の点を取り入れました。文章は転載せず、原則として再構成しています。

- 語順、読点、接続詞の射程、否定の入れ子、列挙の埋没、語形の重さの整理
- 実文書での閾値の校正結果と、「指摘は起点であり命令ではない」という運用
- 中間ファイルを、利用者のプロジェクトに残さない運用
- `--extras` の3種類の指摘
- Claude Code プラグインとしての配布、CI、Release

同リポジトリは、形態素解析、AI臭さのスコア、文体の型、サブエージェントによる推敲も持ちます。このリポジトリは、標準ライブラリだけで動くことと、環境に依存しない単一の `SKILL.md` を優先して、これらは取り入れていません。

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
