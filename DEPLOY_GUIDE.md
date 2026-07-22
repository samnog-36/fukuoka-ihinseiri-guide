# 福岡遺品整理ガイド - デプロイ手順書

このドキュメントでは、本サイトを公開するための手順を説明します。

---

## 前提条件

- GitHubアカウント（作成済み）
- 独自ドメイン（例：fukuoka-ihinseiri-guide.com）

---

## 方法1：Cloudflare Pages（推奨・無料）

### ステップ1：GitHubにリポジトリを作成

1. GitHubにログイン
2. 右上の「+」ボタン → 「New repository」をクリック
3. Repository name: `fukuoka-ihinseiri-guide`
4. Public を選択
5. 「Create repository」をクリック

### ステップ2：ファイルをアップロード

GitHubのリポジトリページで：
1. 「uploading an existing file」リンクをクリック
2. サイトのファイル一式をドラッグ＆ドロップ
3. 「Commit changes」をクリック

### ステップ3：Cloudflare Pagesに接続

1. [Cloudflare](https://dash.cloudflare.com/) にアカウント作成・ログイン
2. 左メニューの「Pages」をクリック
3. 「Create a project」→「Connect to Git」
4. GitHubアカウントを連携し、`fukuoka-ihinseiri-guide` リポジトリを選択
5. ビルド設定：
   - Framework preset: `None`
   - Build command: （空欄のまま）
   - Build output directory: `/`（ルート）
6. 「Save and Deploy」をクリック

### ステップ4：独自ドメインを設定

1. Cloudflare Pagesのプロジェクト設定 → 「Custom domains」
2. 「Set up a custom domain」をクリック
3. ドメイン名を入力（例：fukuoka-ihinseiri-guide.com）
4. 表示されるDNS設定をドメイン管理画面（ムームードメイン等）で設定

---

## 方法2：Netlify（代替・無料）

1. [Netlify](https://www.netlify.com/) にアカウント作成
2. 「Add new site」→「Import an existing project」
3. GitHubリポジトリを選択
4. デプロイ設定はデフォルトのままでOK
5. カスタムドメインを設定

---

## 記事を追加する方法

### Manusに依頼する場合

「○○のテーマで3000字以上の記事を書いて、サイトに追加して」と依頼するだけ。ManusがHTMLファイルを生成し、GitHubにpushします。

### 手動で追加する場合

1. 既存の記事HTMLファイル（例：`/guide/tokushu-seisou.html`）をコピー
2. ファイル名を変更（例：`/guide/new-article.html`）
3. `<h1>`タグ内のタイトルを変更
4. `<div class="article-body">` 内の本文を書き換え
5. `<meta name="description">` を更新
6. GitHubにアップロード → 自動デプロイ

---

## サイト売却時の引き継ぎ

買い手に渡すもの：
1. **GitHubリポジトリのオーナー権限**（Settings → Transfer ownership）
2. **ドメインの名義変更**（ドメイン管理会社の移管手続き）
3. **Cloudflare Pagesのプロジェクト**（買い手が自分のアカウントで再接続）
4. **このREADME**（運用方法の説明として）

---

## ファイル構成

```
fukuoka-ihinseiri-guide/
├── index.html              ← トップページ
├── css/
│   └── style.css           ← デザイン（全ページ共通）
├── area/
│   └── index.html          ← 地域別一覧
├── cost/
│   ├── index.html          ← 費用相場一覧
│   └── 3ldk.html           ← 3LDK費用記事
├── guide/
│   ├── index.html          ← ガイド一覧
│   ├── how-to-choose.html  ← 業者選びガイド
│   ├── tokushu-seisou.html ← 特殊清掃記事
│   └── seizenseiri.html    ← 生前整理記事
├── contact/
│   └── index.html          ← 問い合わせページ
├── for-business/
│   └── index.html          ← 業者向けページ
├── sitemap.xml             ← サイトマップ
├── robots.txt              ← クローラー設定
├── system_design.md        ← 業者機能の設計図
└── DEPLOY_GUIDE.md         ← この手順書
```

---

## 月額費用

| 項目 | 費用 |
|------|------|
| ホスティング（Cloudflare Pages） | 無料 |
| ドメイン | 年間1,000〜1,500円 |
| SSL証明書 | 無料（Cloudflareが自動提供） |
| **合計** | **年間約1,500円のみ** |
