# hermes-agent の確認（2026-10-19）

- 参考先: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)（MIT）
- 確認した基準: コミット `20acba0`
- 確認日: 2026-10-19
- 範囲: 前回の基準 `ccc6956` から `20acba0` まで（340 コミット）。監視パスの変更は 3 ファイル、追跡 Issue は #78。

## 何が変わったか

監視パスの 3 ファイルの変更は、関数名の `_` を外した公開化だけである（`_skill_search_dirs` → `skill_search_dirs`、`_find_all_skills` → `find_all_skills`、`_read_skill_name` → `read_skill_name`）。Skill の探索場所、読み込み、trust の確認の動作を変える差分はない。

## こちらとの照合

`docs/environments.md` の Hermes Agent の記述（配置先、`hermes skills trust`）は、監視パスの差分から変える必要がない。実機での再確認はしていない。

## 採否

採用候補なし。Issue は作らない。

## 限界

- 監視パスの外（`tools/skills_tool.py` など）の変更は見ていない。探索場所そのものの変更は、この範囲では確かめられていない。
