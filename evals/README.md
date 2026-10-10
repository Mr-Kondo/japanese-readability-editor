# 小説モードの評価ケース

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
