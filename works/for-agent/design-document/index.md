# 設計判断の索引

## 番号付きフォルダ

| 番号 | 名称                   | 何について書かれているか                                                                 |
| ---- | ---------------------- | ---------------------------------------------------------------------------------------- |
| 001  | knowledge-index        | 開発時の知見を次の更新に使う知識索引の試行（試行計画と終了の判断）                       |
| 002  | installer              | 導入スクリプト `install.py` と `uninstall.py` の廃止                                     |
| 003  | structure-rules        | 文書構造の規則（OPQ 分析と再評価、節を一つのメッセージに絞る規則）の評価                 |
| 004  | human-review-tooling   | 日本語文章の人手評価ツールの設計調査と連携方針                                           |
| 005  | readability-principles | 日本語可読性の設計原則と、参考にした記事・プロジェクト                                   |
| 006  | fiction-mode           | 小説モードの設計参考と限界                                                               |

## 判断記録（ADR）

過去の判断を確認するときは、テーマから該当する ADR を開きます。`status` は ADR 自体の状態で、規則や提案の採否は「判断」に記載しています。

| 日付       | ADR                                                                        | `status`     | 判断                                                                                                                                |
| ---------- | -------------------------------------------------------------------------- | ------------ | ----------------------------------------------------------------------------------------------------------------------------------- |
| 2026-11-11 | [OPQ の規則の再評価（実験3）](003-structure-rules/opq-reeval-adr.md)           | `accepted`   | 見送り。順序変更を許す採点基準で冒頭配置は改善したが、制約違反ゼロの基準を満たさなかった。                                          |
| 2026-11-11 | [OPQ に基づく結論の冒頭配置（実験1・2）](003-structure-rules/opq-analysis-adr.md)       | `accepted`   | 見送り。冒頭配置は増えたが、意味保持の基準を満たさなかった。後続の確認は[実験3](003-structure-rules/opq-reeval-adr.md)を参照。          |
| 2026-11-11 | [節・項を一つのメッセージに絞る規則](003-structure-rules/section-single-message-adr.md) | `accepted`   | 見送り。主ケースで見出し分割の改善が見られず、候補版の意味保持も全件合格に届かなかった。                                            |
| 2026-11-10 | [導入スクリプトの廃止](002-installer/remove-install-py-adr.md)                    | `accepted`   | `install.py` と `uninstall.py` を廃止。`npx skills add` を基本とし、一部の配置先には手動コピーの手順を残す。                        |
| 2026-11-02 | [知識索引の試行終了](001-knowledge-index/conclude-pilot-adr.md)        | `accepted`   | 試作索引を手動参照用に残し、改良提案機能への自動接続は見送る。                                                                      |
| 2026-11-02 | [知識索引の試行計画](001-knowledge-index/pilot-plan-adr.md)           | `superseded` | スキル更新の知見を少数のページにまとめて試す計画。最終判断は[試行終了の ADR](001-knowledge-index/conclude-pilot-adr.md)を参照。 |

ADR を追加したときや、状態・後継が変わったときは、この表も更新します。

`003-structure-rules/` の `opq-analysis-adr.md` と `opq-reeval-adr.md` は、`evals/` の runner がハッシュで照合するため、本文を変えていません。そのため、本文中の相対リンクは旧位置（`adr/`）のままで、現在は解決しません。

`evals/opq-run`・`opq2-run`・`opq3-run` の `runner.py` は、記録した実行（`run.json`）が自分のハッシュを検査するため、書き換えていません。`runner.py` が `prepare()` で読む ADR のパスは旧 `adr/` のままです。完了済みの実験で、`prepare()` の再実行は想定していません。再現するときは、旧パスに ADR を置くか、新しい記録を作ってください。

`evals/no-skill-comparison.md`（計画書）も、`evals/no-skill-run/run.json` が `plan_sha256` で凍結しているため書き換えていません。本文中の `docs/design.md` は旧パスのままで、現在の場所は `005-readability-principles/design-principles-document.md` です。

