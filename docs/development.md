# 開発

このリポジトリを変更する人向けの説明です。

## ディレクトリ構成

```text
japanese-readability-editor/
├── README.md
├── skill/japanese-readability-editor/     # 正本。配布するのはここだけ
│   ├── SKILL.md
│   ├── references/readability-rules.md
│   ├── references/kokugo-policy.md        # 国語の表記・用法の適用方針
│   ├── references/kokugo-notation.md      # 規則の一覧と出典(規則データから生成)
│   ├── references/kokugo-official.md      # official の運用
│   ├── references/kokugo-sources.md       # 公式資料の記録(資料データから生成)
│   ├── scripts/measure.py
│   ├── scripts/verify_preservation.py
│   ├── scripts/compare_rewrite.py
│   ├── scripts/check_kokugo.py
│   ├── scripts/kokugo_engine.py
│   ├── scripts/validate_kokugo_rules.py
│   ├── data/kokugo-rules.json             # 規則(出典・適用条件・例)
│   ├── data/kokugo-sources.json           # 資料の記録(日付・URL・確認日・SHA-256)
│   ├── data/joyo-kanji.json               # 常用漢字表の字種と音訓(派生データ)
│   ├── data/ijidokun.json                 # 異字同訓の133項目(派生データ)
│   ├── assets/examples.md
│   └── assets/kokugo-cases.md
├── tools/
│   ├── install.py
│   ├── uninstall.py
│   ├── package.py
│   ├── validate_skill.py
│   ├── update_kokugo_sources.py           # 公式資料の照合・抽出(ネットワークを使う唯一のコード)
│   ├── render_kokugo_docs.py              # 規則データから、規則の一覧と出典の文書を生成
│   └── check_all.py                       # 検証とテストをまとめて実行
├── tests/
├── docs/                                  # 詳しい説明と実測の記録
├── .claude-plugin/                        # Claude Code プラグインの定義(正本を指すだけ)
├── .github/workflows/                     # CI と Release
├── LICENSE                                # MIT
└── dist/                                  # 生成物。Git には含めない
```

## 各ファイルの責務

