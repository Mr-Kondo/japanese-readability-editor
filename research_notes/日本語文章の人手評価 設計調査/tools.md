# 人手評価ツールのライブラリ・運用方式・支援スキル調査

調査日: 2026-10-16。公式ドキュメント、公式リポジトリを優先した机上調査。インストール・起動・日本語での操作検証は実施していない。以下の「推論」は本件に対する設計判断であり、製品の公式推奨ではない。

## どのツールが本件に適するか

### Takeaway

少人数の評価で、盲検の A/B 選択・同等・判断不能・理由・JSON 保存に絞るなら、外部依存のないローカル HTML が第一候補。多数の評価者、継続的な割当、厳密な範囲アノテーションが最初から必要なら Label Studio を先に試す。Gradio / Streamlit は短期 Python 試作に有力だが、評価実験の設計や安全な保存を代わりに担うものではない。

### Cited Findings

| 候補 | 確認できた機能・運用 | 本件で必要な補完 |
|---|---|---|
| 静的 HTML + 標準ブラウザ API | FileReader は利用者が選択したローカルファイルを読める。Blob の URL 生成は標準 API。ローカルファイルを読み、結果をファイルとして出す実装の基盤になる。[FileReader](https://developer.mozilla.org/en-US/docs/Web/API/FileReader)、[createObjectURL](https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL_static) | 評価フォーム、左右割当、入力検証、再開、集計、保存完了の明示を実装する。 |
| Gradio | Python の UI ライブラリ。Flagging は入力と出力を実行機の CSV に記録できる。現行説明の CSVLogger は同時処理を考慮する。[Flagging](https://gradio.app/main/docs/gradio/flagging) | 左右の候補・同等・判断不能は独自フォームで設定。Flag ボタンだけでは評価者 ID、再開、重複回答・割当管理は完成しない。 |
| Streamlit | 選択、フォーム送信、テキスト入力、評価用ボタン等を備え、download_button で結果をダウンロードできる。[Widgets](https://docs.streamlit.io/develop/api-reference/widgets)、[Download](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button) | 原文と候補の配置、評価プロトコル、永続保存、左右の対応づけをアプリ側で作る。 |
| Label Studio | Pairwise タグで二つの文章を比較できる。Choices は任意の選択肢を設定でき、Labels はテキストの範囲にラベルを付ける。[Pairwise](https://labelstud.io/tags/pairwise.html)、[Choices](https://labelstud.io/tags/choices.html)、[Labels](https://labelstud.io/tags/labels.html) | Pairwise 単体の仕様から「同等」対応を仮定しない。A / B / 同等 / 判断不能は Choices で明示。候補名の除去と左右の割当は入力生成側で担う。 |
| Argilla | LabelQuestion、RatingQuestion、TextQuestion、RankingQuestion、SpanQuestion を組み合わせられる。SpanQuestion は重複範囲を許す設定を持つ。[Questions](https://docs.argilla.io/latest/reference/argilla/settings/questions/) | Ranking 単体で同順位を扱えるとの確認は取れていない。A / B / 同等 / 判断不能は LabelQuestion として持つのが確実。 |

- Label Studio は JSON / CSV 出力を持ち、生 JSON には元データ、アノテーション結果、評価者、所要時間等を保持する。既定では未評価のタスクは除かれるため、欠測率の集計では元台帳と突合する。[Export](https://labelstud.io/guide/export)
- Argilla は設定と回答をローカルディスクへ保存し、レコードを辞書・リストへ出せる。Hub への公開は必須ではない。[Import / Export](https://docs.argilla.io/latest/how_to_guides/import_export/)
- Gradio の現行 main の pyproject は Python >=3.10 と Apache-2.0 を記載。プロジェクト本体の Python 互換範囲と同一とは限らない。[pyproject](https://github.com/gradio-app/gradio/blob/main/pyproject.toml)
- Streamlit、Label Studio、Argilla の公式リポジトリで Apache-2.0 を確認した。これは本体のライセンスの確認であり、全依存物や商用版の条件の監査ではない。[Streamlit LICENSE](https://github.com/streamlit/streamlit/blob/develop/LICENSE)、[Label Studio LICENSE](https://github.com/HumanSignal/label-studio/blob/develop/LICENSE)、[Argilla repository](https://github.com/argilla-io/argilla)
- **Argilla は公式 README に、原著者が別のプロジェクトへ移行し、新機能追加を行わず、必要なバグ修正・パッチを継続する方針と保守者募集を明記している。** 過去の機能一覧だけで継続拡張の基盤に採用しない。[Argilla README](https://github.com/argilla-io/argilla)

### Inferences

- 推奨順位は、単独・少人数なら静的 HTML、共同運用の既存基盤なら Label Studio、既に Gradio / Streamlit が採用されている場合はそれを再利用、Argilla は既存利用がある場合の継続候補とする。評価者数だけでなく、割当・アクセス権・範囲選択の要否が分岐条件。
- 最小版はマウスによる精密な範囲アノテーションを必須にせず、「候補 A / 文番号 / 問題箇所の引用 / 問題の種類 / 望む修正」を記録する。正確な文字オフセットが必要な研究へ進む時点で Labels 等を採用する。日本語、絵文字、改行を跨ぐ範囲選択は独自実装の検証負担を増やす。
- Gradio の Flagging は収集の足場にはなるが、「役立った / 役立たない」だけでは意味変更の理由や修正箇所が得られないため、単純な組込み Flag をそのまま最終形にしない。
- 静的 HTML の初版で認証・DB・公開サーバー・リアルタイム共同編集を作る機会費用は大きい。必要が実証されるまでは、各評価者の JSON ファイルを後から統合する方式でよい。

### Gaps

- 各ツールの日本語 IME、段落を跨ぐ範囲、数式や Markdown 表示、キーボードのみの操作、同時保存、ブラウザ差は未検証。
- Label Studio の Enterprise の盲検・割当機能を Community Edition で使えるとは確認していない。公式マーケティング記事にある overlap / blind review を OSS の機能と同一視しない。
- 全製品の最新安定版番号、全依存物のライセンス、脆弱性、今後の保守 SLA は未監査。Gradio のいくつかの公式ガイドは取得時に markdown API へのリダイレクトが失敗したため、現在の公開設定の既定値を断定しない。

## ローカル運用とデータの保存をどう扱うか

### Takeaway

ローカルで動くことと、外部通信が一切ないことは別である。初版は文章を API に送らず、外部 CDN も使わず、JSON の明示的な保存と再読込みを持つ方式が適する。

### Cited Findings

- Streamlit は利用統計を収集するが、アプリに含まれる情報を閲覧・保存しないと説明する。`browser.gatherUsageStats = false` で統計送信を停止できる。[Configuration / Telemetry](https://docs.streamlit.io/develop/concepts/configuration/options)
- Argilla の Docker 展開は、サーバー・DB・Elasticsearch のローカル構成を持つ。Python SDK だけの導入とは異なる。[Docker deployment](https://docs.argilla.io/latest/getting_started/how-to-deploy-argilla-with-docker/)
- Argilla は匿名利用情報を送信し、`HF_HUB_DISABLE_TELEMETRY=1` で停止できる。公式にはレコードやデータセット名等は収集しないと説明する。[Telemetry](https://docs.argilla.io/latest/reference/argilla-server/telemetry/)
- Gradio の 4.44.1 公式文書には `analytics_enabled` / `GRADIO_ANALYTICS_ENABLED` の制御が記載される。ただしこれは過去版の仕様であり、実装時は採用版の API で確認する。[Versioned Interface docs](https://gradio.app/4.44.1/docs/gradio/interface)
- Label Studio はローカル環境へインストールでき、SQLite 等へアノテーションを保存する。[Install](https://labelstud.io/guide/install.html)、[Export storage](https://labelstud.io/guide/export.html)
- `file:` URL の localStorage の挙動は仕様上保証されない。プライベートブラウズでは最後のプライベートタブを閉じるとデータが削除される。[MDN localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)
- 表示に textContent を使うと文字列を HTML として解釈しない。評価対象文章を UI に埋め込む場合の基本選択になる。[MDN textContent](https://developer.mozilla.org/en-US/docs/Web/API/Node/textContent)

### Inferences

- 静的版は localStorage を唯一の保存先にしない。途中結果も JSON としてエクスポート・インポートでき、未保存を表示する。実運用で自動永続化が必要なら、同じ JSON 形式を保ってローカルサーバーの保存に移行する。
- 評価者が候補を知り得る名称、skill version、モデル名を評価画面から除き、対応表を収集後の統合処理で結び直す。表示を隠すだけで、配布 JSON に識別子の対応表が入っていれば厳密な盲検とはいえない。作者本人の原稿記憶による盲検の限界も残る。
- ローカル版の入力は JSON Schema 等の追加依存がなくても、必須キー・型・ID 重複・文章ハッシュ・既知の選択肢を明示検証できる。保存結果を入力文章やスキル版へ追跡できるよう、出力に評価プロトコル版と元タスク ID を含める。

### Gaps

- 実行機のインストール状態、ネットワーク遮断下での起動、通信キャプチャ、ファイル保存の復旧試験は行っていない。公式の telemetry 説明だけで完全な無通信を実証したとはいえない。

## 集計ライブラリとスキルをどう役割分担するか

### Takeaway

評価 UI と統計処理は切り分け、最初は件数・勝敗・同等率・欠測・意味変更の件数を集計する。人手データが揃ってから SciPy / statsmodels を分析環境の任意依存として使い、スキル本体に必須依存として組み込まない。

### Cited Findings

- SciPy の `stats.bootstrap` は信頼区間、paired データ、再標本化回数、乱数制御を持つ。[SciPy bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)
- statsmodels の `cohens_kappa` は二人の評価者の分割表を受け取り、単純 kappa と線形・二次重み等に対応する。[Cohen kappa](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.cohens_kappa.html)
- statsmodels は複数評価者のカテゴリ評価用 `fleiss_kappa` も提供する。[Fleiss kappa](https://www.statsmodels.org/stable/generated/statsmodels.stats.inter_rater.fleiss_kappa.html)
- セッションで提供された hugging-face:huggingface-gradio スキルは、Python の UI 部品、Blocks、イベント配線を支援する。[ローカル SKILL.md](/Users/masatomiwada/.codex/plugins/cache/openai-curated-remote/hugging-face/1.0.0/skills/gradio/SKILL.md)
- 提供された data:statistical-analysis スキルは効果量、信頼区間、小標本、多重比較の注意を含む。[ローカル SKILL.md](/Users/masatomiwada/.codex/plugins/cache/claude-cowork/data/1.0.0/skills/statistical-analysis/SKILL.md)
- 提供された skill-creator は、実際の利用や実証された失敗からスキルを改善し、検証スクリプトの通過が判断品質を証明するわけではないと明記する。[ローカル SKILL.md](/Users/masatomiwada/.codex/skills/.system/skill-creator/SKILL.md)

### Inferences

- 本件のデータ単位は原稿であり、同じ原稿に対する複数人の投票を独立した原稿数として扱わない。原稿単位で resample し、その中の全評価者を保持する設計が妥当。`paired=True` は対応の保持に有用だが、評価者間・原稿間の交差構造を自動で解決する機能ではない。
- UI の使いやすさを Gradio スキル、集計の検討を統計スキル、評価で見つけた失敗を既存プロンプトや例へ反映する作業を skill-creator と役割分担できる。どのスキルも日本語人手評価の妥当性の保証や評価者の代用にはならない。
- フィードバックから「失敗タイプ別の改善候補」を作り、別の未使用原稿で改訂前後を比較する。得られた評価をそのまま学習させたり、少数の好みを全モードへ即座に反映したりする必要はない。
- 効果予測として、記録の構造化・追跡性・繰り返し起こる欠点の特定には有用と見込める。一方、UI やライブラリを導入するだけで文章の品質や手戻り時間が何 % 改善するかを示す本件固有の証拠はない。

### Gaps

- SciPy / statsmodels の導入有無、採用環境の互換性、kappa の欠測・カテゴリ偏りへの適合性、cluster bootstrap の具体実装は未検証。数値計算を実施していない。
- 「ライブラリの利用」「スキルの配置」は、ホスト上での実呼出し・保存・品質改善の実証とは区別する必要がある。今回参照したスキルは調査対象であり、ツールの作成やスキル改訂は行っていない。
