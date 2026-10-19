# 国語の表記・用法の規則

`data/kokugo-rules.json` の規則を、分野ごとに一覧にする。この表は規則データから生成した。規則の中身(適用条件、例外と許容形、保護対象、修正例と保持例、機械検出できる範囲、文脈判断が必要な範囲)は、規則データを読む。出典の詳細は [kokugo-sources.md](kokugo-sources.md) にある。

適用設定の選び方と判定区分の意味は [kokugo-policy.md](kokugo-policy.md)、`official` の運用は [kokugo-official.md](kokugo-official.md) にある。

表の見方:

- 区分は、適用設定(general-tech、public-explanation、official)ごとに、規則データが決めている。`accepted_variant` は誤りではない。`error` は太字で示す。
- 区分の末尾の `※` は、その区分がこの skill の運用判断であり、公式資料の規定ではないことを示す(規則データの `basis: skill-policy`)。
- 規則 ID の末尾が示す分野は、ID の2番目の語である(KANJI、KANA、OKURI、GAIRAI、NUM、PUNCT、EXPR、IJIDOKUN、CONSIST、REF)。
- 『出典』の資料 ID は [kokugo-sources.md](kokugo-sources.md)。PDF の出典はページを添える。

## 漢字の使い方

- 字種(表外漢字)と音訓(表外音訓)は別に扱う。常用漢字表の字種だけを確認して、音訓まで確認済みとしない。この skill が音訓を確かめるのは、規則に登録した語だけである。
- 固有名詞(人名・地名)と専門用語・特殊用語は、常用漢字表と内閣訓令の対象外である。機械では識別できないので、表外漢字は error にせず、要確認にとどめる。
- 公用文では、副詞・連体詞は原則として漢字、接続詞は原則として仮名、補助的な用法は仮名で書く(内閣訓令 別紙1(2))。広く一般に向けた解説・広報等では、漢字を用いることになっている語も、仮名で書いたり振り仮名を使ったりしてよい(考え方 本文 Ⅰ-1)。
- 品詞が決まらない語(動詞の連用形+『て』になりうる語など)は、形態素解析を使わないので、確定した指摘にせず要確認に下げる。

| ID | 内容 | general-tech | public-explanation | official | 出典 |
|---|---|---|---|---|---|
| `KOKUGO-KANJI-001` | 常用漢字表にない字種(表外漢字)の使用 | accepted_variant | needs_context | needs_context | `NAIKAKU-JOYO-2010` 前書き 2, 3, 4, 5 (PDF p.1)<br>`NAIKAKU-KUNREI-2010` 別紙 1(1), 3(1)(2)(3) (PDF p.2, 5)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(1)ア・ウ (PDF p.20)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(2) (PDF pp.21-22) |
| `KOKUGO-KANJI-002` | 常用漢字表にない音訓の語(表外音訓) | accepted_variant | recommendation | recommendation | `BUNKA-GUIDE-2022` 解説 Ⅰ-1(2)ア(ア) 訓による語は平仮名で書く (PDF p.21)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(2)イ(ア) 同じ訓を持つ漢字を用いて書く (PDF p.21)<br>`NAIKAKU-KUNREI-2010` 別紙 1(1), 3 (PDF p.2, 5)<br>`NAIKAKU-JOYO-2010` 本表(音訓欄) (PDF pp.11-161) |
| `KOKUGO-KANJI-003` | 仮名で書く接続詞を漢字で書いている | accepted_variant※ | recommendation | recommendation | `NAIKAKU-KUNREI-2010` 別紙 1(2)オ (PDF pp.2-3)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(3)イ 接続詞 (PDF pp.23-24)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(3)エ 法令に倣い仮名で書く (PDF p.24) |
| `KOKUGO-KANJI-004` | 漢字で書く4つの接続詞を仮名で書いている | accepted_variant※ | accepted_variant | recommendation | `NAIKAKU-KUNREI-2010` 別紙 1(2)オ ただし書 次の4語 (PDF p.3)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(3)イ 〔漢字を使って書く接続詞〕 (PDF pp.23-24)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(3)オ (PDF p.24)<br>`BUNKA-GUIDE-2022` 本文 Ⅰ-1 ただし書 (PDF p.5) |
| `KOKUGO-KANJI-005` | 漢字で書く副詞・連体詞を仮名で書いている | accepted_variant※ | accepted_variant | recommendation | `NAIKAKU-KUNREI-2010` 別紙 1(2)イ 副詞及び連体詞 (PDF p.2)<br>`BUNKA-GUIDE-2022` 本文 Ⅰ-1 ただし書 (PDF p.5)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(3)オ (PDF p.24)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(3)イ(接続詞『さらに』) (PDF pp.23-24) |
| `KOKUGO-KANJI-006` | 仮名で書くことが基本の副詞を漢字で書いている | accepted_variant※ | recommendation | recommendation | `NAIKAKU-KUNREI-2010` 別紙 1(2)イ ただし書 (PDF p.2)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(3)ウ 副詞のうち仮名で書くもの (PDF p.24)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(3)ア いわゆる当て字や熟字訓 (PDF p.23) |
| `KOKUGO-KANJI-007` | 補助的な用法・形式的な用法で仮名にする語を漢字で書いている | accepted_variant※ | recommendation | recommendation | `NAIKAKU-KUNREI-2010` 別紙 1(2)カ・キ (PDF p.3)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(3)ア 助動詞・補助的な用法・形式名詞 (PDF p.23)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-1(3)ウ 動詞のうち仮名で書くもの・ある・ない (PDF p.24) |

