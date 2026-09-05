from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_all(text: str, replacements: dict[str, str]) -> str:
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


def update(path: Path, replacements: dict[str, str]) -> None:
    text = path.read_text(encoding="utf-8")
    updated = replace_all(text, replacements)
    if updated != text:
        path.write_text(updated, encoding="utf-8")


area = ROOT / "area/index.html"
update(area, {
    "福岡県の地域別遺品整理情報｜市区町村ごとの費用と業者一覧": "福岡県の地域別遺品整理情報｜自治体ルールと業者選びの確認ポイント",
    "福岡市・北九州市・久留米市など福岡県内の地域別遺品整理情報。各エリアの費用相場、対応業者、自治体サービスを網羅的に紹介。": "福岡市・北九州市・久留米市など福岡県内の地域別遺品整理情報。自治体のごみルール、搬出条件、業者選びで確認したいポイントを地域別に整理。",
    "福岡県全域の遺品整理業者情報と費用相場を地域別にご案内。": "福岡県内の自治体ルールと遺品整理で確認したいポイントを地域別にご案内。",
    "お住まいの地域を選んで、対応業者や費用相場をご確認ください。<br>各地域の特徴や注意点もまとめています。": "お住まいの地域を選んで、自治体のごみルールや業者選びの確認ポイントをご確認ください。<br>各地域の特徴や注意点もまとめています。",
    "福岡市は県内で最も遺品整理の需要が高いエリアです。マンション・集合住宅が多く、エレベーターの有無や駐車スペースによって費用が変動します。": "福岡市ではマンション・集合住宅も多く、搬出時はエレベーターの有無、管理規約、駐車位置などを確認しておくと見積条件をそろえやすくなります。",
    '<strong style="color: var(--text-main);">費用相場：</strong>1K〜1LDKで3万〜12万円、2LDK〜3LDKで15万〜35万円': '<strong style="color: var(--text-main);">費用の確認：</strong>物量・搬出条件・処分品・追加作業をそろえて複数社の見積もりを比較してください。',
    "北九州市は一戸建てが多いエリアです。福岡市に比べて費用がやや抑えめの傾向があります。高齢化率が高く、遺品整理・特殊清掃の需要が増加しています。": "北九州市では区や住宅形態によって搬出条件が異なります。粗大ごみや引越ごみの扱いは北九州市の最新案内を確認してください。",
    '<strong style="color: var(--text-main);">費用相場：</strong>1K〜1LDKで3万〜10万円、2LDK〜3LDKで12万〜30万円': '<strong style="color: var(--text-main);">費用の確認：</strong>間取りだけで判断せず、荷物量・階段・駐車条件などを同じ条件で比較してください。',
    "郊外エリアでは一戸建て・農家の遺品整理が多く、物量が多い傾向があります。出張費が加算される場合があるため、地元密着の業者を選ぶのがポイントです。": "市町村ごとに粗大ごみの申込方法、持ち込み先、収集できない品目が異なります。作業前に対象自治体の最新情報を確認してください。",
    '<strong style="color: var(--text-main);">費用相場：</strong>1K〜1LDKで3万〜8万円、3LDK以上で15万〜40万円': '<strong style="color: var(--text-main);">費用の確認：</strong>地域名よりも実際の物量・搬出条件・作業範囲を見積書で確認してください。',
    "福岡県の遺品整理 費用相場の目安": "福岡県で見積もり時に確認したい条件",
    ">費用相場</th>": ">料金の確認</th>",
    ">作業時間目安</th>": ">見積もりで確認する点</th>",
    ">3万〜8万円</td><td style=": ">個別見積もり</td><td style=",
    ">7万〜15万円</td><td style=": ">個別見積もり</td><td style=",
    ">12万〜25万円</td><td style=": ">個別見積もり</td><td style=",
    ">15万〜35万円</td><td style=": ">個別見積もり</td><td style=",
    ">20万〜60万円</td><td style=": ">個別見積もり</td><td style=",
    ">2〜3時間</td></tr>": ">物量・搬出条件を確認</td></tr>",
    ">3〜5時間</td></tr>": ">物量・搬出条件を確認</td></tr>",
    ">4〜8時間</td></tr>": ">物量・搬出条件を確認</td></tr>",
    ">6〜10時間</td></tr>": ">物量・搬出条件を確認</td></tr>",
    ">1〜2日</td></tr>": ">物量・搬出条件を確認</td></tr>",
    "※上記は目安です。荷物の量、階数、エレベーターの有無、特殊清掃の必要性などで変動します。": "※料金は間取りだけでは決まりません。荷物量、搬出条件、処分品、作業範囲などを同じ条件で複数社へ伝えて比較してください。",
    "福岡県内の信頼できる遺品整理業者をご紹介します。まずはお気軽にご相談ください。": "遺品整理業者を選ぶ際の確認ポイントをご案内します。掲載・広告の扱いは編集方針で公開しています。",
    "/blog/area/article-20260706-kitakyushu-guide.html": "/blog/area/article-20260714-kitakyushu-ihinseiri-guide.html",
    "/blog/area/article-20260706-kurume.html": "/blog/area/article-20260713-kurume-ogori-tosu.html",
    "/blog/area/article-20260706-minami-ku.html": "/blog/area/article-20260719-minami-jonan-ku-guide.html",
    "/blog/area/article-20260707-higashi-ku-guide.html": "/blog/area/article-20260805-fukuokashi-hakata-higashi-chuo.html",
    "/blog/area/article-20260708-hakata-ku-guide.html": "/blog/area/article-20260805-fukuokashi-hakata-higashi-chuo.html",
    "/blog/area/article-20260711-chikushino-onojo-kasuga.html": "/blog/area/article-20260722-chikushino-onojo-kasuga-guide.html",
})

