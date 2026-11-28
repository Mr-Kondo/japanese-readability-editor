# works/ の案内（人間向け）

`works/` には、設計の思想と開発の記録を置きます。ソースコードを読まなくても、全体の大枠を理解できるようにするための資料です。

## フォルダの意味

- `for-agent/`: 正本。英語で書き、AI エージェントが読んで作り直せる粒度で書く。
  - `checklist/`: 実装前の作業チェックリスト。
  - `requirement-definition-document/`: 誰に何が必要か、制約、ハード・ソフトの選定。
  - `implementation-plan/`: 実装の計画。
  - `design-document/`: 設計、仕様、設計判断記録（ADR）。番号付きフォルダごとに、コンポーネントを分ける。
- `for-human/`（このフォルダ）: `for-agent/` から作る日本語の要約。食い違うときは `for-agent/` を優先する。

## 索引

各フォルダの `index.md` から、要約を探せます。

- [要求定義書の索引](requirement-definition-document/index.md): 人手評価ツールの選定と、評価の方法。
- [実装計画の索引](implementation-plan/index.md): 評価ツールの改良、公開文書の準備、具体化の例の修正。
- [設計文書の索引](design-document/index.md): 番号付きのコンポーネントと、設計判断記録（ADR）の一覧。

`checklist/` と `requirements-document/` には、人間向けの要約を作りません。