## 仮名遣い(現代仮名遣い)

- 適用するのは現代文のうち口語体の文章である。原文の仮名遣いによる必要のあるもの、固有名詞などでこれによりがたいものは除かれる(前書き)。
- 『ぢ』『づ』で書くことも認められている語(いなづま、きづな など)は、許容形である。誤りとして報告しない。例示にない語(『少しづつ』など)は、告示の例示から断定せず、要確認にする。

| ID | 内容 | general-tech | public-explanation | official | 出典 |
|---|---|---|---|---|---|
| `KOKUGO-KANA-001` | 助詞『は』を『わ』と書いている | **error** | **error** | **error** | `NAIKAKU-GENDAIKANA-1986` 本文 第2 2 助詞の『は』<br>`NAIKAKU-GENDAIKANA-1986` 前書き |
| `KOKUGO-KANA-002` | 動詞『いう(言)』を『ゆう』と書いている | **error** | **error** | **error** | `NAIKAKU-GENDAIKANA-1986` 本文 第2 4 動詞の『いう(言)』<br>`NAIKAKU-GENDAIKANA-1986` 前書き |
| `KOKUGO-KANA-003` | 『ぢ』『づ』を用いる語を『じ』『ず』で書いている(またはその逆) | **error** | **error** | **error** | `NAIKAKU-GENDAIKANA-1986` 本文 第2 5(1)(2) 及び 注意 |
| `KOKUGO-KANA-004` | 『ぢ』『づ』で書くことも認められている語(許容形) | accepted_variant | accepted_variant | accepted_variant | `NAIKAKU-GENDAIKANA-1986` 本文 第2 5(2) なお書き |
| `KOKUGO-KANA-005` | 『づつ』(『ひとりづつ』以外)の適用範囲 | needs_context | needs_context | needs_context | `NAIKAKU-GENDAIKANA-1986` 本文 第2 5(2) なお書き(例に『ひとりずつ』) |
| `KOKUGO-KANA-006` | 歴史的仮名遣いの文字(ゐ・ゑ・ヰ・ヱ) | needs_context | needs_context | needs_context | `NAIKAKU-GENDAIKANA-1986` 前書き(原文の仮名遣い、固有名詞)<br>`NAIKAKU-GENDAIKANA-1986` 本文 第1(用いる仮名の一覧) |

## 送り仮名の付け方

- 本則・例外・許容を区別する。許容は、本則と並んで慣用として行われ、これによってよい形であり、誤りではない(見方及び使い方 三)。
- 公用文は、原則として通則1〜6の本則・例外、通則7、付表の語による。許容を適用してよいのは通則2・4・6である(内閣訓令 別紙2)。ただし、読み間違えるおそれのない複合の名詞186語は、送り仮名を省くものとする。動詞は本則に従う。
- 広く一般に向けた解説・広報等では、送り仮名を省かずに書くことができる(考え方 本文 Ⅰ-2)。
- 名詞か動詞の連用形かは形態素解析なしには決まらない。この skill は、直後が『が』『を』『の』のときだけ名詞と確定し、それ以外は要確認にする。

