# M&A引継ぎ・資産化チェック

このサイトは「記事ファイルの集合」ではなく、再現可能な運営システムとして売却できる状態を目指す。

## 毎月保存するKPI

- Organic users / sessions
- Search Console clicks / impressions / average position / CTR
- AdSense revenue / page RPM
- 問い合わせ件数
- 掲載事業者数と掲載収益（開始後）
- 送客数・成約数・送客収益（開始後）
- OpenAI API費
- その他インフラ費
- 人手で必要だった運営時間
- indexable記事数 / noindex記事数 / 301統合数

## 買い手へ移管可能にする資産

- GitHub repository
- Domain / DNS
- Hosting
- Search Console
- Google Analytics
- AdSense
- AI/API secretsの再設定手順
- 自治体一次情報DB
- 業者DB
- コンテンツ公開基準
- 自動運転Workflow
- 収益・費用・問い合わせの月次データ

## M&A前に減らす依存

- 外部サービス上の独自JavaScriptへの不要な依存
- 特定個人のローカルPCだけにあるファイル
- 手動でしか更新できないsitemap/search index
- 口頭でしか分からない運用ルール
- 根拠不明な記事データ

## 評価しやすい状態

買い手が確認できるように、月次で docs/growth または別の非公開管理基盤へKPIスナップショットを保存する。
記事数ではなく、自然検索流入、収益、問い合わせ、運営コスト、継続性を説明できる状態を優先する。
