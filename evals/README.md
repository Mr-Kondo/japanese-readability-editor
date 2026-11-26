# スキルの評価ケース

JAIST の技術文書指針を参考にした短い複合語と比較説明の確認は、[計画](jaist-ambiguity.md)、[自作10ケース](jaist-ambiguity-cases.json)、[結果](jaist-ambiguity-result.md)を参照する。現行版で30出力を生成したが、独立採点の点検が5件中1件で一致せず、規則の改修を保留した。実行時のスキルは v0.25.1 を維持する。

確認応答を短くする追加試行は、[計画](jaist-ambiguity2.md)、[自作10ケースと点検7件](jaist-ambiguity2-cases.json)、[比較結果](jaist-ambiguity2-result.md)を参照する。単純な確認4ケースの12出力は、文字数の中央値が約83%減ったが、1件が事前の上限を超えたため候補を採用しなかった。

未使用の文構造・模擬会話・利用者提供文の追加確認は、[計画](jaist-ambiguity3.md)、[固定ケース](jaist-ambiguity3-cases.json)、[結果](jaist-ambiguity3-result.md)を参照する。短縮は別の文構造でも観測したが、意味のずれと依頼条件の逸脱が残った。採点点検も19/20一致で条件未達のため、品質の確定判定を保留し、不採用を維持した。

定量評点と根拠付きの定性評価を、自動／手動の2系統で行う場合は[人手・自動評価ツールの手順](../docs/human-evaluation.md)を参照する。`tools/review_readability.py` は既存の `run.json` と独自の `cases` JSONを取り込み、通信不要の表層検査、任意のLLM採点、ローカルHTMLでの人手評価、回答集計を行う。初回は[人工例題](human-review-example.json)で試せる。

モードBの旧新版・スキル有無を匿名比較する場合は `tools/compare_readability.py` を使う。[比較用の練習3例](blind-comparison-example.json)から評価者別の配布物を作り、候補別の意味保持、引用付きの指摘、両候補合格内の選好、全割付の欠測を記録する。主催者用の版名対応表は配布物から分離する。

不一致・重大度の集計、確認済み指摘の回帰ケース化、人手とLLMの照合、単一版だけを読む理解問題、文書単位の近似区間の手順も[評価ツールのガイド](../docs/human-evaluation.md)にある。[理解問題の人工例](comprehension-example.json)は操作練習であり、効果の実証ではない。開発に使う回帰ケースと、最後に検証する未使用文書を分ける。

公開された実文書（デジタル庁・Python・Kubernetes・青空文庫・IPA）を追加する計画と台帳は、[計画](../docs/public-document-evaluation.md)と[台帳](public-documents/manifest.json)を参照する。原本は取得済みで、抜粋は人の確認待ちの候補である。

Ragas の評価器を調べるための[人工の校正ケース](ragas-calibration/artificial-cases.json)と[期待ラベル](ragas-calibration/artificial-labels.json)は、構成によるラベルで人の確認前である。実運用の成績ではない。手順は[Ragas による自動評価](../docs/ragas-evaluation.md)を参照する。

万能動詞の具体化例の修正は、[実装案と追加調査](../docs/concretization-example-plan.md)、[比較手順](concretization-comparison.md)、[実装・比較結果](concretization-result.md)を参照する。[自作6入力](concretization-cases.json)は、資料なし／ありの対と自然な原文の保持を含む回帰確認用で、未使用文書への一般化を示すものではない。

一般文書 A/B の構造修正・文の働きの保持は、[比較評価の手順](readability-comparison.md)と[自作12ケース](readability-cases.json)を使う。変更前後の条件を固定し、意味保持と読みやすさを別々に判断する。

意味の問い直しと、対象・条件・状態の照合は、[人工8ケース](meaning-confirmation-cases.json)と[確認手順・結果](meaning-confirmation-result.md)を使う。質問後の回答を使う例と、質問しない対照例を含む。既存の単発本文生成用CLIは対話を評価しないため、そのまま成功率を算出しない。

途中で見つかった質問・調整案・担当の省略・本文のみの保持に関する懸念は、[人工16ケース](meaning-concern-cases.json)と[懸念の検討・再検証](meaning-concern-result.md)で追跡する。各ケースを別の文脈で確認し、実行失敗やモデル・条件の変更を記録する。

初回の意味保持失敗に対する修正は、同じ12ケースでの再比較と[追加6ケース](readability-preservation-cases.json)で確認した。[修正・再評価の結果](readability-preservation-result.md)と[生の実行記録](readability-preservation-run.json)を参照する。

さらに広い文章での確認は、[未使用文書による追加評価](readability-generalization.md)を使う。未使用16文書を1件ずつ3回生成し、採点点検用12項目を混ぜる。[実行ツール](../tools/evaluate_readability.py)は既定では準備だけを行い、`--execute`がある場合だけ外部Claudeを呼ぶ。[準備済みの入力・指示](readability-generalization-plan/run.json)と[実施状況](readability-generalization-result.md)は、モデルによる検証結果と区別する。

節・項で伝える内容を一つに絞る規則の、旧版と候補版の比較は、[自作11ケース](section-single-message-cases.json)と[結果（見送り）](section-single-message-result.md)を参照する。規則は足していない。実行記録は[section-single-message-run/](section-single-message-run/)にある。

OPQ（目標・問題・疑問）から結論を決める規則の、旧版と候補版の比較は、[実験1の11ケース](opq-cases.json)、[実験2の15ケース](opq2-cases.json)、[結果（見送り）](opq-result.md)を参照する。冒頭配置の効果は観測できたが、意味保持の事前指標を満たさず、規則は足していない。実行記録は[opq-run/](opq-run/)と[opq2-run/](opq2-run/)にある。意味保持の基準を事前登録し直した[実験3の13ケース](opq3-cases.json)と[実行記録](opq3-run/)も、規則は足していない（結果は[opq-result.md](opq-result.md)）。

