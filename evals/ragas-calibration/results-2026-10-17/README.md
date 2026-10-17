# Ragas の追加検証の記録（2026-10-17）

[Ragas による自動評価](../../../docs/ragas-evaluation.md#追加の検証2026-10-17)の元データ。解釈と限界は文書を参照する。2026-10-16 の記録は [`../results-2026-10-16/`](../results-2026-10-16/README.md)。

| ディレクトリ | 内容 |
|---|---|
| `subtle/` | 微妙な欠陥を含む人工21件（`../artificial-cases-subtle.json`、ラベルは `../artificial-labels-subtle.json`）の採点 `ragas-run-part*.json` と、構成ラベルとの突き合わせ |
| `art-repeats/` | 既存の人工13件の再実行2回（`repeat1-part*.json`、`repeat2-part*.json`）と、2026-10-16 の実行を加えた3回分の安定性 `ragas-stability.*` |
| `coverage-low/` | 人工34件（13＋21）の factual だけを `coverage=low` で採点した記録と突き合わせ |
| `discriminate/` | 人工34件の rubric を `--discriminate`（観点の弁別の指示つき）で採点した記録と突き合わせ |
| `comparison/` | 同じ34件で、既定の設定（`coverage=high`、指示なし）の突き合わせ。`labels-34.json` は両方のラベルを合算した作業用ファイル |

- 構成ラベルは人の確認前。実運用の成績ではない。件数が少なく、率は記述値。
- 設定は `atomicity=high`、`--profile gov-org`（7観点）、評価器は Claude CLI。macOS、Python 3.13.16、`tools/ragas-constraints.txt` の版で実行した。**呼出しごとの生応答（`raw/`）は保存していない**。
- 今回の新規実行の費用は、定価換算で合計約7.5 USD。
- `comparison/` は、既定の設定の13件の再実行1回目（`art-repeats/repeat1-*`）と `subtle/` を統合して作った。
- 今回の新規実行で失敗した呼出しは1件（`subtle/` の `paraphrase-k8s` の recall、モデル出力の JSON の解析エラー）。採点不能として記録され、0点にはしていない。

```bash
# 人工21件（微妙な欠陥）
.venv-ragas/bin/python tools/ragas_readability.py calibrate \
  --run evals/ragas-calibration/results-2026-10-17/subtle/ragas-run-part{1,2,3}.json \
  --labels evals/ragas-calibration/artificial-labels-subtle.json --out-dir /tmp/jre-subtle-calib
# 人工13件の3回分の安定性（1回目は 2026-10-16 の記録）
.venv-ragas/bin/python tools/ragas_readability.py stability \
  --repeat evals/ragas-calibration/results-2026-10-16/artificial/ragas-run-part{1,2,3}.json \
  --repeat evals/ragas-calibration/results-2026-10-17/art-repeats/repeat1-part{1,2,3}.json \
  --repeat evals/ragas-calibration/results-2026-10-17/art-repeats/repeat2-part{1,2,3}.json \
  --labels evals/ragas-calibration/artificial-labels.json --out-dir /tmp/jre-stability
# 観点の弁別の指示つき（34件）
.venv-ragas/bin/python tools/ragas_readability.py calibrate \
  --run evals/ragas-calibration/results-2026-10-17/discriminate/{art,subtle}-ragas-run-part{1,2,3}.json \
  --labels evals/ragas-calibration/results-2026-10-17/comparison/labels-34.json --out-dir /tmp/jre-disc-calib
```
