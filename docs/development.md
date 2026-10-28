# 開発

このリポジトリを変更する人向けの説明です。

評価用のツールと画面テンプレートは、配布スキルの外に置いています。

| 文書 | 内容 |
|---|---|
| [文章評価ツール](human-evaluation.md) | 定量・定性評価、自動／手動検証、モードBの匿名二候補比較。`tools/review_readability.py`、`compare_readability.py`、`comprehension_readability.py`、`statistics_readability.py`、`feedback_readability.py` |
| [公開文書による評価データ整備の計画](public-document-evaluation.md) | 出典・利用条件・分割の台帳を検査する `tools/validate_public_corpus.py`。文書群ごとの手順は `public-documents-*.md` |
| [Ragas による自動評価](ragas-evaluation.md) | 任意依存の自動評価 `tools/ragas_readability.py` |
| [評価ケースと記録](../evals/README.md) | モデルを使う評価の入力と結果。`tools/evaluate_readability.py` が使う |
| [利用者のフィードバック](feedback.md)、[参考にしたリポジトリの更新確認](upstream-watch.md) | `tools/feedback_loop.py`、`tools/upstream_watch.py` の手順と限界 |

## ディレクトリ構成

```text
japanese-readability-editor/
├── README.md
├── skills/japanese-readability-editor/     # 正本。配布するのはここだけ
│   ├── SKILL.md
│   ├── references/                         # readability-rules.md、scripts.md、kokugo-check.md、fiction-*.md、kokugo-*.md、feedback.md
│   ├── scripts/                            # measure.py、verify_preservation.py、compare_rewrite.py、check_kokugo.py ほか
│   ├── data/                               # 国語の規則、資料の記録、常用漢字表、異字同訓
│   └── assets/                             # examples.md、kokugo-cases.md、fiction-*.md
├── tools/                                  # 配布物の生成、検証、評価、更新確認(Skill の外。配布物には入らない)
├── tests/
├── evals/                                  # モデルを使う評価の入力と結果
├── docs/                                   # 詳しい説明と実測の記録
├── reports/、research_notes/               # 設計時の調査の記録(2026-10-16。リンクは当時の絶対パスのまま)
├── .claude-plugin/                         # Claude Code プラグインの定義(正本を指すだけ)
├── .github/workflows/                      # CI、Release、参考先の更新確認(週1回)
├── LICENSE                                 # MIT
└── dist/                                   # 生成物。Git には含めない
```

## 各ファイルの責務

