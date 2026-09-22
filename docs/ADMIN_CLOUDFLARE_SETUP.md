# SAM Admin / Manus脱却 本番セットアップ

## 構成

- 公開サイト: Cloudflare Pages
- 動的API: Cloudflare Pages Functions
- DB: Cloudflare D1 binding name `DB`
- 管理画面: `https://fukuoka-ihinseiri-guide.com/samadminsetup`
- 管理認証: Cloudflare Access + Google IdP
- 許可メール: **samkojinmail@gmail.com のみ**
- SEO: Google Search Console service account
- AI履歴: GitHub main / Content Growth OS

## 必須Cloudflare設定

### 1. D1

D1 databaseを1つ作成し、Pages project `fukuoka-ihinseiri-guide` に binding `DB` で接続する。

マイグレーション:

```bash
npx wrangler d1 execute <DATABASE_NAME> --remote --file=migrations/0001_admin_core.sql
```

### 2. Pages environment variables / secrets

Productionに設定:

- `CF_ACCESS_TEAM_DOMAIN` = `https://<team>.cloudflareaccess.com`
- `CF_ACCESS_AUD` = Access application AUD tag
- `GOOGLE_SERVICE_ACCOUNT_JSON` = Search Console service account JSON（secret）
- `SEARCH_CONSOLE_SITE_URL` = `sc-domain:fukuoka-ihinseiri-guide.com`
- `RATE_LIMIT_SALT` = 十分長いランダム文字列
- `GITHUB_DASHBOARD_TOKEN` = 任意。未設定でも公開repoの範囲は取得可能

### 3. Cloudflare Access

Self-hosted application:

- Application path: `fukuoka-ihinseiri-guide.com/samadminsetup/*`
- Identity provider: Google
- Allow policy: Email = `samkojinmail@gmail.com` のみ
- 他のAllow/Bypassは作らない

コード側でもAccess JWTを再検証し、同じメールアドレス以外を403にする。

## Manusデータ移行

管理画面には以下のD1テーブルを再構築済み:

- inquiries
- inquiry_memos
- business_applications
- advertisements
- ad_events
- audit_logs

旧Manus/TiDBのデータを書き出したら、
`POST /samadminsetup/api/import` で管理者認証下から取り込める。
移行前後の件数を必ず照合する。

D1側のバックアップ:
`GET /samadminsetup/api/export`

## 公開API

- POST /api/inquiry
- POST /api/business
- GET/POST /api/business/setup/{token}
- GET /api/ad/serve
- POST /api/ad/track
- POST /api/ad/reveal
- GET /ad-widget.js

公開フォームAPIには入力検証とIPベースのD1 rate limitを入れている。

## 業者セットアップ

管理者が業者申込を承認すると、30日間有効なランダムトークンを生成し:

`https://fukuoka-ihinseiri-guide.com/business/setup/{token}`

を返す。トークンはDBに平文保存せずSHA-256 hashで保持する。

## 広告

既存の `.fkg-ad` 枠を維持し、同一ドメインの `/ad-widget.js` が:

1. ジャンル一致広告を取得
2. impression記録
3. ボタン押下時click記録
4. 電話/メールをAPIから開示
5. phone_reveal / email_reveal を分離記録

する。

## AI自動運転

毎日05:10 JST:
Search Console → 改善候補 → Editor AI → 独立Reviewer AI → 静的品質Gate →
PASSのみPR → main自動merge → Cloudflare Pages本番反映。

管理画面でAI変更履歴、Reviewer score、Search Console推移、main反映履歴を確認できる。

## Manus runtime切替

`.github/workflows/manus-runtime-cutover.yml` がmain反映時に一度実行され、
公開HTMLの旧Manus API / ad-widget URLを同一ドメインへ置換する。

切替完了後も旧Manus環境は、旧データ照合が終わるまで読み取り専用で残す。
