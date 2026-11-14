#!/bin/sh
# Markdown の整形の確認 → 文法 → 日本語の校正を、この順にすべて実行する。自動修正はしない。
# 使い方: npm run lint:md -- <Markdown ファイル>...
set -u
[ "$#" -gt 0 ] || { echo "使い方: npm run lint:md -- <Markdown ファイル>..." >&2; exit 2; }
status=0
echo "== Prettier(整形の確認)"
npx --no-install prettier --check "$@" || status=1
echo "== markdownlint-cli2(文法)"
npx --no-install markdownlint-cli2 "$@" || status=1
echo "== textlint(日本語の校正)"
npx --no-install textlint "$@" || status=1
exit $status
