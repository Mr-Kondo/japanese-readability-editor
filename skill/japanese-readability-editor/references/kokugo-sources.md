# 国語の表記・用法の出典

この skill の国語の規則は、文化庁が公開する次の公式資料に基づく。規則の中身は `data/kokugo-rules.json` にあり、各規則が根拠として挙げる資料 ID と節・ページは、この文書の ID に対応する。

確認日は 2026-10-10 である。この日に、入口の公式ページから各資料へたどり、原本(PDF と HTML)を取得して本文を読んだ。検索結果の要約だけでは規則を実装していない。

## 公式資料の規定と、この skill の運用判断を区別する

- 公式資料の規定: 規則データの `provenance` が `primary-source`(資料の規定そのもの)か `primary-source-derived`(資料の例示や原則を、この skill が活用形や条件へ広げたもの)の部分。
- この skill の運用判断: `provenance` が `skill-policy` の規則と、各規則の `skill_decisions` に書いた部分。どの区分(error、recommendation など)にするか、品詞が決まらない語を要確認に下げるか、といった判断を含む。
- 文の長さ(30〜45字の目安、46字以上、段落は200字以上)や、20字未満の文が3文以上続く箇所は、この skill の運用上の目安であり、文化庁の基準ではない。

## 資料の性格

| 種別 | 資料 | 性格 |
|---|---|---|
| 内閣告示 | 常用漢字表、現代仮名遣い、送り仮名の付け方、外来語の表記、ローマ字のつづり方 | 一般の社会生活における目安・よりどころ。科学・技術・芸術等の専門分野や個々人の表記には及ばない(各告示の前書き) |
| 内閣訓令 | 公用文における漢字使用等について | 各行政機関が作成する公用文を対象にする。固有名詞は対象外で、専門用語・特殊用語では従わなくてもよい(別紙3) |
| 建議 | 公用文作成の考え方 | 政府内の公用文作成の手引。告示・訓令そのものではなく、その運用の考え方と推奨 |
| 報告・答申 | 「異字同訓」の漢字の使い分け例、敬語の指針 | 一つの参考。異なる使い分けを否定しない |
| 通知 | 「公用文作成の考え方」の周知について | 周知の依頼。規則を新たに定めるものではない |

## 資料一覧

| ID | 正式名称 | 発出主体 | 種別 | 告示・発出日 | この skill での役割 |
|---|---|---|---|---|---|
| `NAIKAKU-JOYO-2010` | 常用漢字表(平成22年内閣告示第2号) | 内閣総理大臣 | 内閣告示 | 2010-11-30 | 規則の根拠として使っている |
| `NAIKAKU-KUNREI-2010` | 公用文における漢字使用等について(平成22年内閣訓令第1号(別紙)) | 内閣総理大臣 | 内閣訓令 | 2010-11-30 | 規則の根拠として使っている |
| `NAIKAKU-GENDAIKANA-1986` | 現代仮名遣い(昭和61年内閣告示第1号) | 内閣総理大臣 | 内閣告示 | 1986-07-01 | 規則の根拠として使っている |
| `NAIKAKU-OKURIGANA-1973` | 送り仮名の付け方(昭和48年内閣告示第2号) | 内閣総理大臣 | 内閣告示 | 1973-06-18 | 規則の根拠として使っている |
| `NAIKAKU-GAIRAI-1991` | 外来語の表記(平成3年内閣告示第2号) | 内閣総理大臣 | 内閣告示 | 1991-06-28 | 規則の根拠として使っている |
| `NAIKAKU-ROMAJI-2025` | ローマ字のつづり方(令和7年内閣告示第4号) | 内閣総理大臣 | 内閣告示 | 2025-12-22 | 参照先として記録するだけ(自動判定しない) |
| `BUNKA-GUIDE-2022` | 公用文作成の考え方(建議)(令和4年1月7日 文化審議会建議(付: 解説)) | 文化審議会 | 建議 | 2022-01-07 | 規則の根拠として使っている |
| `NAIKAKU-NOTICE-2022` | 「公用文作成の考え方」の周知について(令和4年1月11日内閣文第1号) | 内閣官房長官 | 通知 | 2022-01-11 | 参照先として記録するだけ(自動判定しない) |
| `BUNKA-IJIDOKUN-2014` | 「異字同訓」の漢字の使い分け例(報告)(平成26年2月21日 文化審議会国語分科会報告) | 文化審議会国語分科会 | 報告 | 2014-02-21 | 規則の根拠として使っている |
| `BUNKA-KEIGO-2007` | 敬語の指針(答申)(平成19年2月2日 文化審議会答申) | 文化審議会 | 答申 | 2007-02-02 | 参照先として記録するだけ(自動判定しない) |