現行スキルを、スキルなし・数行の指示と、同じ12ケースで比べる評価は、[計画](no-skill-comparison.md)と[結果](no-skill-comparison-result.md)を使う。モデル採点では意味保持と読みやすさで優位だったが、規則に沿った自作の出題での結果で、一般的な優位の証拠ではない。

原文にない「ではなく」を現行スキルが作るかを測る評価は、[計画](negation-contrast.md)と[結果](negation-contrast-result.md)を使う。短い合成文（16本×3回）では、42/48が原文のまま返り、2文を1文にまとめる書き換えが起きなかったため、発生は測れていない。検出は、人が書いた例10本中9本を、示さなかった（事後の確認）。冗長な段落12本×3回で測り直した[結果](negation-contrast-long-result.md)では、書き換えは全出力で起き（24/24）、作った出力は0件だった。

太字のラベルを文へ入れる推敲で、ラベルの語と働きが落ちるかを測る評価（#57 の E）は、[計画](bold-label.md)と[結果](bold-label-result.md)を使う。10本×3回では、現行スキルは太字を残して箇条書きへ直す書き換えが多く、太字を文へ入れた出力は target 24件のうち3件（1本の3回）だけだった。計画の前提（12件以上）を満たさず、測定は成立していない。

認知負荷5項目（比較・探索・推測・要約・暗算）の規則の初回比較は、[計画](cognitive-load.md)と[結果](cognitive-load-result.md)を参照する。差・合計の計算（A）は[追加比較の結果](cognitive-load-a2-result.md)を踏まえ、v0.25.0 で採用した。不足の指摘（E）は初回の呼び出しの指示（本文だけ返す）と衝突して測れていないため、下記で別に比較した。初回の実行記録は[cognitive-load-run/](cognitive-load-run/)にある。

不足の指摘の規則の旧版と候補版の比較は、[計画](gap-note.md)と[結果](gap-note-result.md)を参照する。新版は不足を指摘したが、情報がそろった原文にも指摘を出し（11/15、旧版は1/15）、計画の基準で不採用になった。規則は足していない。実行記録は[gap-note-run/](gap-note-run/)にある。

原文の語に絞った不足の指摘の再比較は、[計画](gap-note2.md)と[結果](gap-note2-result.md)を参照する。Sonnet で108出力を完了したが、事前の語群判定は旧版0/24、候補版1/24で、差6件以上の基準を満たさず不採用とした。判定器の取りこぼしがあるため、効果がない証明とは扱わない。実行時のスキルは v0.25.0 を維持する。

## 小説モード

[fiction-cases.json](fiction-cases.json) は24件の自作入力、期待する操作、守る事実、禁止する変更、評価方法を持つ。covers は18の必須観点に対応する。公開小説の本文は使っていない。開発資料であり実行時の依存ではない。

[fiction-model-run.json](fiction-model-run.json) に先頭12件の実入力・実出力・読み込んだスキルのハッシュを記録した。別の新しいモデル文脈に更新したスキルを読み込ませ、12件を一括で処理した。別のモデル文脈による判定は12件pass、0件fail、0件uncertain。正確なモデル識別子・サンプリング設定は取得できず、製品固有のスキル呼び出しや他製品は未検証。e13〜e24のモデル挙動は未実行である。

## ケースと評価の方法

各ケースに id、covers、input、expected_mode、expected_operation、facts_to_preserve、forbidden_changes、evaluation_method を持たせる。モード競合が未解決なら undetermined、対象不足や競合の確認は clarify。Dはplan/draft/continue/revise/critique、既存モードはgenerate/rewrite/paragraph-onlyと記録する。

文章全体の完全一致を正解にしない。文体、視点と知識、開示順序、意図しない混乱、依頼への適合を別々に確認する。面白さを数値一つで保証しない。Cは変更範囲の契約として全文字の保持を厳密に検査できる。

1. SKILL.mdと必要な参照を新しい文脈へ読み込ませ、コミットIDまたはハッシュを記録する。インストール済みの古いコピーを使わない。
2. 実入力・実出力・実行日時・モデル・読み込んだ指示を残す。モデル名を取得できない場合は不明とする。一括実行やケース間の文脈共有も記録する。
3. 観点ごとにpass/fail/uncertainと出力箇所・理由を残す。実装者の自己レビュー、独立モデルの採点、人間の文学的評価を区別する。採点モデルの指示と実出力も保存できなければ、その記録不足を限界として残す。
4. Cはtarget_textとverify_preservation.py --strictで照合する。既定の空白除去比較だけでは不十分で、--strictもCRLF/BOMを正規化する。[生バイト比較](../tests/test_fiction_integration.py) を併用し、空白・タブ・既存改行・BOMが同じ位置に残り、追加は改行だけか確かめる。本文以外の解説を勝手に除去して成功扱いしない。
5. 実行済み・未実行・環境スキップを分ける。失敗を残して同じ入力で再実行する。独立実行ができない場合はモデル挙動を未検証とする。

外部送信、有料APIの新規契約、新規インストールは必須にしない。

## 決定的な構造検査

```bash
python3 -m unittest discover -s tests -p 'test_fiction_evals.py'
```

構造検査は項目・観点番号・操作の網羅性だけを確認する。モデルを呼ばず、モデル挙動や文学的品質の証拠にはしない。SKILL.mdのキーワードの存在も指示に従った証拠ではない。