| ID | 内容 | general-tech | public-explanation | official | 出典 |
|---|---|---|---|---|---|
| `KOKUGO-OKURI-001` | 通則1の許容形(表わす、行なう など) | accepted_variant | recommendation | recommendation | `NAIKAKU-OKURIGANA-1973` 通則1 許容<br>`NAIKAKU-OKURIGANA-1973` 『本文』の見方及び使い方 三・五<br>`NAIKAKU-KUNREI-2010` 別紙 2(1), 2(2) (PDF pp.4-5)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-2ア (PDF p.25) |
| `KOKUGO-OKURI-002` | 通則2の許容形(終る、変る、起る など) | accepted_variant | recommendation | recommendation | `NAIKAKU-OKURIGANA-1973` 通則2 許容<br>`NAIKAKU-OKURIGANA-1973` 『本文』の見方及び使い方 五<br>`NAIKAKU-KUNREI-2010` 別紙 2(2) (PDF p.5)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-2ア (PDF p.25) |
| `KOKUGO-OKURI-003` | 公用文で送り仮名を省くと定められた186語を、省かずに書いている | accepted_variant | accepted_variant | **error** | `NAIKAKU-KUNREI-2010` 別紙 2(1) ただし書・2(2) (PDF pp.4-5)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-2イ(186語) (PDF p.25)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-2ウ (PDF p.25)<br>`NAIKAKU-OKURIGANA-1973` 通則6 許容<br>`NAIKAKU-OKURIGANA-1973` 通則7 |

## 外来語の表記

- 『外来語の表記』は、語形にゆれのあるものについて、語形をどちらかに決めようとはしていない。慣用が定まっているものはそれによる。分野によって異なる慣用が定まっている場合は、それぞれの慣用によって差し支えない(留意事項その1)。
- 語末の長音符号は、告示が『慣用に応じて省くことができる』とし、考え方が『長音符号を用いて書くのが原則』とする。記述が異なるので、適用設定で区分を分けた(IT 分野の『サーバ』は general-tech では許容形)。
- 固有名詞(人名、会社名、商品名)は、告示の対象外である。

| ID | 内容 | general-tech | public-explanation | official | 出典 |
|---|---|---|---|---|---|
| `KOKUGO-GAIRAI-001` | 外来語の語末の長音符号を省いた形(サーバ、ユーザ、カテゴリ など) | accepted_variant | recommendation | recommendation | `NAIKAKU-GAIRAI-1991` 留意事項その2 Ⅲ(撥音,促音,長音その他に関するもの) 3 注3<br>`NAIKAKU-GAIRAI-1991` 留意事項その1(原則的な事項)<br>`NAIKAKU-GAIRAI-1991` 前書き<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-3エ (PDF p.26)<br>`BUNKA-GUIDE-2022` 本文 Ⅰ-3 (PDF p.5) |
| `KOKUGO-GAIRAI-002` | 『ヴ』を用いた表記 | accepted_variant | recommendation | recommendation | `NAIKAKU-GAIRAI-1991` 留意事項その2 Ⅱ(第2表に示す仮名に関するもの) 7<br>`NAIKAKU-GAIRAI-1991` 前書き<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-3ウ (PDF p.26) |
| `KOKUGO-GAIRAI-003` | 第1表・第2表にない仮名の組合せ | accepted_variant | recommendation | recommendation | `NAIKAKU-GAIRAI-1991` 本文(『外来語の表記』に用いる仮名と符号の表)<br>`NAIKAKU-GAIRAI-1991` 留意事項その1(特別な音の書き表し方)<br>`BUNKA-GUIDE-2022` 本文 Ⅰ-3 (PDF p.5)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-3ア (PDF p.26) |

## 数字の使い方

- 検査するのは『○か所』『○か月』だけである。そのほかの数字の用法は未検査(KOKUGO-REF-004)。

| ID | 内容 | general-tech | public-explanation | official | 出典 |
|---|---|---|---|---|---|
| `KOKUGO-NUM-001` | 算用数字に付く『ヶ所』『カ月』などの表記 | accepted_variant※ | recommendation | recommendation | `BUNKA-GUIDE-2022` 解説 Ⅰ-4ケ (PDF p.28)<br>`BUNKA-GUIDE-2022` 本文 Ⅰ-4ケ (PDF p.5) |

## 符号の使い方

- 検査するのは、句点にピリオドを使う書き方だけである。『，』と『、』の混在は、許容される表記の混在として KOKUGO-CONSIST-001 で扱う。

