PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  name TEXT,
  role TEXT NOT NULL DEFAULT 'admin',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  last_signed_in INTEGER
);

CREATE TABLE IF NOT EXISTS inquiries (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  phone TEXT NOT NULL,
  email TEXT NOT NULL,
  region TEXT NOT NULL,
  service_type TEXT NOT NULL,
  floor_plan TEXT,
  budget TEXT,
  preferred_timing TEXT,
  details TEXT,
  status TEXT NOT NULL DEFAULT '未対応' CHECK(status IN ('未対応','対応中','完了')),
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_inquiries_created ON inquiries(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_inquiries_status ON inquiries(status);

CREATE TABLE IF NOT EXISTS inquiry_memos (
  id TEXT PRIMARY KEY,
  inquiry_id TEXT NOT NULL REFERENCES inquiries(id) ON DELETE CASCADE,
  content TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_inquiry_memos_inquiry ON inquiry_memos(inquiry_id, created_at DESC);

CREATE TABLE IF NOT EXISTS business_applications (
  id TEXT PRIMARY KEY,
  company_name TEXT NOT NULL,
  contact_person TEXT NOT NULL,
  phone TEXT NOT NULL,
  email TEXT NOT NULL,
  service_area TEXT NOT NULL,
  service_content TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT '未対応' CHECK(status IN ('未対応','承認','却下')),
  setup_token_hash TEXT,
  setup_token_created_at INTEGER,
  setup_token_expires_at INTEGER,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_business_created ON business_applications(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_business_status ON business_applications(status);

CREATE TABLE IF NOT EXISTS advertisements (
  id TEXT PRIMARY KEY,
  business_id TEXT NOT NULL UNIQUE REFERENCES business_applications(id) ON DELETE CASCADE,
  company_name TEXT NOT NULL,
  catchphrase TEXT,
  description TEXT,
  phone TEXT,
  email TEXT,
  price_range TEXT,
  business_hours TEXT,
  qualifications TEXT,
  logo_url TEXT,
  photo_url TEXT,
  service_genres_json TEXT NOT NULL DEFAULT '[]',
  service_area TEXT,
  banner_url TEXT,
  is_active INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ads_active ON advertisements(is_active);

CREATE TABLE IF NOT EXISTS ad_events (
  id TEXT PRIMARY KEY,
  ad_id TEXT NOT NULL REFERENCES advertisements(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK(event_type IN ('impression','click','phone_reveal','email_reveal')),
  placement TEXT,
  page_url TEXT,
  page_genre TEXT,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ad_events_ad_time ON ad_events(ad_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ad_events_type_time ON ad_events(event_type, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action TEXT NOT NULL,
  entity_type TEXT NOT NULL,
  entity_id TEXT,
  details_json TEXT,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created ON audit_logs(created_at DESC);

CREATE TABLE IF NOT EXISTS rate_limits (
  id TEXT PRIMARY KEY,
  scope TEXT NOT NULL,
  count INTEGER NOT NULL,
  bucket INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS migration_state (
  key TEXT PRIMARY KEY,
  value_json TEXT NOT NULL,
  updated_at INTEGER NOT NULL
);
