---
status: accepted
date: 2026-11-10
decision-makers: 利用者（Q1〜Q6 の推奨案を承認）、Claude Code（実測と実装）
---

# install.py と uninstall.py を廃止し、導入を `npx skills add` に一本化する

## 文脈

`skills/*/SKILL.md` の配置により、`npx skills add` で導入できるようになった（[Issue #155 の PR](https://github.com/Mr-Kondo/japanese-readability-editor/pull/155)）。一方、`tools/install.py`（455行）、`tools/uninstall.py`（140行）、それらのテスト（865行）は、配置先の表、OpenCode と Hermes の配置先の解決、退避、リンクなどを自前で保守している。導入手段が2つあると、README と手順が煩雑になる。追跡: [Issue #156](https://github.com/Mr-Kondo/japanese-readability-editor/issues/156)。

## 仮説と撤退条件

- 仮説: `npx skills add` が、`install.py` の担っていた配置を全環境で置き換えられ、`install.py` は保守費だけを生む。
- 反証の指標: 削除前に、隔離した HOME で5環境（Codex、Claude Code、OpenCode、Hermes、Antigravity）へ入れ、配置先が `install.py` と同じ場所か、`verify_install.py` が「正本と一致」と「同梱スクリプトの動作」を通すか、2回入れて上書きされるかを見る。通らない環境は、その環境の手順を残す。

## 観測（2026-11-10、macOS、skills 1.7.6、隔離した HOME）

| 確認 | 結果 |
|---|---|
| Codex、OpenCode | `~/.agents/skills/` に入る。`install.py` の共通配置と一致。OpenCode は `.agents/skills/` を読む（公式文書） |
| Claude Code | 1環境だけなら `~/.claude/skills/` へ実体をコピー。複数環境なら `~/.agents/skills/` の実体へのリンク |
| Hermes | `~/.hermes/skills/` へのリンク。`install.py` の既定と一致。`HERMES_HOME`・プロファイルの指定は未確認 |
| Antigravity IDE・CLI | ユーザー全体では `~/.agents/skills/` に入る。`install.py` は `~/.gemini/config/skills/` と `~/.gemini/antigravity-cli/skills/` に置いていた。**一致しない** |
| 再実行 | 同名のものを上書きした（追加した余分なファイルも消えた） |
| `remove` | 動作した |
| `verify_install.py` | `~/.agents/skills/` と `~/.claude/skills/` の両方で、0 error、0 warning |

## 決定

1. `tools/install.py`、`tools/uninstall.py`、`tests/test_install.py`、`tests/test_uninstall.py` を削除する。
2. `package.py` と `verify_install.py` は残す。両者が使う配置先の表と解決は `skill_env.py` へ移す。
3. 同名 Skill の重複検出（`verify_install.py` の警告と、`skill_env.py` の探索）は、上書きで足りるため削除する。
4. 失う機能: リポジトリへの直接リンク（`--link`）、上書き前の退避、`--dry-run`、重複の警告。複数環境への導入は失わない（`-a` に環境を並べる）。
5. リポジトリへの直接リンクは、`ln -s` の1行を docs に残す。
6. Antigravity のユーザー全体の配置先は、`npx skills` では入らないため、手動コピー（`cp -R`）の手順を docs に残す。
7. `package.py` が作る OpenCode・Hermes 配布物の INSTALL.md は、`npx skills add <パス>` と手動コピーの2本にする。
8. 過去の検証記録（`docs/user-guide-validation.md`、`docs/opencode-hermes-checks.md`、`evals/`）は書き換えない。
9. 導入手順が変わるため、VERSION を上げてリリースする。

## 選択肢と機会費用

- **`install.py` を残す**: 配置先の細かい指定と退避を保てる。一方、約3200行の保守と、2つの導入手順の説明が続く。
- **配置系をすべて削除（`verify_install.py`、`package.py` の配布物生成を含む）**: 削減は最大。一方、CI と release.yml が使う配布物の生成と検証を作り直す必要がある。今回は見送る。
- **`install.py` だけ削除**: 孤立した `uninstall.py` が残るため採らない。

## 失うもの・未確認

- 上書き前の退避が無くなるため、上書きで失う内容は戻せない。
- `npx skills` の GitHub からの実インストール、`update`、Hermes のプロファイル指定は未確認。確認前は「確認済み」と書かない。
- `install.py` で入れた既存の複製は、`npx skills` では消えない。docs に、古い複製を消してから入れ直す注意を書く。
