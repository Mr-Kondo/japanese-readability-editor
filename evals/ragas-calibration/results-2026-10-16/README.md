# Ragas 検証の記録（2026-10-16）

[Ragas による自動評価](../../../docs/ragas-evaluation.md#検証結果2026-10-16) の元データ。解釈と限界は文書を参照する。

| ディレクトリ | 内容 |
|---|---|
| `artificial/` | 人工13件（`../artificial-cases.json`）の採点。3分割で実行した `ragas-run-part*.json` と、構成ラベルとの突き合わせ `ragas-calibration.*` |
| `digital-agency-tuning/` | #40 調整用3抜粋のスキル生成と既存のLLM採点（`skill-generation-and-llm-grading-run.json`）、Ragas 採点 `ragas-run-part*.json`、並置 `ragas-vs-llm.*` |

- 構成ラベルは人の確認前。実運用の成績ではない。実生成にはラベルがなく、正しさを判定していない。
- 各 `ragas-run-part*.json` は、設定、Ragas とその依存の版、呼出しごとのプロンプトのハッシュ・モデル識別子・費用・構造化出力を持つ。**呼出しごとの生応答（`raw/`）は保存していない**。
- 分割実行の統合は `calibrate`／`compare-llm` が行う（設定が違う run は拒否する）。

```bash
.venv-ragas/bin/python tools/ragas_readability.py calibrate \
  --run evals/ragas-calibration/results-2026-10-16/artificial/ragas-run-part{1,2,3}.json \
  --labels evals/ragas-calibration/artificial-labels.json --out-dir /tmp/jre-calib
.venv-ragas/bin/python tools/ragas_readability.py compare-llm \
  --ragas-run evals/ragas-calibration/results-2026-10-16/digital-agency-tuning/ragas-run-part{1,2,3}.json \
  --eval-run evals/ragas-calibration/results-2026-10-16/digital-agency-tuning/skill-generation-and-llm-grading-run.json \
  --out-dir /tmp/jre-vs-llm
```
