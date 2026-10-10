# 小説モードの設計参考・採否・限界

確認日：2026-10-10。次の8ページは実際に本文を取得して読んだ。外部本文・コード・テンプレートは転載せず、設計の着想から独自に実装した。追加サービス・有料 API・新規依存はない。

| 資料（直接リンク） | 読めた内容・採用 | 不採用・適用限界 |
|---|---|---|
| [danjdewhurst/story-skills](https://github.com/danjdewhurst/story-skills) | README の chapter-writing、voice-style、revision-continuity、line-editing の責務分離。設定・文体・整合性を区別 | 24技能・CLI・出版・定期執筆・整合性コンパイラは取り込まない。構造化記録の検査を本文の意味保証へ広げない |
| [wgwtest/novel-writing](https://github.com/wgwtest/novel-writing/blob/main/novel-writing/SKILL.md) | planning、drafting/continuing、reviewing の分岐。人物の知識・推論・誤認、因果診断、用途別参照 | 人物初登場で属性を足す、全場面の変化などの一律要件は採らない |
| [alt-code-ai/agent: fiction-writing-prose](https://github.com/alt-code-ai/agent/blob/main/skills/fiction-writing-prose/SKILL.md) | 語彙・構文・知覚・リズム、視点・語りの距離、場面と要約の役割 | 説明なら必ず書き直す、五感・感情語排除・特定リズムの絶対化は採らない |
| [葦沢かもめ：AIを使って小説を書く方法](https://note.com/ashizawakamome/n/n7fbe741f0906) | 作者に合う工程と、工程ごとの知識・評価項目の整理 | 固定工程・必須承認待ちを導入しない。成功談を普遍的品質保証にしない |
| [鳴島悠希：CodexCLIで長編小説執筆環境](https://note.com/x2775co/n/n9c3dd65fc2aa) | 文体サンプル・canon・outline の区別、出来事の発生順と読者への提示順の分離 | 配布 ZIP は未取得・未検証。GraphRAG・巨大な初期構成は導入しない |
| [CARTA TECH BLOG：Agentic-Writing](https://techblog.cartaholdings.co.jp/entry/claude-code-skill-agentic-writing) | 文体ルールと作者の原文サンプルの併用 | 技術記事の体験談であり小説品質向上の実証ではない。構想合意と出版の必須化は採らない |
| [Agent Skills Specification](https://agentskills.io/specification) | SKILL.md を入口に、scripts/references/assets を必要時に読む構成 | 仕様準拠から各製品の動作や品質を保証しない |
| [Anthropic：Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) | コード・モデル・人間による評価を区別。モデル判定にも非決定性と校正の限界がある | 静的検査を指示遵守の実行証拠にしない。単一数値で面白さを保証しない |

ライセンスは [story-skills の LICENSE](https://raw.githubusercontent.com/danjdewhurst/story-skills/main/LICENSE) と [novel-writing の LICENSE](https://raw.githubusercontent.com/wgwtest/novel-writing/main/LICENSE) を読んで MIT と確認した。alt-code-ai/agent のライセンス、記事・仕様等の転載許諾は未確認。転載していないため外部コードの帰属を実装へ混ぜない。今後転用する場合は、その版の許諾と帰属条件を別途確認する。

## 今回の判断

- A/B/C の名称・明示指定・既存スクリプト既定値を維持する。矛盾する複数モード指定は原文を保って確認する。
- D の新規生成と保持を伴う推敲を操作で分け、一般文書の短文化・比喩説明化から分岐させる。
- 小さな依頼に管理一式を要求しない。長編メモは任意とし、原稿・設定の自動上書きを禁止する。
- 設定指定の検査は文字列の単純一致に限る。数・括弧・表記の候補は、人が読むための補助とする。
- コアに Codex 固有 API を導入しない。既存配布先・OpenCode/Hermes のアダプターと文化庁関連機能を維持する。

## 検証の限界

決定的なテストは CLI・データ・保持・配布を検査する。モデル挙動は [評価ケースと実行記録](../evals/README.md)で別に扱う。実装者の自己レビューは独立したモデル実行や人間による文学的評価の代わりにならない。創作文全体の完全一致を正解にせず、文体、視点・知識、開示、混乱、依頼適合を見る。参照資料の創作論を普遍的な文学の法則と扱わない。