| ID | 内容 | general-tech | public-explanation | official | 出典 |
|---|---|---|---|---|---|
| `KOKUGO-PUNCT-001` | 句点にピリオド『.』『．』を使っている | accepted_variant※ | recommendation | recommendation | `BUNKA-GUIDE-2022` 解説 Ⅰ-5(1)ア (PDF p.29)<br>`BUNKA-GUIDE-2022` 本文 Ⅰ-5(1)ア (PDF p.6) |

## 表現

- 考え方の表現に関する推奨は、一概に誤りとは言えないものを含む。recommendation にとどめ、error にしない。
- 『まず最初に』『従来から』『返事を返す』『排気ガス』『被害を被る』は、考え方が慣用や強調として一概に誤りとも言えないとする例なので、検出しない。

| ID | 内容 | general-tech | public-explanation | official | 出典 |
|---|---|---|---|---|---|
| `KOKUGO-EXPR-001` | 『～するべき』と『～すべき』で文を終える形 | accepted_variant※ | recommendation | recommendation | `BUNKA-GUIDE-2022` 解説 Ⅲ-1オ (PDF p.42)<br>`BUNKA-GUIDE-2022` 本文 Ⅲ-1オ (PDF p.9) |
| `KOKUGO-EXPR-002` | 意味が重複する表現(諸先生方、約20名くらい など) | accepted_variant※ | recommendation | recommendation | `BUNKA-GUIDE-2022` 解説 Ⅱ-5ウ(ア) 表現の重複に留意する (PDF p.38)<br>`BUNKA-GUIDE-2022` 本文 Ⅱ-5ウ (PDF p.8) |
| `KOKUGO-EXPR-003` | 解説・広報等の文末の『ございます』 | accepted_variant※ | recommendation | accepted_variant※ | `BUNKA-GUIDE-2022` 解説 Ⅱ-6ウ (PDF p.39)<br>`BUNKA-GUIDE-2022` 本文 Ⅱ-6ウ (PDF p.8) |

## 異字同訓

- 『異字同訓』の使い分け例は『一つの参考』であり、異なる使い分けを否定する趣旨ではなく、仮名で表記することも妨げない(前書き3)。常に要確認とし、正しい漢字の候補は示さない。
- 読みだけで使い分けを決めない。国語に関する世論調査の多数派・少数派だけで、正誤を決めない。語義と文脈で決める。
- 133項目のうち、技術文書や案内文で紛らわしさが問題になりやすい16項目だけを検査する。残りは未検査である。

| ID | 内容 | general-tech | public-explanation | official | 出典 |
|---|---|---|---|---|---|
| `KOKUGO-IJIDOKUN-001` | 異字同訓の漢字の使い分け(確認用) | accepted_variant | needs_context | needs_context | `BUNKA-IJIDOKUN-2014` 前書き3, 4 (PDF p.6)<br>`BUNKA-IJIDOKUN-2014` 本表 項目009, 017, 030, 032, 033, 041, 047, 057, 059, 084, 086, 090, 104, 105, 108, 117 (PDF pp.8-29)<br>`BUNKA-GUIDE-2022` 本文 Ⅱ-5ア(イ) (PDF p.8) |

## 許容される複数表記の混在

- この規則は、この skill の運用判断である。多数派かどうかは、許容される表記のあいだで選ぶときの判断材料にとどめ、明確な誤りを広げる理由にしない。
- 明示された表記基準と組織の用語集を先に確認する。用語集が表記を指定していれば、その表記を候補に示す。

| ID | 内容 | general-tech | public-explanation | official | 出典 |
|---|---|---|---|---|---|
| `KOKUGO-CONSIST-001` | 許容される複数の表記が、同じ文書の中で混在している (運用判断) | recommendation※ | recommendation※ | recommendation※ | `BUNKA-GUIDE-2022` 解説 Ⅰ-3ウ(第2表を用いる場合の統一) (PDF p.26)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-4エ(全角・半角の統一) (PDF p.27)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-5(1)ア(『、』と『，』の混在) (PDF p.29)<br>`NAIKAKU-GAIRAI-1991` 留意事項その1(語形にゆれのあるものについて、語形をどちらかに決めようとはしていない)<br>`NAIKAKU-OKURIGANA-1973` 『本文』の見方及び使い方 五(本則又は許容のいずれに従ってもよい) |

## 参照のみ(自動判定しない)

- 初期実装では、参照先の整理にとどめる。ここに挙げた項目の適否は、検査していない。