## 利用条件と出典の表示

文化庁のサイトのコンテンツは、[文部科学省ウェブサイト利用規約](https://www.mext.go.jp/b_menu/1351168.htm)に従って利用する。出典を記載すれば、編集・加工して利用できる(商用利用を含む)。加工した場合は、加工したことを記載する。

- 出典: 文化庁ホームページ(上の各資料の公式 URL)。
- 加工: `data/joyo-kanji.json` と `data/ijidokun.json` は、公式の PDF から字種・音訓・項目を機械的に取り出した派生データである。`data/kokugo-rules.json` の規則は、公式資料を読んでこの skill が作成した。いずれも文化庁が作成したものではなく、文化庁が内容を保証するものでもない。
- 規約の確認: コンテンツは出典を記載すれば自由に利用でき、編集・加工して利用する場合は加工したことを記載する。国が作成したように見せて公表してはならない。この規約のページは証明書の検証に失敗して直接取得できず、WebFetch による要約で確認した。

## 各資料の詳細

### `NAIKAKU-JOYO-2010` 常用漢字表

- 正式名称: 常用漢字表(平成22年内閣告示第2号)
- 発出主体: 内閣総理大臣
- 資料の種別: 内閣告示
- 告示・発出日: 2010-11-30
- 公式 URL: <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/kanji/index.html>
- 確認日: 2026-10-10(公式サイトから原本のバイト列を取得し、本文を読んで確認した)
- 性格: 一般の社会生活における漢字使用の目安を示す内閣告示。科学・技術・芸術等の専門分野や個々人の表記には及ばない。
- 適用範囲: 前書き1〜5: 法令・公用文書・新聞・雑誌・放送など一般の社会生活が対象。専門分野・個々人の表記に及ぼさない(2)。都道府県名の漢字とそれに準じる漢字を除き固有名詞を対象としない(3)。過去の著作や文書の漢字使用を否定しない(4)。運用では個々の事情に応じた適切な考慮の余地がある(5)。
- 現行であることの確認: 2026-10-10 に内閣告示・内閣訓令の一覧(naikaku/index.html、最終更新 2025-12-22)に掲載されていることを確認した。

取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。

| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |
|---|---|---|---|---|---|
| pdf | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/pdf/joyokanjihyo_20101130.pdf> | 3551021 | 164 | 2019-11-15 | `d9f28aeb4ce8250dbde07de20ac66cca71805ba09d94e4942c752dffa84d8d42` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/kanji/index.html> | 12468 | - | 2024-03-18 | `1e19637461b44577623d8c918daf73115ab65dfac6888306354cf7e3e9951e1c` |

### `NAIKAKU-KUNREI-2010` 公用文における漢字使用等について

- 正式名称: 公用文における漢字使用等について(平成22年内閣訓令第1号(別紙))
- 発出主体: 内閣総理大臣
- 資料の種別: 内閣訓令
- 告示・発出日: 2010-11-30
- 公式 URL: <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/sanko/koyobun/index.html>
- 確認日: 2026-10-10(公式サイトから原本のバイト列を取得し、本文を読んで確認した)
- 性格: 各行政機関が作成する公用文における漢字使用等を定める内閣訓令。常用漢字表の告示と同日に出された。
- 適用範囲: 別紙3: 1(漢字使用)と2(送り仮名)は固有名詞を対象としない(1)。専門用語・特殊用語を書き表す場合など特別な漢字使用等を必要とする場合は1と2によらなくてよい(2)。専門用語等で読みにくい場合は振り仮名を用いる等の配慮をする(3)。法令は別途、内閣法制局の通知による(4)。
- 現行であることの確認: 2026-10-10 に「公用文に関する諸通知」(最終更新 2024-03-18)に掲載されていることと、「公用文作成の考え方」(建議)の本文と解説(Ⅰ-1、Ⅰ-2)がこの訓令の運用を基準として挙げていることを確認した。

取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。

| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |
|---|---|---|---|---|---|
| pdf | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/sanko/koyobun/pdf/kunrei.pdf> | 154676 | 5 | 2019-11-15 | `688317a978e9a91ca0a2a213e6d6e4f137a92a3a741cca814114e062573572a1` |
| pdf | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/pdf/joyokanjihyobesi_20101130.pdf> | 109301 | 4 | 2019-11-15 | `c2c7dcaa6e1f91ef90bf0100b96c2e9eb52c26d500777e1c1bc411ee09450225` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/sanko/koyobun/index.html> | 11879 | - | 2024-03-18 | `5f4763c6638ab22d64d8224c681909a0cf643927d256a119e6f847c32861e84b` |

### `NAIKAKU-GENDAIKANA-1986` 現代仮名遣い

- 正式名称: 現代仮名遣い(昭和61年内閣告示第1号)
- 発出主体: 内閣総理大臣
- 資料の種別: 内閣告示
- 告示・発出日: 1986-07-01
- 公式 URL: <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gendaikana/index.html>
- 確認日: 2026-10-10(公式サイトから原本のバイト列を取得し、本文を読んで確認した)
- 性格: 一般の社会生活において現代の国語を書き表すための仮名遣いのよりどころを示す内閣告示。
- 適用範囲: 前書き: 主として現代文のうち口語体のものに適用。原文の仮名遣いによる必要のあるもの、固有名詞などでこれによりがたいものは除く。科学・技術・芸術等の専門分野や個々人の表記には及ばない。擬声・擬態、特殊な方言音、外来語・外来音は対象としない。
- 現行であることの確認: 2026-10-10 に内閣告示・内閣訓令の一覧に掲載されていることを確認した。

取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。

| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |
|---|---|---|---|---|---|
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gendaikana/maegaki.html> | 12351 | - | 2024-03-18 | `26b22540f112b5b07709289ae46c75f4c6223038bca283a10adbebaa334db07c` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gendaikana/honbun_dai1.html> | 13027 | - | 2024-03-18 | `1871be806ed13f115faef584a1d539454341c1da2d6ef752a05aa657b4e21292` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gendaikana/honbun_dai2.html> | 15047 | - | 2024-03-18 | `47ff123f735dfd0e2c6f1b9097a08de18fd94e928e59b56ee62464b39db096b1` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gendaikana/kunrei.html> | 11671 | - | 2024-03-18 | `16699ad4ef122d5ac19ef452b7969d4d60316e0d035f535b3b1e7d58694034b5` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gendaikana/index.html> | 11736 | - | 2026-05-14 | `e01c83d16b27b040f3e78bd827ea539b5f252263bfe0760994df1cb76ab88441` |

### `NAIKAKU-OKURIGANA-1973` 送り仮名の付け方

- 正式名称: 送り仮名の付け方(昭和48年内閣告示第2号)
- 発出主体: 内閣総理大臣
- 資料の種別: 内閣告示
- 告示・発出日: 1973-06-18
- 公式 URL: <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/index.html>
- 確認日: 2026-10-10(公式サイトから原本のバイト列を取得し、本文を読んで確認した)
- 性格: 一般の社会生活において「常用漢字表」の音訓によって現代の国語を書き表す場合の送り仮名の付け方のよりどころを示す内閣告示。本則・例外・許容を区別する。
- 適用範囲: 前書き一〜三: 法令・公用文書・新聞・雑誌・放送など一般の社会生活が対象。専門分野や個々人の表記には及ばない。漢字を記号的に用いたり表に記入したりする場合や、固有名詞を書き表す場合は対象としない。許容は、本則と並んで慣用として行われ、これによってよいもの(見方及び使い方 三、五)。
- 現行であることの確認: 2026-10-10 に内閣告示・内閣訓令の一覧に掲載されていることを確認した。

取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。

| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |
|---|---|---|---|---|---|
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/maegaki.html> | 11288 | - | 2024-03-18 | `9fce274abb44ffa13cc049a31b2fd75b5ac7207d5337d7a04871211340e294c1` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/mikata.html> | 13505 | - | 2024-03-18 | `019463635ad7784eb831561531695060559137bf88c73d5095c6d6b8f4411ec3` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/honbun01.html> | 12786 | - | 2024-03-18 | `ed8c2e317a386c95f79a70f0b0c2d1d250c466902be30b3808caac4aa6634484` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/honbun02.html> | 13338 | - | 2024-03-18 | `d72246784687c47c22e08dfdacb6f24b8e4735343b7291514af12b25388cba85` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/honbun03.html> | 11535 | - | 2024-03-18 | `7b66cdf9cda567a244bdc0166c8e3f26918cdc4dbf1af60a66af33cf562f6517` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/honbun04.html> | 12653 | - | 2024-03-18 | `3d3c85b1b16da7eca14c64dfc1e9cc46953830165a6847b67c508f1f0ee9a202` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/honbun05.html> | 11912 | - | 2024-03-18 | `5acd07e62258504b31ceaba45536501f1a4f68464185be5ddb125d2589fa8f9d` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/honbun06.html> | 13982 | - | 2024-03-18 | `7aacb986c10ccb8141849952d142c8cf5e6abd3a1432c96f9cf36361c133385a` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/honbun07.html> | 12391 | - | 2024-03-18 | `f919ea6ec580387cc602a3053cf7db3436daa5e0162a339882fa6b84b91d4af5` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/huhyo.html> | 11416 | - | 2024-03-18 | `c76e5612ba2c43cd6c0ff20e33b3b0590b4485ab7c1b0fd034f2ab9e186962b7` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/kunrei.html> | 11793 | - | 2024-03-18 | `76d9c9a098b0c1baf3b1877b37c2139ae62da80160f24e29e5c23105568479e5` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/okurikana/index.html> | 11838 | - | 2026-05-14 | `ce3333a98d1d8170dcd766f8ebbb3b76577a7a08ebdc2655a17d33a76665a1f4` |

### `NAIKAKU-GAIRAI-1991` 外来語の表記

- 正式名称: 外来語の表記(平成3年内閣告示第2号)
- 発出主体: 内閣総理大臣
- 資料の種別: 内閣告示
- 告示・発出日: 1991-06-28
- 公式 URL: <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/index.html>
- 確認日: 2026-10-10(公式サイトから原本のバイト列を取得し、本文を読んで確認した)
- 性格: 一般の社会生活において現代の国語を書き表すための「外来語の表記」のよりどころを示す内閣告示。語形にゆれのあるものについて、語形をどちらかに決めようとはしていない。
- 適用範囲: 前書き: 法令・公用文書・新聞・雑誌・放送など一般の社会生活が対象。専門分野や個々人の表記には及ばない。固有名詞など(人名、会社名、商品名等)でこれによりがたいものには及ぼさない。過去に行われた様々な表記を否定しない。
- 現行であることの確認: 2026-10-10 に内閣告示・内閣訓令の一覧に掲載されていることを確認した。

取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。

| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |
|---|---|---|---|---|---|
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/maegaki.html> | 11673 | - | 2024-03-18 | `d5212c726958633f7664a2d0754c8004044fc4180015a82dc764a0571f4030ef` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/honbun01.html> | 11430 | - | 2026-05-15 | `e98da6c7756a6c7439659ce24b4d2462a40e4af8f126d36bfe0c9f4d17acfaf0` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/honbun02.html> | 11871 | - | 2024-03-18 | `c60b1c17785d30a76a61be03f318ee65602e82748866a58ee172c16ae7bdc787` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/honbun03.html> | 11056 | - | 2025-08-18 | `65434f79acb7bf263e17c20fe38eb6a34f7d9dd8a980b66d3a751e7634485eb8` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/honbun04.html> | 13257 | - | 2025-08-18 | `f176e06dc066eb38bdee6298e1875be57eb98eb56c34f9f6bb66707bb8e9edc5` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/honbun05.html> | 15297 | - | 2024-03-18 | `40751c1f4185f9ce6f3ddca2c0da8a5ac203933c94b9039a04c16350dd7bcbbe` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/honbun06.html> | 14321 | - | 2024-03-18 | `26fbcc6ded1c4af8b358793be18649fbc9955dad7127c910dad4fb03f9276d7e` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/kunrei.html> | 11585 | - | 2024-03-18 | `efa800799294dab57e968903606616c49618a39f7d081da61dd79aacf29c8280` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/gairai/index.html> | 12155 | - | 2026-05-14 | `7f6ef43bf1755eca254f930f8e462edefd78cb99a07bbe595e2338ccdd6d38a9` |

### `NAIKAKU-ROMAJI-2025` ローマ字のつづり方

- 正式名称: ローマ字のつづり方(令和7年内閣告示第4号)
- 発出主体: 内閣総理大臣
- 資料の種別: 内閣告示
- 告示・発出日: 2025-12-22
- 公式 URL: <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/roma/index2.html>
- 確認日: 2026-10-10(公式サイトから原本のバイト列を取得し、本文を読んで確認した)
- 性格: 一般の社会生活において現代の国語をローマ字で書き表す場合のよりどころを示す内閣告示。昭和29年内閣告示第1号を廃止して定められた。
- 適用範囲: 前書き1〜6: 法令・公用文書・新聞・雑誌・放送など一般の社会生活が対象。専門分野や個々人の表記には及ばない。過去のつづり方を否定しない。本表以外のつづり方にも意義や用途がある。
- 現行であることの確認: 2026-10-10 に内閣告示・内閣訓令の一覧(最終更新 2025-12-22)に掲載されていることを確認した。この版が昭和29年の告示に代わる現行の告示である。

取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。

| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |
|---|---|---|---|---|---|
| pdf | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/pdf/94303201_01.pdf> | 615641 | 7 | 2025-12-22 | `8eade8ea202ed69bac25b779028360b25702513d6ada6e433059dc73ce0e0077` |
| html | <https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/roma/index2.html> | 12168 | - | 2025-12-22 | `42e9edad70b9ed618c6c6de42a27ce5fc277135420d929613c7054f789c33194` |

### `BUNKA-GUIDE-2022` 公用文作成の考え方(建議)

- 正式名称: 公用文作成の考え方(建議)(令和4年1月7日 文化審議会建議(付: 解説))
- 発出主体: 文化審議会
- 資料の種別: 建議
- 告示・発出日: 2022-01-07
- 公式 URL: <https://www.bunka.go.jp/seisaku/bunkashingikai/kokugo/hokoku/93650001_01.html>
- 確認日: 2026-10-10(公式サイトから原本のバイト列を取得し、本文を読んで確認した)
- 性格: 政府内における公用文作成の手引として活用されることを目指した建議。内閣告示・内閣訓令そのものではなく、それらの運用の考え方と、表記・用語・文章の推奨をまとめたもの。
- 適用範囲: 本文 基本的な考え方 1(2): 公用文の表記は原則として法令と一致させる。法令に準ずる告示・通知等は公用文表記の原則に従う。議事録・報道発表資料・白書などは原則に基づきつつ読み手に合わせて工夫する。広く一般に向けた解説・広報等は、特別な知識を持たない人にとっての読みやすさを優先して書き表し方を工夫する。
- 現行であることの確認: 2026-10-10 に文化審議会国語分科会の報告・答申等のページ(最終更新 2024-07-10)に掲載されていることと、内閣官房長官通知(NAIKAKU-NOTICE-2022)で政府内に周知されていることを確認した。

取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。

| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |
|---|---|---|---|---|---|
| pdf | <https://www.bunka.go.jp/seisaku/bunkashingikai/kokugo/hokoku/pdf/93651301_01.pdf> | 2257110 | 63 | 2022-08-22 | `47ad41d2b9ed689215b36aef6656f1d250cb872a74c3cb44b6174cfc4746a8cf` |
| html | <https://www.bunka.go.jp/seisaku/bunkashingikai/kokugo/hokoku/93650001_01.html> | 18619 | - | 2024-07-10 | `158a14110fe8b30287fcf4fd884fef5c8bfbff31aa85fccd0117c16e0cf3e727` |

### `NAIKAKU-NOTICE-2022` 「公用文作成の考え方」の周知について

- 正式名称: 「公用文作成の考え方」の周知について(令和4年1月11日内閣文第1号)
- 発出主体: 内閣官房長官
- 資料の種別: 通知
- 告示・発出日: 2022-01-11
- 公式 URL: <https://www.bunka.go.jp/koho_hodo_oshirase/hodohappyo/93651302.html>
- 確認日: 2026-10-10(公式サイトから原本のバイト列を取得し、本文を読んで確認した)
- 性格: 「公用文作成の考え方」(建議)を貴管下職員へ周知するよう各国務大臣に求めた内閣官房長官通知。昭和27年の依命通知「公用文改善の趣旨徹底について」を同日付けで廃止した。
- 適用範囲: 周知を求める通知であり、表記の規則を新たに定めるものではない。
- 現行であることの確認: 2026-10-10 に公用文に関する諸通知のページからのリンク先として確認した。

取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。

| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |
|---|---|---|---|---|---|
| html | <https://www.bunka.go.jp/koho_hodo_oshirase/hodohappyo/93651302.html> | 18284 | - | 2024-07-10 | `99fe0e66eefbe3937b2ac7f8c35f5fa0ccf782e4e41214a08d1024455faa15dc` |

### `BUNKA-IJIDOKUN-2014` 「異字同訓」の漢字の使い分け例(報告)

- 正式名称: 「異字同訓」の漢字の使い分け例(報告)(平成26年2月21日 文化審議会国語分科会報告)
- 発出主体: 文化審議会国語分科会
- 資料の種別: 報告
- 告示・発出日: 2014-02-21
- 公式 URL: <https://www.bunka.go.jp/seisaku/bunkashingikai/kokugo/hokoku/pdf/ijidokun_140221.pdf>
- 確認日: 2026-10-10(公式サイトから原本のバイト列を取得し、本文を読んで確認した)
- 性格: 常用漢字表の同訓の漢字について、使い分けの大体を簡単な説明と用例で示した報告。一つの参考であり、異なる使い分けを否定する趣旨ではなく、仮名で表記することも妨げない(前書き3)。
- 適用範囲: 前書き3, 4: 年代差・個人差・分野ごとの表記習慣の違いがある。常用漢字1字の訓同士でない場合(偏る/片寄る、独り/一人など)は取り上げていない。
- 現行であることの確認: 2026-10-10 に「公用文作成の考え方」の関係資料として参照されていることを確認した(解説 Ⅱ-5)。

取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。

| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |
|---|---|---|---|---|---|
| pdf | <https://www.bunka.go.jp/seisaku/bunkashingikai/kokugo/hokoku/pdf/ijidokun_140221.pdf> | 924697 | 53 | 2019-11-15 | `57ad033db96d0d035992c5cc0ffd2703db16ef2e84ccdbdff92d6851c7c0d3fb` |

### `BUNKA-KEIGO-2007` 敬語の指針(答申)

- 正式名称: 敬語の指針(答申)(平成19年2月2日 文化審議会答申)
- 発出主体: 文化審議会
- 資料の種別: 答申
- 告示・発出日: 2007-02-02
- 公式 URL: <https://www.bunka.go.jp/seisaku/bunkashingikai/kokugo/hokoku/pdf/keigo_tosin.pdf>
- 確認日: 2026-10-10(公式サイトから原本のバイト列を取得し、本文を読んで確認した)
- 性格: 敬語の仕組みと使い方についての答申。個々の表記の正誤を定める資料ではない。
- 適用範囲: 参照先として記録するのみ。この skill は敬語の自動判定を行わない。
- 現行であることの確認: 2026-10-10 に文化審議会国語分科会の報告・答申等のページに掲載されていることを確認した。

取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。

| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |
|---|---|---|---|---|---|
| pdf | <https://www.bunka.go.jp/seisaku/bunkashingikai/kokugo/hokoku/pdf/keigo_tosin.pdf> | 613704 | 82 | 2019-11-15 | `3a567c6d85e990e0f90f0698c1403ba5826c7c6f9e7e50c93ea5d4da9336882d` |

## 再確認の方法

公式資料が改定されていないかは、次のコマンドで確かめる。ネットワークを使うので、日常の検査(`check_kokugo.py`)とは別に、規則を更新するときだけ実行する。リポジトリの `tools/` にあり、配布物には入らない。

```bash
python3 tools/update_kokugo_sources.py verify
```

SHA-256 が記録と一致しない資料は、公式側で内容が変わった可能性がある。規則の根拠(節・ページ)を読み直してから、`data/kokugo-sources.json` と規則データを更新する。HTML のページは、サイトの見た目の更新でも変わるので、不一致は本文を読んで判断する。

## 取得できなかった資料

- 「法令における漢字使用等について」(内閣法制局長官決定)。「公用文作成の考え方」と内閣訓令から参照されているが、原資料は取得していない。この skill は法令の表記を検査しない。
- 「表外漢字字体表」(平成12年国語審議会答申)と「常用漢字表の字体・字形に関する指針」(平成28年文化審議会国語分科会報告)。取得しておらず、字体の検査は行わない。
- 文部科学省ウェブサイト利用規約のページは、証明書の検証に失敗して直接取得できなかった。要約でのみ確認した。
