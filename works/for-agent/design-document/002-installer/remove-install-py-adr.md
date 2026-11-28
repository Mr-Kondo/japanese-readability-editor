---
status: accepted
date: 2026-11-10
decision-makers: User (approved recommendations Q1–Q6), Claude Code (measurement and implementation)
---

# Retire install.py and uninstall.py and standardize installation on `npx skills add`

## Context

Placing skills under `skills/*/SKILL.md` made them installable with `npx skills add` ([Issue #155 PR](https://github.com/Mr-Kondo/japanese-readability-editor/pull/155)). Meanwhile, `tools/install.py` (455 lines), `tools/uninstall.py` (140 lines), and their tests (865 lines) maintain their own destination table, OpenCode and Hermes destination resolution, backups, links, and other behavior. Two installation methods make the README and procedures cumbersome. Tracking: [Issue #156](https://github.com/Mr-Kondo/japanese-readability-editor/issues/156).

## Hypothesis and rollback criteria

- Hypothesis: `npx skills add` can replace the placement performed by `install.py` in every environment, leaving `install.py` as maintenance cost only.
- Falsification criteria: Before deletion, install into five environments (Codex, Claude Code, OpenCode, Hermes, Antigravity) under an isolated HOME. Check whether destinations match those used by `install.py`, whether `verify_install.py` passes both “matches the canonical source” and “bundled scripts work,” and whether a second install overwrites the first. Keep the procedure for any environment that does not pass.

## Observations (2026-11-10, macOS, skills 1.7.6, isolated HOME)

| Check                   | Result                                                                                                                                                                        |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Codex, OpenCode         | Installed under `~/.agents/skills/`, matching the shared destination used by `install.py`. OpenCode reads `.agents/skills/` (official documentation).                         |
| Claude Code             | With one environment, files are copied to `~/.claude/skills/`. With multiple environments, they are linked to the files under `~/.agents/skills/`.                            |
| Hermes                  | Linked to `~/.hermes/skills/`, matching the `install.py` default. `HERMES_HOME` and profile selection were not checked.                                                       |
| Antigravity IDE and CLI | For all users, installed under `~/.agents/skills/`. `install.py` placed them under `~/.gemini/config/skills/` and `~/.gemini/antigravity-cli/skills/`. **They do not match.** |
| Reinstall               | An item with the same name was overwritten (extra files added to it were also removed).                                                                                       |
| `remove`                | Worked.                                                                                                                                                                       |
| `verify_install.py`     | 0 errors and 0 warnings under both `~/.agents/skills/` and `~/.claude/skills/`.                                                                                               |

## Decision

1. Delete `tools/install.py`, `tools/uninstall.py`, `tests/test_install.py`, and `tests/test_uninstall.py`.
2. Keep `package.py` and `verify_install.py`. Move the destination table and resolution they use to `skill_env.py`.
3. Remove duplicate same-name Skill detection (the warning in `verify_install.py` and search in `skill_env.py`), because overwriting is sufficient.
4. Lost features: direct links to repositories (`--link`), backups before overwrite, `--dry-run`, and duplicate warnings. Installing to multiple environments remains possible (list environments with `-a`).
5. Keep the one-line `ln -s` procedure for direct links to repositories in the docs.
6. Because `npx skills` does not install to Antigravity's all-user destination, keep manual-copy instructions (`cp -R`) in the docs.
7. For OpenCode and Hermes distributions created by `package.py`, provide two procedures in INSTALL.md: `npx skills add <パス>` and manual copying.
8. Do not rewrite historical verification records (`docs/user-guide-validation.md`, `docs/opencode-hermes-checks.md`, or `evals/`).
9. Because installation procedures change, increment VERSION and release.

## Options and opportunity costs

- **Keep `install.py`**: Retains fine-grained destination selection and backups. However, about 3200 lines of maintenance and explanations for two installation procedures continue.
- **Delete all placement tooling, including `verify_install.py` and distribution generation in `package.py`**: Maximizes reduction. However, distribution generation and verification used by CI and `release.yml` would need to be rebuilt. Not adopted this time.
- **Delete only `install.py`**: Not adopted because the now-orphaned `uninstall.py` would remain.

## Lost capabilities and unchecked items

- Without backups before overwriting, overwritten content cannot be restored.
- Actual installation from GitHub with `npx skills`, `update`, and Hermes profile selection were not checked. Do not describe them as verified before checking.
- Existing copies installed with `install.py` are not removed by `npx skills`. The docs must tell users to remove old copies before reinstalling.