| ファイル | 責務 |
|---|---|
| `SKILL.md` | 頻繁に使う判断とワークフロー。4つのモード(A〜D)とその指定、診断の順序、変更してはならないもの |
| `references/scripts.md`、`references/kokugo-check.md` | 全モードでは使わない手順を、本文から出したもの。スクリプトの一覧と用法、国語の表記・用法の適用手順。C の手順は、参照にすると C のたびに読み込みの1ターンが増えて損だったので、本文に残した(計測: [docs/validation/skill-token-usage-2026-10-19.md](validation/skill-token-usage-2026-10-19.md))。Skill 読み込み時の入力トークンを減らすために分けた。100行を超える参照には目次を付ける(`tests/test_skill_guards.py`) |
| `references/readability-rules.md` | 各診断段階の詳しい基準と、モードの指定が食い違うときの扱い。Agent が迷ったときだけ読む |
| `assets/examples.md` | 修正前後の例。必要なときだけ読む |
| `references/fiction-writing.md`、`references/fiction-checks.md`、`assets/fiction-*.md` | モード D の操作契約、補助検査の仕様、修正例、任意の文脈メモ。[小説モードの正本と評価](#小説モードの正本と評価) |
| `references/feedback.md` | 利用者が問題の報告を求めたときだけ読む手順 |
| `scripts/check_fiction.py` | 小説向けの字数、括弧、指定文字列の検査(読み取り専用) |
| `scripts/measure.py` | 段落・文の長さなどの計測、修正候補の位置の表示、`--extras` の指摘(読み取り専用) |
| `scripts/verify_preservation.py` | 空白以外の文字列が同一かの検査。`--strict` は、改行以外の全文字が同一で改行が減っていないことまで検査する(読み取り専用) |
| `scripts/compare_rewrite.py` | 書き換えの前後の比較。意味が変わったかもしれない箇所を挙げる(読み取り専用。SudachiPy が入っていれば使う) |
| `VERSION` | Skill の版。この値が変わった main への push で、`release.yml` がタグ(`v` + この値)と Release を作る。`tests/test_skill_info.py` が、同じ版のリリースノートがあることを確かめる |
| `scripts/skill_info.py` | 版と実行環境(OS・アプリ・モデル・日付)の JSON を標準出力に出す(読み取り専用)。保存先は `~/.agents/skill-env/<スキル名>.json` で、保存は実行した側 |
| `scripts/make_feedback.py` | 結果の問題を報告する票(JSON)を自動保存し、標準出力にも出す(通信なし)。[利用者のフィードバック](feedback.md) |
| `scripts/make_change_report.py` | 書き換えの前後の変化を、本文を含まない選択式の記録(JSON)として自動保存し、標準出力にも出す(通信なし)。[変化の記録](feedback.md#使った後の変化を記録する) |
| `references/kokugo-*.md` | 国語の表記・用法の適用方針、規則の一覧、公用文の運用、出典。Agent が必要なときだけ読む。詳細は [国語の表記・用法の検査](kokugo.md) |
| `data/*.json` | 国語の規則、資料の記録、常用漢字表、異字同訓。`scripts/check_kokugo.py` と `scripts/validate_kokugo_rules.py` が読む |
| `scripts/check_kokugo.py` | 国語の表記・用法の規則で文章を検査する。区分、位置、理由、候補、出典 ID を出す(読み取り専用、ネットワークなし) |
| `scripts/kokugo_engine.py` | 検査エンジン(保護対象の判定、検出、区分の決定)。単独では実行しない |
| `scripts/validate_kokugo_rules.py` | 規則データの検証(読み取り専用) |
| `assets/kokugo-cases.md` | 国語の表記の修正例と、変更してはいけない反例 |
| `tools/install.py` | 各環境の配置先へコピーまたはリンクする。内容が同じなら何もせず、違う既存のものは上書きしない。OpenCode と Hermes の配置先は `skill_env.py` で解決し、同名 Skill の重複を警告する |
| `tools/uninstall.py` | `install.py` で配置したものを、配置先から削除する。配置先の決め方は `install.py` と共有する |
| `tools/verify_install.py` | 配置した Skill を検証する。スクリプトを、Skill でもリポジトリでもない、空白と日本語を含むディレクトリから実行する(何も変更せず、何もインストールしない) |
| `tools/skill_env.py` | OpenCode と Hermes の配置先の解決(環境変数は引数で受ける)、同名 Skill の探索、正本との内容の比較。`install.py`、`uninstall.py`、`verify_install.py`、`package.py` が使う |
| `tools/package.py` | ZIP、SHA-256、Gemini Apps 向けの出力、OpenCode と Hermes 向けの配布物を生成する |
| `tools/validate_skill.py` | Skill の構造と互換性を検証する |
| `tools/update_kokugo_sources.py` | 公式資料を取得して SHA-256 を照合する(`verify`)。PDF から常用漢字表と異字同訓のデータを作る(`extract-*`)。Skill の外にあり、配布物には入らない |
| `tools/render_kokugo_docs.py` | `references/kokugo-notation.md`(規則の一覧)と `references/kokugo-sources.md`(出典)を、規則データから生成する。`--check` で最新かを確かめる。この2つの文書は手で書き換えない |
| `tools/feedback_loop.py` | 利用者から送付された票の受領・検証(`intake`)、独立文書数での集約と回帰ケース化(`triage`)、改良案の下書き(`propose`、既定は送信しない)、修正前後の比較(`verify`)。`skills/` は書き換えない。[利用者のフィードバック](feedback.md) |
| `tools/upstream_watch.py` | 参考にしたリポジトリの更新を調べ(`check`)、追跡 Issue を作り(`notify`)、解析を終えた基準を進める(`mark-reviewed`)、参考先を登録する(`add`)。登録簿は `docs/upstream/sources.json`。Skill の外にあり、配布物には入らない。[参考にしたリポジトリの更新確認](upstream-watch.md) |
| `tools/check_all.py` | 検証とテストをまとめて実行する。内容は「[検証](#検証)」 |
| 評価用のツール | `review_readability.py`、`compare_readability.py`、`comprehension_readability.py`、`statistics_readability.py`、`feedback_readability.py`、`evaluate_readability.py`、`ragas_readability.py`、`validate_public_corpus.py`、`measure_skill_tokens.py`(Skill を入れた隔離プロジェクトで `claude -p` を流し、トークンとスクリプトの実行を記録する。[計測の記録](validation/skill-token-usage-2026-10-19.md))、`extract_*_text.py`(と画面テンプレートの `*.html`)。文書は冒頭の表にある。Skill の外にあり、配布物には入らない |
| `.claude-plugin/` | Claude Code のプラグインとして入れるための定義。`skills/` を指すだけで、Skill は複製しない |
| `.github/workflows/` | CI(検証、テスト、パッケージ生成)、タグを push したときの Release、週に1回の参考先の更新確認(`upstream-watch.yml`。追跡 Issue を作るだけで、リポジトリは書き換えない) |

## パッケージ生成

この文書のコマンドは、`python3` で書いています。Windows では、`python` で実行する場合があります([Python のコマンド名](installation.md#python-のコマンド名))。

```bash
python3 tools/package.py
```

```text
dist/
├── japanese-readability-editor.zip          # ChatGPT Work / Claude Cowork のアップロード用
├── japanese-readability-editor.sha256
├── gemini-apps-instructions.md              # Gemini Apps の Gem / Custom Instructions 用
├── gemini-apps/japanese-readability-editor/ # Gemini Apps の Skills 用(scripts/ なし)
├── opencode/                                # OpenCode 用。japanese-readability-editor/ と INSTALL.md
└── hermes/                                  # Hermes Agent 用。japanese-readability-editor/ と INSTALL.md
```

ZIP の最上位は `japanese-readability-editor/` の1フォルダです。その直下に、`SKILL.md`、`references/`、`scripts/`、`data/`、`assets/` が入ります。Gemini Apps 向けのフォルダは、Chat向けの構成として、`scripts/`、専用入力の`data/`、実機で取り込みを拒否された`VERSION`を含めません。通常のZIPと他環境の配布物には`VERSION`を残します。これはGemini Apps全体でスクリプトを実行できないという意味ではありません。通常のZIPはルートへ直接 `SKILL.md` を置く構造ではありません。

ZIP は再現可能で、同じ入力からは同じ SHA-256 になります。`--no-gemini-apps` で、Gemini Apps 向けの出力を省けます。

`dist/opencode/` と `dist/hermes/` の `japanese-readability-editor/` は、正本の完全な複製です。環境ごとに変えるのは、配置先とコマンドを書いた `INSTALL.md` だけで、Skill の本文は複製しません。生成のたびに、`verify_install.py` と同じ検証(正本との一致を含む)を行い、失敗すると終了コード 1 です。`--bundle opencode` のように対象を選べ、`--no-agent-bundles` で省けます。

main の `skills/japanese-readability-editor/VERSION` が変わると、Actions が、その版のタグ(`v` + VERSION)と Release を作ります(`.github/workflows/release.yml`)。同じ版の Release が既にあれば、何もしません。版を上げる PR をマージするだけでリリースされます。失敗したときは、Actions の画面から手動で再実行できます。`docs/release-notes/v<版>.md` があれば、それが Release のノートになります。なければ自動生成です。Release は、[Releases のページ](https://github.com/Mr-Kondo/japanese-readability-editor/releases)で公開されます。添付されるものと、ダウンロードの方法は、[インストール](installation.md#アップロード型の環境に入れる)にあります。

## 一般文書 A/B のモデル評価

改良中に懸念が見つかったら、固有情報を除いてIssueにし、根拠・解消条件・確認方法を記録します。同じ懸念は既存Issueへ追記します。今回の対象Issueを明示し、既存の別案件と混同しません。

対象の懸念が解消するまで、検討・最小の修正・再検証を繰り返します。追加の懸念もIssueで追跡し、未確認と書くだけで完了扱いにはしません。修正不要と判断する場合も根拠を残します。

実行失敗や欠測を成功へ置き換えず、モデルや条件を変える場合は旧新版を同じ条件へそろえます。対象Issueの解消条件と結果を確認してからマージ・リリースし、公開物の確認と作業ブランチ・一時物の後片付けまで終えます。

構造を直す手順と文の働きの保持は、[比較評価の手順](../evals/readability-comparison.md)と[自作ケース](../evals/readability-cases.json)で確認します。変更前後で生成条件を固定し、意味保持の成否と、両方が意味を保った場合の読みやすさを分けて採点します。例集・指示の文言検査や単体テストの成功だけでは、モデル出力の改善を確認したことにはなりません。評価資料は配布スキルの必須依存にしません。

未使用文書での追加確認は [評価手順](../evals/readability-generalization.md)と `tools/evaluate_readability.py` を使います。既定は外部通信のない準備だけで、`--execute`を付けた場合だけ既存認証のClaude CLIを呼びます。単体テストではプロセス実行の境界を差し替え、モデル呼び出しは行いません。出力欠落、採点点検の誤答、実行失敗を成功へ置き換えないことを検査します。

## 小説モードの正本と評価

D の正本は共通 `SKILL.md` と `references/fiction-writing.md`、`references/fiction-checks.md`、`assets/fiction-examples.md`、任意の `assets/fiction-context-template.md`、読み取り専用 `scripts/check_fiction.py` です。詳細を参照へ分け、製品固有 API を必須依存にしません。文化庁の規則データと既存 CLI の既定値は変更しません。

`evals/fiction-cases.json` はモデル挙動の評価入力と観点です。構造テスト・キーワード検査だけではモデルの実行証拠になりません。[評価手順と実施範囲](../evals/README.md)、[設計参考・採否・限界](fiction-design.md)を参照してください。

配布 ZIP と OpenCode/Hermes 向けフォルダは追加ファイルも正本から複製します。Gemini Apps のフォルダは従来どおり scripts/data を除き、貼付用指示にも D の契約を埋め込みます。新規 evals は開発資料なので Skill の必須依存にはしません。

## 検証

```bash
python3 tools/validate_skill.py
python3 skills/japanese-readability-editor/scripts/validate_kokugo_rules.py
python3 tools/check_all.py
```

`tools/check_all.py` は、Skill の検証、国語の規則データの検証、生成した文書の最新確認、全テストを順に実行します。1つでも失敗すれば終了コード 1 です。ネットワークは使いません。規則データ(`data/kokugo-rules.json`、`data/kokugo-sources.json`)を変えたら、`python3 tools/render_kokugo_docs.py` で `references/kokugo-notation.md` と `references/kokugo-sources.md` を作り直します。

次を確認し、エラーがあれば終了コード 1 を返します。

- `SKILL.md` が、大文字小文字まで正確な名前で存在する
- frontmatter が先頭にあり、`name`(`japanese-readability-editor`)と `description` がある
- `name` がディレクトリ名と一致する
- 製品固有の frontmatter がない(`name` と `description` 以外は誤りとして扱う)
- 参照する `references/`、`scripts/`、`assets/` のファイルが存在する
- skill の外を指す `../` や絶対パスがない
- `scripts/` の Python が、通信、外部コマンドの実行、ファイルの削除と書き込みをしない(`feedback_storage.py` の保存用フォルダ作成と、保存失敗時の未完成ファイル削除だけを例外とする。国語の検査などは読み取り専用)
- ZIP にできる

frontmatter は、どのエージェントの解析器でも読める、保守的な YAML の部分集合に限ります。値は1行で書き、値の中の `: ` と ` #` は避けます。

## テスト

```bash
python3 -m unittest discover -s tests -v
```

標準ライブラリの `unittest` だけを使います。対象は、次のとおりです。

- `measure.py`、`verify_preservation.py`(`--strict` を含む)、`compare_rewrite.py`
- `check_kokugo.py` と `kokugo_engine.py`(一次資料の例示・許容・適用範囲から決めた期待値、適用設定ごとの区分、`needs_context`、用語集、保護対象、再現性、JSON の形式、終了コード、入力が変わらないこと、ネットワークなしで動くこと)
- `validate_kokugo_rules.py` と規則データ(不正なデータの検出、出典の記録、文書との整合)
- `tools/update_kokugo_sources.py`(取得は差し替える。通信しない)と `tools/check_all.py`
- `tools/upstream_watch.py`(gh の応答を差し替える。通信しない)と、登録簿 `docs/upstream/sources.json` の整合(確認の記録の実在、ライセンスの条件)、`upstream-watch.yml` の権限
- モード C の厳密な確認と、モード B の意味保存の回帰(`test_kokugo_modes.py`)
- `assets/kokugo-cases.md` の例と、実際の検査結果の一致(`test_kokugo_cases.py`)
- `validate_skill.py`、`install.py`、`uninstall.py`、`package.py`
- `skill_env.py`(OpenCode と Hermes の配置先の解決、プロファイルと `active_profile`、`config.yaml` の読み取り、同名 Skill の探索、内容の比較)と、`install.py` の OpenCode と Hermes の対応(冪等性、内容が違う既存のものの保護、`--dest`、空白と日本語を含むパス、環境変数と `--home`)
- `verify_install.py`(壊れた配置の検出、対象の環境ごとのメタデータ、リポジトリの外からのスクリプトの実行)と、配置した複製が正本と同じ出力を返すこと
- `compare_rewrite.py` の SudachiPy がない経路と、`tokenizer` の表示(`test_tokenizer_modes.py`。SudachiPy が入っている環境でも、import を塞いだ別プロセスで試す)
- `SKILL.md` の `description`(要件で挙げたトリガー語と、除外する入力を含むか、200字以内か)
- `SKILL.md` の行数が、`tests/test_skill_guards.py` の `MAX_SKILL_LINES` 以内か、参照先の節が残っているか(指示の文言そのものは、テストで固定せず、evals で測る)
- `.claude-plugin/` の定義(正本を指し、Skill を複製していないか)
- `check_fiction.py`、`make_feedback.py`、`feedback_loop.py`と、評価用のツール(`review_readability.py` ほか。通信せず、モデルの呼び出しは差し替える)
- 各スクリプトの標準出力が UTF-8 であること(`test_stdio_utf8.py`)

CI は `.github/workflows/ci.yml` にあります。Ubuntu、macOS、Windows で、Skill の検証、国語の規則データの検証、テスト、パッケージ生成を実行します。

Ubuntu では、Python 3.10 と最新版で試し、2つのジョブでは SudachiPy を入れて試します。辞書は、一方が core、もう一方が small です。`compare_rewrite.py` の SudachiPy を使うテストは、SudachiPy が入っている環境だけで実行します。

テストは、利用者の Python 環境に何も入れません。SudachiPy がない経路は、入っていない仮想環境、または import を塞いだ別プロセスで試します。ある経路は、SudachiPy が入っている環境で実行します。OpenCode と Hermes の配置先のテストは、一時ディレクトリの `--home`、または一時ディレクトリを指す `HOME` だけを使います。利用者の `HERMES_HOME` などの環境変数が混ざらないよう、子プロセスから外しています。
