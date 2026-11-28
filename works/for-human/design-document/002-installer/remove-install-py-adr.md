[原文（英語）](../../../for-agent/design-document/002-installer/remove-install-py-adr.md)。食い違うときは原文が正本です。

# install.py と uninstall.py を廃止し、導入を npx skills add に統一する

状態: `accepted`（2026-11-10）

## 要点

- 採用する。`tools/install.py`、`tools/uninstall.py`、それぞれのテストを削除する。
- 導入は `npx skills add` に統一する。過去の検証記録は書き換えない。
- `package.py` と `verify_install.py` は残す。配置先の表と解決処理は `skill_env.py` へ移す。
- 不採用である。配置ツール全体の削除（CI と配布の再構築が必要になるため）と、`install.py` だけの削除（`uninstall.py` が孤立するため）を採らない。
- Antigravity は配置先が一致しないため、`cp -R` の手順を文書に残す。

## 目的

`install.py`（455行）、`uninstall.py`（140行）、テスト（865行）の保守を減らし、導入手順を1つにします。Skill は `npx skills add` で導入できる状態になりました（PR #155）。追跡は Issue #156 です。

## アプローチ

仮説は「`npx skills add` が、どの環境でも `install.py` の配置を代替できる」です。2026-11-10 に、macOS・skills 1.7.6・隔離された HOME で5環境を確かめました。

| 確認                     | 結果                                                                                                    |
| ------------------------ | ------------------------------------------------------------------------------------------------------- |
| Codex、OpenCode          | `~/.agents/skills/` に入る。`install.py` の共通配置先と一致する。                                       |
| Claude Code              | 1環境では `~/.claude/skills/` にコピーされ、複数環境では `~/.agents/skills/` へリンクされる。           |
| Hermes                   | `~/.hermes/skills/` にリンクされ、`install.py` の既定と一致する。`HERMES_HOME` とプロファイルは未確認。 |
| Antigravity              | 全ユーザー向けの `~/.agents/skills/` に入る。`install.py` の `~/.gemini/` 配下とは**一致しない**。      |
| 再導入                   | 同名の項目は上書きされ、その中に追加したファイルも消える。                                              |
| `remove`、検証スクリプト | `remove` は動作した。`verify_install.py` は両方の場所でエラーと警告が0件だった。                        |

## 限界・未確認

- 失う機能は、リポジトリへの直接リンク（`--link`）、上書き前のバックアップ、`--dry-run`、重複の警告である。直接リンクは `ln -s` の手順で補う。
- 上書きされた内容は、バックアップがないため復元できない。
- `npx skills` による GitHub からの導入、`update`、Hermes のプロファイル選択は未確認である。確かめるまで検証済みと書かない。
- `install.py` で入れた既存の複製は消えない。文書は、再導入の前に古い複製を削除するよう書く。
