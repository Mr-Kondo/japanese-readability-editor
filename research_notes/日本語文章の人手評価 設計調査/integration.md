# 既存スキルへの人手評価ツール統合

確認日: 2026-10-16。対象コミット: `26ec2c1d04da69409702f49408311c80af79174b`。リポジトリと祖先、今回参照する直下に AGENTS.md は存在せず、会話で提供された指示と RTK.md に従った。実装・モデル再実行・依存導入はしていない。

## 1. 何が既にあり、人手評価はどこを補うか

### Takeaway
現状は意味保持のモデル採点と機械的な候補検出が中心であり、人間が原文・依頼・資料を読み、読解上の利得と意味の損失を分けて記録する入口を加える価値がある。既存 JSON 記録を入力に使い、採点結果は別ファイルに保存する設計が小さい。

### Cited Findings
- スキルは「短くする」ことではなく意味・精度・必要情報を保ち認知負荷を下げることを目的とする。数値・条件・例外・主体等を保護し、文字数目安は合否基準ではない。— [SKILL.md:10-16](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:10)、[SKILL.md:64-83](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:64)
- 既存の比較手順は版名を伏せて左右順を入れ替え、意味保持 pass/fail/uncertain を各版に付け、両版 pass のペアだけ left/right/tie/uncertain で読みやすさを比べる。根拠は該当表現で説明する。人間・実装者自己レビュー・モデル採点を区別する契約が既にある。— [比較手順:30-40](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-comparison.md:30)
- 一般化評価は16件×3反復の48出力について意味保持46 pass・1 fail・1 uncertain、採点点検12項目全正答で HOLD。45個の B 出力のうち13個は前後の空白を除いて原文と同じで、意味保持の成功を読みやすさ改善とみなせない。独立した人間による46合格の確認ではない。— [評価結果:18-27](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization-result.md:18)
- 具体的失敗は方針表明「広げないようにします」を依頼「広げないでください」に変えた例。未判定は時間的前後「引き上げた後」を因果も示唆し得る「引き上げると」に変えた例。— [評価結果:29-49](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization-result.md:29)
- 開発用 evaluate_readability.py は三つのスキル本文、ハッシュ、ケース、生成・採点指示、モデル・生出力を run.json に記録する。採点対象には原文・文脈・候補・保持/禁止項目を持ち、source_id と kind を採点モデルから伏せる。ただしモデル採点は意味保持のみであり、読みやすさの勝敗を実装していない。— [生成・採点指示:18-31](/Volumes/SSD/Programming/japanese-readability-editor/tools/evaluate_readability.py:18)、[grading_items:108-150](/Volumes/SSD/Programming/japanese-readability-editor/tools/evaluate_readability.py:108)、[prepare:173-180](/Volumes/SSD/Programming/japanese-readability-editor/tools/evaluate_readability.py:173)
- 現在の実行記録は `schema_version/status/suite/outputs/grading_items/grading_calls/skill_sha256/runner_sha256/summary` を持ち、実物の summary も HOLD・46/1/1 と一致した。— [run.json](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization-run/run.json)
- 機械検査は修正候補の提示であり、意味保証ではない。C の strict も CRLF/BOM を正規化するため、全文字・既存空白・改行・BOMを保つ契約の確認には別途原文字またはバイト検査が必要。— [SKILL.md:103-113](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:103)、[評価手順:21-29](/Volumes/SSD/Programming/japanese-readability-editor/evals/README.md:21)

### Inferences
- 最小ツールは、既存 run.json と手動で用意した入力・出力を読み込み、ブラウザで評価し JSON を明示的に書き出す開発者用のローカル画面。版の比較は固定した左右割付をセッションごとに保持する。機械警告・既存 LLM 判定・版名は一次人手評価の提出まで伏せると、それらへの追随を抑えられる。
- 原文と候補の通常表示を基本にし、差分は任意表示とする。差分だけを読むと「変更された局所」に評価が偏り、段落全体の読解のつまずきを捉えにくい。
- B を主要パイロットとする根拠は既存の失敗と未判定が得られていること。長い文章、条件・否定、文の働き、因果の4層を意識して選ぶ。既知の fail/uncertain だけを選んだ集合は、障害発見には使えるが通常運用の改善率推定には使わない。

### Gaps
- このリポジトリに人間の独立評価データ、理解課題、読解時間の測定値は見つからない。現在のモデル合格率から読解速度・理解度の効果量は予測できない。
- 外部サービスの UI を使う場合の費用・共有範囲・運用負担は本調査担当の対象外。関連ライブラリ担当の調査と合わせて決める。

## 2. モード別の評価軸とフィードバック形式

### Takeaway
全モードに同じ「読みやすさ点」を付けるのは不適切である。まず依頼・モード・操作の契約違反を独立に記録し、品質の好みと切り分ける。