cost = ROOT / "cost/index.html"
update(cost, {
    "福岡の遺品整理費用相場｜間取り別料金と安くする5つのコツ": "福岡の遺品整理費用｜見積条件と比較ポイント",
    "福岡県の遺品整理費用を間取り別に解説。1K〜4LDKの料金相場、追加費用の内訳、費用を抑える5つのコツを紹介。複数業者の見積もり比較で最安値を実現。": "福岡で遺品整理の費用を確認するときに、物量、搬出条件、処分品、追加作業、買取など金額が変わる条件と見積もり比較のポイントを整理。",
    "福岡県の遺品整理 費用相場一覧｜間取り別・作業内容別": "福岡県の遺品整理費用｜見積条件・作業内容別の確認ポイント",
    "福岡県の遺品整理費用を間取り別に一覧で紹介。": "福岡県の遺品整理で費用が変わる条件と見積もり時の確認項目を紹介。",
    "福岡県の遺品整理 費用相場一覧": "福岡県の遺品整理 費用の確認ポイント",
    "間取り別に福岡県内の遺品整理費用の目安をまとめています。<br>正確な費用は現地見積もりで確認しましょう。": "現在の間取りだけでなく、物量・搬出条件・処分品・追加作業を確認しましょう。<br>同じ条件で複数社の見積もりを比較するのが基本です。",
    "間取り別 費用相場一覧（福岡県）": "間取り別 見積もり確認表（福岡県）",
    ">費用相場</th>": ">料金の確認</th>",
    ">作業時間</th>": ">確認ポイント</th>",
    ">作業人数</th>": ">見積条件</th>",
    ">3万〜8万円</td><td style=": ">個別見積もり</td><td style=",
    ">7万〜15万円</td><td style=": ">個別見積もり</td><td style=",
    ">12万〜25万円</td><td style=": ">個別見積もり</td><td style=",
    ">15万〜35万円</td><td style=": ">個別見積もり</td><td style=",
    ">20万〜60万円</td><td style=": ">個別見積もり</td><td style=",
    ">1〜3時間</td><td style=": ">物量・搬出経路</td><td style=",
    ">2〜5時間</td><td style=": ">物量・搬出経路</td><td style=",
    ">3〜7時間</td><td style=": ">物量・搬出経路</td><td style=",
    ">5〜10時間</td><td style=": ">物量・搬出経路</td><td style=",
    ">1〜2日</td><td style=": ">物量・搬出経路</td><td style=",
    ">1〜2名</td></tr>": ">処分品・追加作業</td></tr>",
    ">2〜3名</td></tr>": ">処分品・追加作業</td></tr>",
    ">3〜4名</td></tr>": ">処分品・追加作業</td></tr>",
    ">4〜6名</td></tr>": ">処分品・追加作業</td></tr>",
    ">5〜8名</td></tr>": ">処分品・追加作業</td></tr>",
    "上記は目安です。荷物の量、階数（エレベーターの有無）、作業日（土日祝は割増の場合あり）、特殊な廃棄物の有無などによって変動します。正確な費用は必ず現地見積もりで確認してください。": "料金は間取りだけでは決まりません。荷物量、搬出条件、処分品、作業範囲、追加料金条件を同じ条件で複数社へ伝えて比較してください。",
    "同じ間取りでも荷物が多いほど高くなります。事前に自分で処分できるものは処分しておくと節約に。": "同じ間取りでも物量で作業量が変わります。見積もり時に収納・物置を含む対象範囲を伝えましょう。",
    "買取可能な品物があれば費用から差し引かれます。貴金属・ブランド品は要チェック。": "買取を希望する場合は、査定額を作業費から差し引くのか別精算なのか確認しましょう。",
    "土日祝日や繁忙期（3月・9月）は割増料金になる業者もあります。": "日程による料金条件がある場合は、契約前に見積書へ明記されているか確認しましょう。",
    "正確な費用を知りたい方へ": "見積もりを比較したい方へ",
    "実際の費用は現地見積もりで確認するのが確実です。複数社の見積もりを無料で手配いたします。": "実際の費用は作業条件で変わります。複数社へ同じ条件を伝え、作業範囲と追加料金条件を比較してください。",
    "無料見積もりを依頼する": "見積もりの確認ポイントを見る",
    "/blog/cost/article-20260706-cost-saving-tips.html": "/blog/cost/article-20260707-cost-yasuku-suru.html",
    "/blog/cost/article-20260804-hiyou-yasuku-suru-houhou.html": "/blog/cost/article-20260707-cost-yasuku-suru.html",
    "/blog/cost/article-20260712-ihinseiri-hiyo-yasuku.html": "/blog/cost/article-20260707-cost-yasuku-suru.html",
    "/blog/cost/article-20260706-mitsumori-hikaku.html": "/blog/cost/article-20260803-mitsumorisho-mikata.html",
})

print("layout-preserving AdSense cleanup complete")
