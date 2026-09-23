PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS ad_placements (
  key TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  description TEXT,
  monthly_price INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1,
  sort_order INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL
);

INSERT OR IGNORE INTO ad_placements (key,label,description,monthly_price,is_active,sort_order,updated_at) VALUES
  ('article_top','記事上部','記事の冒頭付近。最も早く読者の目に入る掲載枠。',0,0,10,0),
  ('article_middle','記事中部','本文を読み進めた読者に表示する掲載枠。',0,0,20,0),
  ('article_bottom','記事下部','記事を読み終えた関心度の高い読者向け掲載枠。',0,0,30,0),
  ('sidebar','サイドバー/CTA付近','ガイドページ等の補助導線に表示する掲載枠。',0,0,40,0);

ALTER TABLE advertisements ADD COLUMN placements_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE advertisements ADD COLUMN starts_at INTEGER;
ALTER TABLE advertisements ADD COLUMN ends_at INTEGER;
ALTER TABLE advertisements ADD COLUMN contract_price_monthly INTEGER;
ALTER TABLE advertisements ADD COLUMN billing_note TEXT;
ALTER TABLE advertisements ADD COLUMN website_url TEXT;

UPDATE advertisements
SET placements_json='["article_middle"]'
WHERE placements_json IS NULL OR placements_json='[]';
