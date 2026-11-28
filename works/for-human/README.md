# works/ の案内（人間向け）

`works/` には、設計の思想と開発の記録を置きます。ソースコードを読まなくても、全体の大枠を理解できるようにするための資料です。

## フォルダの意味

- `for-agent/`: 正本。英語で書き、AI エージェントが読んで作り直せる粒度で書きます。
  - `checklist/`: 実装前の作業チェックリスト。
  - `requirement-definition-document/`: 誰に何が必要か、制約、ハード・ソフトの選定。
  - `implementation-plan/`: 実装の計画。
  - `design-document/`: 設計、仕様、設計判断記録（ADR）。番号付きフォルダごとに、コンポーネントを分けます。
- `for-human/`（このフォルダ）: `for-agent/` から作る日本語の要約。食い違うときは `for-agent/` を優先します。

`for-human/` の要約は、まだ作っていません。`for-agent/` の各文書を読んでください。