| ID | 内容 | 参照するとき | 未検査の範囲 | 出典 |
|---|---|---|---|---|
| `KOKUGO-REF-001` | 敬語の指針 | 敬語の誤用が疑われるとき、または相手や場面に応じた待遇表現が問題になるとき、答申の該当箇所を直接読む。 | 敬語の自動判定は行わない。敬語の適否はすべて未検査。 | `BUNKA-KEIGO-2007` 第2章 敬語の仕組み、第3章 敬語の具体的な使い方 (PDF 全82ページ)<br>`BUNKA-GUIDE-2022` 解説 Ⅱ-6ウ(敬語の使い方) (PDF p.39) |
| `KOKUGO-REF-002` | ローマ字のつづり方 | ローマ字で国語を書き表す箇所が問題になるとき、告示の本表と添え書きを直接読む。昭和29年の告示(旧版)を前提にしていないか注意する。 | ローマ字表記の自動判定は行わない。ローマ字の適否はすべて未検査。 | `NAIKAKU-ROMAJI-2025` 前書き、本表、添え書き、(付)対照表 (PDF 全7ページ)<br>`BUNKA-GUIDE-2022` 本文 Ⅰ-5(2)オ(日本人の姓名のローマ字表記) (PDF p.7) |
| `KOKUGO-REF-003` | 字体(通用字体、表外漢字字体表、字体・字形の指針) | 旧字体・異体字が混じる文書で、字体の統一が問題になるとき。 | 字体(旧字体、許容字体、IVS による異体字)の検査は行わない。字種が表外かどうかは KOKUGO-KANJI-001 で扱う。 | `BUNKA-GUIDE-2022` 解説 Ⅰ-1(1)イ (PDF p.20)<br>`NAIKAKU-JOYO-2010` (付)字体についての解説 (PDF pp.4-10) |
| `KOKUGO-REF-004` | 数字・符号の使い方(検査しない項目) | 公用文の数字・符号の細則を確認したいとき。 | 検査するのは『○か所』『○か月』、全角・半角数字の混在、読点『、』『，』の混在、句点のピリオドだけ。それ以外の数字・符号の用法は未検査。 | `BUNKA-GUIDE-2022` 解説 Ⅰ-4(数字の使い方) (PDF pp.27-28)<br>`BUNKA-GUIDE-2022` 解説 Ⅰ-5(符号の使い方) (PDF p.29) |
| `KOKUGO-REF-005` | 用語と文章(考え方 Ⅱ・Ⅲ) | 表記の検査より先に、構成と論理、文の長さ、主語と述語、二重否定を確認するとき。この skill の診断の順序と references/readability-rules.md を使う。 | 言い換えの適否、文体、構成の適否は自動判定しない。二重否定は measure.py --extras が拾う(別の仕組み)。 | `BUNKA-GUIDE-2022` 本文 Ⅱ, Ⅲ (PDF pp.7-10)<br>`BUNKA-GUIDE-2022` 解説 Ⅱ, Ⅲ (PDF pp.33-46)<br>`BUNKA-GUIDE-2022` 解説 Ⅲ-3ア(一文を短くする) (PDF p.44)<br>`NAIKAKU-NOTICE-2022` 本文(周知の依頼、昭和27年の依命通知の廃止) |
| `KOKUGO-REF-006` | 法令における漢字使用等について | 法令の文章を書く、または法令の引用の表記を確認するとき。 | 原資料は取得していない。内容を確認していないため、この skill は法令の表記を検査しない。 | `BUNKA-GUIDE-2022` 解説 Ⅰ-1(3) 関係資料 (PDF p.24)<br>`NAIKAKU-KUNREI-2010` 別紙 4(法令における取扱い) (PDF p.5) |

## 規則の読み方

各規則の `provenance` は、規則のどこまでが公式資料の規定かを示す。

- `primary-source`: 資料の規定そのもの。検出する語や形が、資料に書かれている。
- `primary-source-derived`: 資料の例示や原則を、この skill が活用形や条件へ広げたもの。広げた部分は各規則の `skill_decisions` に書いてある。
- `skill-policy`: この skill の運用判断。公式資料が定めていない確認を、判断材料として示す。error にはならない。

`error` を出せるのは、内閣告示または内閣訓令を根拠に挙げる規則だけである(`validate_kokugo_rules.py` が検査する)。建議・報告・答申(考え方、異字同訓、敬語の指針)と、この skill の運用判断は、recommendation か needs_context までにとどまる。
