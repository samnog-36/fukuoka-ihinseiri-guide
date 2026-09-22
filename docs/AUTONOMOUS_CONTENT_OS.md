# 自律コンテンツ・SEO運営OS

## 目的

福岡遺品整理ガイドを、記事量産型サイトではなく「一次情報・地域データ・検索実績を継続的に蓄積する専門メディア」として育てる。

主目標:

1. AdSenseポリシーとサイト品質を維持する
2. Search Consoleの実績を使い、伸びる可能性の高い既存記事を優先改善する
3. 福岡県・各自治体・国の一次情報を根拠として蓄積する
4. 将来の業者DB・見積送客・掲載課金へ拡張する
5. 運営手順とデータ資産を残し、M&A時に引き継ぎやすくする

## 自動運転フロー

毎日 05:10 JST 頃に GitHub Actions が起動する。

Search Console取得（設定済みの場合）
→ 全indexable記事を品質採点
→ 順位4〜20位、表示回数、CTR、記事品質を合わせて優先度算出
→ 最優先ページを1件だけ選択
→ AIがWeb調査
→ 一次情報を優先して本文を改善
→ 信頼性・HTML・AdSense品質Gate
→ PASS時だけ専用branchへcommit
→ main向けPull Request作成

新規記事の自動量産は初期設定では禁止している。
config/content_os.json の allow_scheduled_new_articles は false を維持する。

## 必要なGitHub設定

Repository Settings → Secrets and variables → Actions

Secrets:
- OPENAI_API_KEY
- GOOGLE_SERVICE_ACCOUNT_JSON（Search Consoleを自動取得する場合）

Variables:
- OPENAI_MODEL: 例 gpt-5.6-terra
- SEARCH_CONSOLE_SITE_URL: https://fukuoka-ihinseiri-guide.com/

Search Console用サービスアカウントには対象プロパティの閲覧権限だけを与える。

## 安全設計

AIは以下を禁止される。

- 架空の口コミ・体験談・専門家・監修者・業者・実績
- 根拠不明の統計、料金、割合、ランキング
- 地名だけ差し替えた記事量産
- AI生成を隠すためだけの文章偽装
- 品質Gateを通さずmainへ直接公開

記事改善時には、最低1つの優先一次情報が必要。
編集情報と公式確認先が失われた場合は自動停止する。

## データ資産

- data/source_registry.json: 一次情報の優先ソース
- data/municipalities.json: 福岡県60自治体の調査状態
- data/vendors.schema.json: 将来の業者DB定義
- docs/growth/search_console_latest.json: Search Console集計
- docs/growth/content-os-latest.json: 改善優先順位
- docs/growth/quality-gate.json: 品質検査結果

## 今後の拡張

自治体DBは、粗大ごみ、自己搬入、一般廃棄物、家電リサイクル、相談窓口、更新日、根拠URLを自治体ごとに持たせる。

業者DBは、許認可・対応地域・サービス・料金公開・最終確認日・広告掲載の有無を分離する。広告掲載の有無を検索順位や編集評価と混同しない。
