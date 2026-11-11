"""事後の確認（事前登録にない）: 人が書いた失敗例（否定の文と次の文を「AではなくB」で結んだ文）を、
compare_rewrite.py が markers で示すかを、決定論的に調べる。モデルは呼ばない。"""
import json
from pathlib import Path
import sys

FOLDER = Path(__file__).resolve().parent
sys.path.insert(0, str(FOLDER))
import runner

MERGED = {
    "t01": "この機能は既存のファイルを上書きではなく、出力先に同名のファイルがあるときは連番を付けて別名で保存する。",
    "t02": "初期設定ではなく、設定画面でオンにすると更新があったときにメールが届く。",
    "t03": "この試験は本番のデータベースではなく、テスト用に用意した複製に対して実行する。",
    "t04": "遅延の原因はネットワークではなく、データベースのロック待ちが長く続いていたことである。",
    "t05": "旧バージョンでは設定ファイルを手で編集するのではなく、画面の指示に従って入力すると設定が書き込まれる。",
    "t06": "今回の変更は利用者向けの画面ではなく、内部の集計処理が新しくなった。",
    "t07": "申請は郵送ではなく、専用のフォームから提出してもらう。",
    "t08": "見積もりには保守費用ではなく、保守は別の契約として年額で提示する。",
    "t09": "この指標は応答の速さではなく、処理した件数を一定時間ごとに数えたものである。",
    "t10": "新しい担当者は、すぐにすべての権限を持つのではなく、最初の1か月は閲覧だけを許可し、その後に編集の権限を渡す。",
}

if __name__ == "__main__":
    cases = {c["id"]: c["text"] for c in json.loads((FOLDER / "cases.json").read_text(encoding="utf-8"))["cases"]}
    found = 0
    for case_id, after in MERGED.items():
        hits = runner.sentences_with_hit(after)
        result = runner.detected(cases[case_id], after, hits)
        found += result
        print(case_id, "検出" if result else "検出なし")
    print(f"markers で検出: {found}/{len(MERGED)}")