### Cited Findings
- A は新規生成、B は意味保持を伴う書き換え、C は改行と空行の挿入のみ。D は小説で plan/draft/continue/revise/critique の契約に分かれる。明示指定を優先し、不可能なら無断で別モードへ移らない。— [SKILL.md:18-35](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:18)
- A/B の構造修正は読者の問い、主述・修飾、否定・理由・条件の範囲、文の働き・時制の保持を確認する。B は元の文との照合を求める。— [SKILL.md:55-62](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:55)、[SKILL.md:88-101](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/SKILL.md:88)
- D revise は出来事・動機・関係・視点・確信度・開示順・象徴・結末を保ち、critique は本文を書き換えず根拠と読者への影響を示す。D draft/continue に原文完全保持や一文対応を要求しない。— [fiction-writing.md:23-35](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/references/fiction-writing.md:23)
- D は比喩説明化、短文化、主語補完、時制統一等を一律適用しない。文学的品質は文体保持、視点・知識、開示順、混乱、依頼適合から読み、単一数値で面白さを保証しない。— [fiction-writing.md:52-60](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/references/fiction-writing.md:52)、[fiction-writing.md:79-85](/Volumes/SSD/Programming/japanese-readability-editor/skill/japanese-readability-editor/references/fiction-writing.md:79)

### Inferences
提案する評価軸（仕様案であり実装済みではない）:

| モード | 契約・保持 | 人が判断する品質 | 避ける誤評価 |
|---|---|---|---|
| A | 指示・資料との一致、根拠のない追加、必須事項・用語・数値 | 読者の問いへの回答、構造、理解可能性、自然さ | 原文との完全一致、短さだけで成功扱い |
| B | 条件・否定・主体・数量・文の働き・強さ・時制 | 主述/修飾の明確さ、読み戻り、段落、自然さ。比較は保持成功ペアに限定 | 変更量が多いほど高評価、意味改変を相殺する総合点 |
| C | 改行挿入だけか機械検査。既存バイトの扱いも記録 | 話題境界、読み進めやすさ、分割過多 | 語の言い換えへの加点 |
| D | 操作、確定設定、既存本文の保持範囲、視点・知識・開示 | 語り口、会話、文の呼吸、意図しない混乱。好みと不整合を分離 | 一般文書用の短文化・結論先出し・比喩排除 |

最低限の記録を次に絞る:

- `task`: schema_version, task_id, mode, operation, request, audience/context, source/document_id, source_text または source_bytes_sha256, candidates[{candidate_id,text,skill_sha256,model_id,run_id,output_id}], rubric_version, split(training/regression/holdout)。既存 run の参照と出力ハッシュにより候補の取り違えを防ぐ。C でバイト保持を判定する場合はオリジナルファイルから生成した検査結果も保存する。
- `assignment`: assignment_id, task_id, evaluator_id（仮名で可）, evaluator_role/対象分野への慣れ, 候補の左右順, 実施日時。集計用の候補対応表は採点中に表示しない。
- `annotation`: annotation_id, assignment_id, revision, contract_status(pass/fail/uncertain), dimensions ごとの回答, preference(left/right/tie/uncertain/該当なし), evidence[{candidate_id,start,end,quote,category,severity,reason}], optional_suggestion, elapsed_ms, rubric_version。未回答・該当なし・不明・同点は別値にする。offset と quote の整合性を保存時に確認する。
- 最初のフォームは「契約違反/不明→該当箇所と理由」「品質比較→左右/同点/不明と理由」「任意修正案」の3ブロック。全員に多数の点数欄を埋めさせるより、少数の軸を根拠付きで取る。理解課題や時間比較は別の検証セッションにする。通常の採点時間は精読・注釈・UI操作込みであり読解速度ではない。
- 一次評価は独立に保存し、意見の不一致は上書きせず別の adjudication（裁定）として残す。「専門的に意味が違う」と「自分はこの文体が好き」を同じ重大度にしない。

### Gaps
- 評価者の人数・専門性・対象文書・作者本人か第三者かは未指定。集計で一般読者代表とみなす根拠はない。
- schema は案であり既存 schema v1 をそのまま変更する提案ではない。候補複数・A/C/D・手動入力を扱う共通 envelope は、既存の生成記録の外側に足す方が安全。

## 3. 最小の改善ループと将来MVPの変更範囲

### Takeaway
評価収集画面だけではスキルは改善しない。指摘を再現ケース・限定したルールや例へ変え、未使用文書で品質と保持の両方を再確認する工程が必要である。

