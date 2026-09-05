# 福岡遺品整理ガイド - デプロイ・運用手順

このドキュメントは、`fukuoka-ihinseiri-guide.com` の公開と記事更新を安全に行うための手順です。

---

## 公開環境

- リポジトリ: `samnog-36/fukuoka-ihinseiri-guide`
- 公開方式: Cloudflare Pages（GitHub連携）
- 独自ドメイン: `fukuoka-ihinseiri-guide.com`
- Framework preset: None
- Build command: なし
- Build output directory: `/`

`main` への反映は公開サイトへ影響するため、大きなSEO・広告・リダイレクト変更は作業ブランチとPull Requestで確認してから反映します。

---

## 記事を追加・更新する前の原則

### 記事数や文字数を目的にしない

「毎日1本」「各カテゴリ20本」「3,000字以上」のような数量目標だけを理由に記事を作成しません。既存記事と検索意図が重なる場合は、新規URLを増やさず既存記事を更新・統合します。

### AIを使う場合も一次情報を確認する

AIは構成・下書き・表現整理に使用できますが、次の情報は公開前に一次情報まで確認します。

- 国・自治体の制度、手続き、料金、期限
- 相続・税務・契約上の責任
- 健康・衛生・消毒・感染症に関する判断
- 統計、割合、調査結果
- 事業者の料金、許認可、サービス内容

出典は「省庁のトップページ」ではなく、本文の主張を直接確認できるページを優先します。

### 実態のない権威付けをしない

実際に監修を受けていない場合、次のような表現を使いません。

- 専門家が解説
- 弁護士監修レベル
- プロが教える
- 専門家が実例を紹介

また、確認できない「優良業者のみ」「正確な相場」「必ず」「絶対」などの断定を避けます。

---

## 新規記事を作る前のチェック

1. `blog/` とサイト内検索で同じ検索意図の記事がないか確認する。
2. 既存記事に追記すれば解決するテーマなら新規URLを作らない。
3. 福岡固有の一次情報や、読者が実際に判断に使える独自要素があるか確認する。
4. 法律・税務・衛生など個別判断リスクが高いテーマは、十分な確認ができない場合は公開しないか `noindex` とする。
5. 公開後に `sitemap.xml`、カテゴリ一覧、検索データ、内部リンクを更新する。

詳細は `docs/ARTICLE_PUBLICATION_STANDARD.md` を参照してください。

---

## AdSense品質チェック

AdSense関連の大幅更新時は、作業ブランチで以下を実行します。

```bash
python3 scripts/apply_adsense_content_consolidation.py
python3 scripts/apply_adsense_consolidation_phase2.py
python3 scripts/adsense_quality_audit.py
python3 scripts/verify_adsense_trust_updates.py
git diff --check
```

監査結果は以下へ保存されます。

- `docs/ADSENSE_CONTENT_AUDIT_20260904.md`
- `docs/ADSENSE_CONSOLIDATION_DECISIONS_20260904.md`
- `docs/ADSENSE_CONSOLIDATION_PHASE2_20260904.md`

`fix/adsense-low-value-20260904` ブランチではGitHub Actionsでも同じ監査を実行します。

---

## 301統合・noindexの考え方

### 301リダイレクト

同じ検索意図のページが複数ある場合、内容・更新状況・一次情報が優れた代表ページへ301で統合します。統合元は `sitemap.xml`、サイト内検索、記事一覧から外します。

### noindex

法律・税務・契約責任・感染症など、内容を残す必要はあるものの検索流入を受ける状態で公開するには確認不足のページは、一時的に `noindex, follow` とし、広告も停止します。確認後に再公開を判断します。

---

## 非コンテンツページの広告

次のページではAdSense広告を読み込みません。

- 編集方針・運営情報
- プライバシーポリシー
- お問い合わせフォーム
- 業者向け掲載案内

広告より本文が主となるページだけを広告対象にします。

---

## 公開後の確認

1. トップページ、代表記事、統合先URLが200で表示されること。
2. 301統合元URLが正しい代表ページへ移動すること。
3. `ads.txt` がルートで取得できること。
4. `robots.txt` と `sitemap.xml` が取得できること。
5. `noindex` 保留ページがサイトマップに含まれていないこと。
6. モバイルでナビゲーション・本文・フォームが崩れていないこと。
7. Search Consoleでは、統合元の減少と代表URLのインデックス状況を確認すること。

---

## サイト売却・引き継ぎ時

買い手へ必要に応じて以下を引き継ぎます。

1. GitHubリポジトリ
2. ドメイン管理
3. Cloudflare Pagesプロジェクト
4. Google Analytics / Search Console / AdSense の適切な権限
5. 本運用手順と編集方針
