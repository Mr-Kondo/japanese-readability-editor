# hermes-agent（2026-10-18）の確認

- 参考先: [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)（MIT）
- 確認した基準: 既定ブランチの先頭 `ccc6956`。リリースは v0.22.2（`watch.releases` は false なので、監視パスの変更だけで数えている）
- 確認日: 2026-10-18
- 範囲: 登録時の基準 `46d7718`（2026-10-10 の確認、`docs/environments.md` の Hermes の節）から。監視パスの変更ファイルは 4 件。追跡 Issue は #63。

## 何が変わったか（コミットの題から。コードは読んでいない）
- `agent/skill_bundles.py`: スキルの束のキャッシュが、同じ時刻の編集を見落とさないようにした。保存を原子的にした。
- `agent/skill_commands.py`: スキルの走査の署名を、カタログの木全体にした。別の端末から入れたスキルが、すぐ `/` コマンドに出るようにした。圧縮のときのスキルの印の扱い。
- `agent/skill_preprocessing.py`: 入れ子、別プロファイル、読めないロックの、コミュニティのスキルでは、インラインのシェルを無効にした。
- `tools/skill_manager_tool.py`: エスケープのずれの補正を共有した。

## 採否
| 項目 | 採否 |
|---|---|
| 配置先、`hermes skills list`、`trust`、`[Skill directory]` の動作（`docs/environments.md` の記述） | 変更なし。記述を更新する根拠は見つからなかった |
| インラインのシェルの無効化 | この Skill は、インラインのシェルを使わない。対応なし |

## 限界
- コミットの題だけを読んだ。実機の Hermes（v0.22.2）では確かめていない。`docs/environments.md` の確認日（2026-10-10）と版（v0.21.7）は、このとおり残す。