| ファイル | 責務 |
|---|---|
| `SKILL.md` | 頻繁に使う判断とワークフロー。3つのモードとその指定、診断の順序、変更してはならないもの |
| `references/readability-rules.md` | 各診断段階の詳しい基準と、モードの指定が食い違うときの扱い。Agent が迷ったときだけ読む |
| `assets/examples.md` | 修正前後の例。必要なときだけ読む |
| `scripts/measure.py` | 段落・文の長さなどの計測、修正候補の位置の表示、`--extras` の指摘(読み取り専用) |
| `scripts/verify_preservation.py` | 空白以外の文字列が同一かの検査。`--strict` は、改行以外の全文字が同一で改行が減っていないことまで検査する(読み取り専用) |
| `scripts/compare_rewrite.py` | 書き換えの前後の比較。意味が変わったかもしれない箇所を挙げる(読み取り専用。SudachiPy が入っていれば使う) |
| `references/kokugo-*.md` | 国語の表記・用法の適用方針、規則の一覧、公用文の運用、出典。Agent が必要なときだけ読む。詳細は [国語の表記・用法の検査](kokugo.md) |
| `data/*.json` | 国語の規則、資料の記録、常用漢字表、異字同訓。`scripts/check_kokugo.py` と `scripts/validate_kokugo_rules.py` が読む |
| `scripts/check_kokugo.py` | 国語の表記・用法の規則で文章を検査する。区分、位置、理由、候補、出典 ID を出す(読み取り専用、ネットワークなし) |
| `scripts/kokugo_engine.py` | 検査エンジン(保護対象の判定、検出、区分の決定)。単独では実行しない |
| `scripts/validate_kokugo_rules.py` | 規則データの検証(読み取り専用) |
| `assets/kokugo-cases.md` | 国語の表記の修正例と、変更してはいけない反例 |
| `tools/install.py` | 各環境の配置先へコピーまたはリンクする |
| `tools/uninstall.py` | `install.py` で配置したものを、配置先から削除する。配置先の決め方は `install.py` と共有する |
| `tools/package.py` | ZIP、SHA-256、Gemini Apps 向けの出力を生成する |
| `tools/validate_skill.py` | Skill の構造と互換性を検証する |
| `tools/update_kokugo_sources.py` | 公式資料を取得して SHA-256 を照合する(`verify`)。PDF から常用漢字表と異字同訓のデータを作る(`extract-*`)。Skill の外にあり、配布物には入らない |
| `tools/render_kokugo_docs.py` | `references/kokugo-notation.md`(規則の一覧)と `references/kokugo-sources.md`(出典)を、規則データから生成する。`--check` で最新かを確かめる。この2つの文書は手で書き換えない |
| `tools/check_all.py` | Skill の検証、規則データの検証、生成した文書の最新確認、全テストをまとめて実行する |
| `.claude-plugin/` | Claude Code のプラグインとして入れるための定義。`skill/` を指すだけで、Skill は複製しない |
| `.github/workflows/` | CI(検証、テスト、パッケージ生成)と、タグを push したときの Release |

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
└── gemini-apps/japanese-readability-editor/ # Gemini Apps の Skills 用(scripts/ なし)
```

ZIP の最上位は `japanese-readability-editor/` の1フォルダです。その直下に、`SKILL.md`、`references/`、`scripts/`、`data/`、`assets/` が入ります。Gemini Apps 向けのフォルダは、実行できない `scripts/` と、その入力にしか使わない `data/` を含めません。ZIP のルートへ直接 `SKILL.md` を置く構造ではありません。

ZIP は再現可能で、同じ入力からは同じ SHA-256 になります。`--no-gemini-apps` で、Gemini Apps 向けの出力を省けます。

`v` で始まるタグを GitHub に push すると、Actions が Release を作ります(`.github/workflows/release.yml`)。Release には、ZIP、SHA-256、Gemini Apps 向けの指示文が添付されます。Release は、[Releases のページ](https://github.com/Mr-Kondo/japanese-readability-editor/releases)で公開されます。リポジトリを取得せずに、ZIP を入手できます。

## 検証

```bash
python3 tools/validate_skill.py
python3 skill/japanese-readability-editor/scripts/validate_kokugo_rules.py
python3 tools/check_all.py
```

`tools/check_all.py` は、Skill の検証、国語の規則データの検証、生成した文書の最新確認、全テストを順に実行します。ネットワークは使いません。規則データ(`data/kokugo-rules.json`、`data/kokugo-sources.json`)を変えたら、`python3 tools/render_kokugo_docs.py` で `references/kokugo-notation.md` と `references/kokugo-sources.md` を作り直します。

次を確認し、エラーがあれば終了コード 1 を返します。

- `SKILL.md` が、大文字小文字まで正確な名前で存在する
- frontmatter が先頭にあり、`name`(`japanese-readability-editor`)と `description` がある
- `name` がディレクトリ名と一致する
- 製品固有の frontmatter がない(`name` と `description` 以外は誤りとして扱う)
- 参照する `references/`、`scripts/`、`assets/` のファイルが存在する
- skill の外を指す `../` や絶対パスがない
- `scripts/` の Python が、通信、外部コマンドの実行、ファイルの削除と書き込みをしない(`check_kokugo.py` などの国語の検査も同じ)
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
- モード C の厳密な確認と、モード B の意味保存の回帰(`test_kokugo_modes.py`)
- `assets/kokugo-cases.md` の例と、実際の検査結果の一致(`test_kokugo_cases.py`)
- `validate_skill.py`、`install.py`、`uninstall.py`、`package.py`
- `SKILL.md` の `description`(要件で挙げたトリガー語と、除外する入力を含むか、200字以内か)
- `SKILL.md` と references の、意味を保つための指示と、モードの指定の指示が消えていないか。`SKILL.md` が150行以内か
- `.claude-plugin/` の定義(正本を指し、Skill を複製していないか)

CI は `.github/workflows/ci.yml` にあります。Ubuntu、macOS、Windows で、Skill の検証、国語の規則データの検証、テスト、パッケージ生成を実行します。

Ubuntu では、Python 3.10 と最新版で試し、2つのジョブでは SudachiPy を入れて試します。辞書は、一方が core、もう一方が small です。`compare_rewrite.py` の SudachiPy を使うテストは、SudachiPy が入っている環境だけで実行します。
