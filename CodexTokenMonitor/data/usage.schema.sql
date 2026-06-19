CREATE TABLE token_events (
  event_id TEXT PRIMARY KEY,
  timestamp TEXT NOT NULL,
  session_id TEXT NOT NULL,
  cwd TEXT,
  originator TEXT,
  source_file TEXT NOT NULL,
  total_tokens INTEGER NOT NULL,
  input_tokens INTEGER NOT NULL,
  cached_input_tokens INTEGER NOT NULL,
  output_tokens INTEGER NOT NULL,
  reasoning_output_tokens INTEGER NOT NULL,
  last_total_tokens INTEGER NOT NULL,
  model_context_window INTEGER,
  primary_used_percent REAL,
  primary_window_minutes INTEGER,
  primary_resets_at INTEGER,
  secondary_used_percent REAL,
  secondary_window_minutes INTEGER,
  secondary_resets_at INTEGER,
  plan_type TEXT,
  limit_id TEXT,
  rate_limit_reached_type TEXT,
  raw_metrics_json TEXT NOT NULL
);
CREATE INDEX idx_token_events_timestamp ON token_events(timestamp);
CREATE INDEX idx_token_events_session ON token_events(session_id);
CREATE TABLE file_state (
  path TEXT PRIMARY KEY,
  size INTEGER NOT NULL,
  mtime_ns INTEGER NOT NULL,
  scanned_at TEXT NOT NULL
);
CREATE TABLE monitor_samples (
  sampled_at TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  latest_event_at TEXT,
  primary_used_percent REAL,
  primary_remaining_percent REAL,
  secondary_used_percent REAL,
  secondary_remaining_percent REAL,
  active_sessions INTEGER,
  total_sessions INTEGER,
  token_count_events INTEGER,
  threads_working INTEGER,
  agents_working INTEGER,
  projects_working INTEGER,
  latest_total_tokens_sum INTEGER,
  latest_upload_tokens_sum INTEGER,
  latest_output_tokens_sum INTEGER,
  latest_contextual_tokens_sum INTEGER,
  latest_reasoning_tokens_sum INTEGER,
  average_burn_rate_primary_percent_per_hour REAL,
  one_hour_burn_rate_primary_percent_per_hour REAL,
  summary_json TEXT NOT NULL
, sample_bucket_at TEXT);
CREATE INDEX idx_monitor_samples_sampled_at ON monitor_samples(sampled_at);
CREATE INDEX idx_monitor_samples_source ON monitor_samples(source);
CREATE UNIQUE INDEX idx_monitor_samples_source_bucket
        ON monitor_samples(source, sample_bucket_at)
        WHERE sample_bucket_at IS NOT NULL
        ;
