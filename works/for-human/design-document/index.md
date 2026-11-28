[原文（英語）](../../for-agent/design-document/index.md)。食い違うときは原文が正本です。

# 設計文書の索引

## 番号付きフォルダ

| 番号 | 名称                     | 内容                                                                                                                                                                                                                |
| ---- | ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 001  | `knowledge-index`        | 開発の知見を後の更新で再利用するための試作の[計画](001-knowledge-index/pilot-plan-adr.md)と[結論](001-knowledge-index/conclude-pilot-adr.md)                                                                        |
| 002  | `installer`              | `install.py` と `uninstall.py` の[廃止](002-installer/remove-install-py-adr.md)                                                                                                                                     |
| 003  | `structure-rules`        | 文章構造の規則の評価。[OPQ 実験1・2](003-structure-rules/opq-analysis-adr.md)、[OPQ 実験3](003-structure-rules/opq-reeval-adr.md)、[節ごとに内容を1つに限る規則](003-structure-rules/section-single-message-adr.md) |
| 004  | `human-review-tooling`   | 日本語の文章の人による評価。[設計の調査](004-human-review-tooling/design-survey-document.md)と[統合の方針](004-human-review-tooling/integration-document.md)                                                        |
| 005  | `readability-principles` | 日本語の[読みやすさの設計原則](005-readability-principles/design-principles-document.md)と、参照した記事・プロジェクト                                                                                              |
| 006  | `fiction-mode`           | フィクション向けモードの[参照元と採否](006-fiction-mode/design-references-document.md)                                                                                                                              |

## 設計判断記録（ADR）

過去の判断を主題から探します。`status` は記録そのものの状態で、「決定」は提案を採用したかどうかを示します。

| 日付       | ADR                                                                              | `status`     | 決定                                                                                                                 |
| ---------- | -------------------------------------------------------------------------------- | ------------ | -------------------------------------------------------------------------------------------------------------------- |
| 2026-11-11 | [OPQ の再評価（実験3）](003-structure-rules/opq-reeval-adr.md)                   | `accepted`   | 不採用。並べ替えを許す採点では結論が先頭に来る傾向が改善したが、違反ゼロの基準を満たさなかった                       |
| 2026-11-11 | [OPQ の先頭結論（実験1・2）](003-structure-rules/opq-analysis-adr.md)            | `accepted`   | 不採用。先頭の結論は増えたが、意味の保持が基準を満たさなかった。追試は[実験3](003-structure-rules/opq-reeval-adr.md) |
| 2026-11-11 | [節ごとに内容を1つに限る規則](003-structure-rules/section-single-message-adr.md) | `accepted`   | 不採用。主な事例で見出しの分割は改善せず、候補はすべての事例で意味を保てなかった                                     |
| 2026-11-10 | [インストーラの廃止](002-installer/remove-install-py-adr.md)                     | `accepted`   | 採用。`install.py` と `uninstall.py` を削除し、既定は `npx skills add` にする。一部の配置先は手動コピーの手順を残す  |
| 2026-11-02 | [知識索引の試作の結論](001-knowledge-index/conclude-pilot-adr.md)                | `accepted`   | 試作の索引は手動の参照用に残す。改良提案へは自動で接続しない                                                         |
| 2026-11-02 | [知識索引の試作の計画](001-knowledge-index/pilot-plan-adr.md)                    | `superseded` | スキル更新の知見を記録する少数のページを計画した。最終判断は結論 ADR を参照                                          |

ADR を追加するか、`status` や後継を変えたときは、この表も更新します。

英訳前の日本語原文の出典、ハッシュ、凍結された評価記録の扱いは、[原文の索引](../../for-agent/design-document/index.md)にあります。