### Cited Findings
- 既存の評価計画は入力・出力を見て調整した場合、その後は未使用文書での確認と呼ばず、回帰に移して新しい入力を使う。自作16文書×3反復は独立した48文書ではなく、一般的な失敗率を推定しない。— [readability-generalization.md:9-21](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization.md:9)、[同:43-45](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization.md:43)
- 現在のツールは新規出力先のみを許し、モデル採点形式、欠落、点検誤答、不明、モデル変化を検査する。テストは通信せず準備し、既存記録の上書きを拒否し、途中失敗を残すことを確認している。— [evaluate_readability.py:124-180](/Volumes/SSD/Programming/japanese-readability-editor/tools/evaluate_readability.py:124)、[test_evaluate_readability.py:28-99](/Volumes/SSD/Programming/japanese-readability-editor/tests/test_evaluate_readability.py:28)
- スキルは標準ライブラリだけで動くことを優先し、既存の開発評価CLIも配布スキルへ外部モデル依存を追加しない。— [design.md:42](/Volumes/SSD/Programming/japanese-readability-editor/docs/design.md:42)、[readability-generalization.md:25](/Volumes/SSD/Programming/japanese-readability-editor/evals/readability-generalization.md:25)
- 正本は skill/japanese-readability-editor/ のみで、配布ツールはそのファイルを列挙して ZIP・各環境向け複製を生成する。tools/ の開発用ツールはその正本の外にある。— [package.py:20-43](/Volumes/SSD/Programming/japanese-readability-editor/tools/package.py:20)、[test_package.py:43-54](/Volumes/SSD/Programming/japanese-readability-editor/tests/test_package.py:43)
- 全体検査は unittest discover を含むため tests/ に置いた検査は既存の全体検査で実行される。— [check_all.py:64-72](/Volumes/SSD/Programming/japanese-readability-editor/tools/check_all.py:64)

### Inferences
提案する改善サイクル:

1. スキル・モデル・指示・評価基準を固定。用途を揃えた文書を選び、候補を生成/取り込む。
2. 版名・LLM判定を伏せた独立人手評価を行う。少数を二重評価し、基準の食い違いを先に校正する。
3. 契約違反、品質問題、好み、判断材料不足に分ける。不一致は担当者が原文・資料で裁定する。
4. 反復する実証された問題だけを最小のスキル修正へ変える。既にある「文の働きを保つ」と同じ抽象指示を単純増殖させず、失敗/保持例と具体的な照合行動を検討する。
5. 指摘例と自然な原文を残す反例を回帰へ追加する。スキルの変更前後を同条件で比較し、保持悪化と品質利得を別に見る。
6. 既知例で成功しても別の未使用文書で再評価。評価者の好みに過度適合していないか別人/別分野で確認する。

将来MVPの最小スコープ（今回実装しない）:

| 範囲 | 変更案 | 影響・チェック |
|---|---|---|
| tools/ | human_review.py 等、1つの開発CLIで既存 run.json/共通 task JSON を読み、ローカル評価画面と回答 JSON を扱う | 既存 evaluate_readability.py の生成/採点 CLI・schema は維持。run は読み取り専用 |
| UI | 小さなローカル HTML/JS。Python 標準ライブラリで生成し、明示的に回答 JSON をダウンロード/再読込 | 日本語・改行・引用・コードをそのまま表示し、HTML文字列を実行しない。XSSを防ぐ textContent、キーボード操作、保存状態、再開後の左右順を確認 |
| データ | task/annotation の版付き形式、匿名評価者ID、根拠引用、分割、集計 | 不正 enum、候補不一致、重複・欠落、改訂の二重計上、未判定、Cの元バイト取り違えをテスト |
| tests/fixtures | 新規の人手評価ツールの小さなテスト・A/B/C/Dの最小 fixture | roundtrip、原文保持、不正入力、HTML混入、回答再開、保持失敗の比較除外。実ブラウザの保存とキーボード操作は別途確認 |
| evals/README.md・docs/ | 手順、評価基準、適用限界、JSON形式、保存先、既存記録 import の例 | 説明とCLIの整合。研究メモ・実文書を誤って公開/同梱しない |
| skill/・package/install・依存設定 | 評価UIの初期MVPでは変更不要 | ユーザーへ配布する要件が確定した段階で別途設計。UIを正本内へ置くと各配布先へ波及する |

- ローカル HTML の案は共同編集・認証・遠隔サーバー・自動クラウド送信・自動微調整を省ける。一方、回答のダウンロード/再取込は多少手間になる。評価が数人・数十件の段階なら運用基盤を持たない機会費用の方が小さいと予測する。多数人同時作業や厳密なアクセス管理が必要なら既存アノテーション基盤を優先する。
- 効果予測の順序: (i) 指摘の再現性と追跡可能性の向上は比較的見込みが高い、(ii) 人間固有の意味/読解問題の発見はモデルと異なる観点が得られる場合に期待、(iii) 特定失敗の減少は修正・回帰・未使用評価が成功した場合に期待、(iv) 一般的な理解度/速度/文学的品質の向上率は現時点では数値予測不能。
- 評価収集の工数、裁定、規則増加によるスキル肥大、慎重化で原文保持が増え改善が止まる逆効果を測る。提案工数や人数は計画値として置き、実測の効果量と混同しない。

### Gaps
- 人手評価の実測前なので、「何%改善」「何時間削減」は根拠がない。信頼度を付けるなら調査者の設計判断への確信と、実証された効果の確率を区別すべき。
- 新規 UI の実装、テスト、実ブラウザ検証、既存テスト再実行は本調査では行っていない。現在の人手評価不在は今回見たファイル範囲の所見であり、外部で未共有の評価がないことまで断言しない。
