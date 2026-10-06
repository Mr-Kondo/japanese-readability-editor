# 開発

## ディレクトリ構成

```text
japanese-readability-editor/
├── README.md
├── skill/japanese-readability-editor/     # 正本。配布するのはここだけ
│   ├── SKILL.md
│   ├── references/readability-rules.md
│   ├── scripts/measure.py
│   ├── scripts/verify_preservation.py
│   ├── scripts/compare_rewrite.py
│   └── assets/examples.md
├── tools/
│   ├── install.py
│   ├── package.py
│   └── validate_skill.py
├── tests/
├── docs/                                  # 実測の記録など、README から分けた資料
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
| `scripts/verify_preservation.py` | 空白以外の文字列が同一かの検査(読み取り専用) |
| `scripts/compare_rewrite.py` | 書き換えの前後の比較。意味が変わったかもしれない箇所を挙げる(読み取り専用。SudachiPy が入っていれば使う) |
| `tools/install.py` | 各環境の配置先へコピーまたはリンクする |
| `tools/package.py` | ZIP、SHA-256、Gemini Apps 向けの出力を生成する |
| `tools/validate_skill.py` | Skill の構造と互換性を検証する |
| `.claude-plugin/` | Claude Code のプラグインとして入れるための定義。`skill/` を指すだけで、Skill は複製しない |
| `.github/workflows/` | CI(検証、テスト、パッケージ生成)と、タグを push したときの Release |

## パッケージ生成

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

## 検証

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

## テスト

```bash
python3 -m unittest discover -s tests -v
```

標準ライブラリの `unittest` だけを使います。対象は、次のとおりです。

- `measure.py`、`verify_preservation.py`、`compare_rewrite.py`
- `validate_skill.py`、`install.py`、`package.py`
- `SKILL.md` の `description`(要件で挙げたトリガー語と、除外する入力を含むか、200字以内か)
- `SKILL.md` と references の、意味を保つための指示と、モードの指定の指示が消えていないか。`SKILL.md` が150行以内か
- `.claude-plugin/` の定義(正本を指し、Skill を複製していないか)

CI は `.github/workflows/ci.yml` にあります。Ubuntu、macOS、Windows で、検証、テスト、パッケージ生成を実行します。

Ubuntu では、Python 3.10 と最新版で試し、2つのジョブでは SudachiPy を入れて試します。辞書は、一方が core、もう一方が small です。`compare_rewrite.py` の SudachiPy を使うテストは、SudachiPy が入っている環境だけで実行します。
