-- EnvPulse Athena Schema
-- SQL to set up the signals database and table

-- Create database
CREATE DATABASE IF NOT EXISTS envpulse_db
  COMMENT 'EnvPulse environment monitoring database'
  LOCATION 's3://envpulse-signals-prod/database/';

-- Create main signals table (partitioned for performance)
CREATE TABLE IF NOT EXISTS envpulse_db.signals (
  -- Probe identification
  probe_id VARCHAR COMMENT 'Unique probe identifier',
  probe_name VARCHAR COMMENT 'Human-readable probe name',
  
  -- Environment and service information
  environment VARCHAR COMMENT 'Environment: dev, staging, prod',
  service VARCHAR COMMENT 'Service being monitored',
  region VARCHAR COMMENT 'AWS region or deployment region',
  
  -- Signal metadata
  signal_type VARCHAR COMMENT 'Type: api, ui, synthetic, health, data',
  source VARCHAR COMMENT 'Source system or probe runner',
  
  -- Status and results
  status VARCHAR COMMENT 'PASS, FAIL, TIMEOUT, ERROR',
  status_code INT COMMENT 'HTTP status code if applicable',
  error_code VARCHAR COMMENT 'Application error code',
  error_message VARCHAR COMMENT 'Detailed error message',
  
  -- Performance metrics
  response_time_ms INT COMMENT 'Response time in milliseconds',
  dns_time_ms INT COMMENT 'DNS resolution time',
  connect_time_ms INT COMMENT 'Connection time',
  first_byte_time_ms INT COMMENT 'Time to first byte',
  
  -- Health and validation
  health_score INT COMMENT '0-100 health percentage',
  validation_passed BOOLEAN COMMENT 'Whether validation checks passed',
  validation_details VARCHAR COMMENT 'JSON with validation results',
  
  -- Metadata and context
  metadata VARCHAR COMMENT 'JSON with additional context',
  tags VARCHAR COMMENT 'Comma-separated tags for filtering',
  
  -- Tracking
  timestamp VARCHAR COMMENT 'ISO 8601 timestamp of probe execution',
  execution_id VARCHAR COMMENT 'Unique execution identifier',
  batch_id VARCHAR COMMENT 'Batch identifier for grouped probes'
)
COMMENT 'Environment monitoring signals and health checks'
PARTITIONED BY (
  year INT,
  month INT,
  day INT
)
STORED AS PARQUET
LOCATION 's3://envpulse-signals-prod/signals/'
TBLPROPERTIES (
  'classification' = 'parquet',
  'compressionType' = 'snappy',
  'typeOfData' = 'file'
);

-- Create summary table for daily metrics
CREATE TABLE IF NOT EXISTS envpulse_db.daily_summary (
  date DATE,
  environment VARCHAR,
  service VARCHAR,
  signal_type VARCHAR,
  total_probes INT,
  successful_probes INT,
  failed_probes INT,
  timeout_probes INT,
  error_probes INT,
  success_rate DOUBLE,
  avg_response_time_ms DOUBLE,
  p95_response_time_ms INT,
  p99_response_time_ms INT,
  min_response_time_ms INT,
  max_response_time_ms INT,
  created_at TIMESTAMP
)
PARTITIONED BY (year INT, month INT, day INT)
STORED AS PARQUET
LOCATION 's3://envpulse-signals-prod/daily-summary/'
TBLPROPERTIES ('compressionType' = 'snappy');

-- Create alerts history table
CREATE TABLE IF NOT EXISTS envpulse_db.alerts_history (
  alert_id VARCHAR,
  environment VARCHAR,
  service VARCHAR,
  alert_type VARCHAR,
  severity VARCHAR,
  message VARCHAR,
  status VARCHAR,
  created_at TIMESTAMP,
  resolved_at TIMESTAMP,
  acknowledged_by VARCHAR,
  acknowledged_at TIMESTAMP,
  runbook_url VARCHAR,
  metadata VARCHAR
)
PARTITIONED BY (year INT, month INT, day INT)
STORED AS PARQUET
LOCATION 's3://envpulse-signals-prod/alerts-history/'
TBLPROPERTIES ('compressionType' = 'snappy');

-- Common queries

-- 1. Get latest failures
-- SELECT
--   environment,
--   service,
--   COUNT(*) as failure_count,
--   MAX(from_iso8601_timestamp(timestamp)) as last_failure
-- FROM envpulse_db.signals
-- WHERE status = 'FAIL'
--   AND from_iso8601_timestamp(timestamp) > current_timestamp - interval '1' hour
--   AND year = CAST(YEAR(current_date) AS VARCHAR)
--   AND month = CAST(MONTH(current_date) AS VARCHAR)
--   AND day = CAST(DAY(current_date) AS VARCHAR)
-- GROUP BY environment, service
-- ORDER BY failure_count DESC;

-- 2. Calculate environment uptime
-- SELECT
--   environment,
--   ROUND(
--     100.0 * SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) / COUNT(*),
--     2
--   ) as uptime_percentage
-- FROM envpulse_db.signals
-- WHERE from_iso8601_timestamp(timestamp) > current_timestamp - interval '24' hour
-- GROUP BY environment;

-- 3. Response time statistics
-- SELECT
--   environment,
--   service,
--   COUNT(*) as probe_count,
--   APPROX_PERCENTILE(response_time_ms, 0.50) as p50,
--   APPROX_PERCENTILE(response_time_ms, 0.95) as p95,
--   APPROX_PERCENTILE(response_time_ms, 0.99) as p99,
--   AVG(response_time_ms) as avg_time
-- FROM envpulse_db.signals
-- WHERE response_time_ms IS NOT NULL
--   AND from_iso8601_timestamp(timestamp) > current_timestamp - interval '1' hour
-- GROUP BY environment, service;

-- 4. Get alerts in last 24 hours
-- SELECT
--   alert_id,
--   environment,
--   alert_type,
--   severity,
--   message,
--   created_at
-- FROM envpulse_db.alerts_history
-- WHERE from_iso8601_timestamp(created_at) > current_timestamp - interval '24' hour
-- ORDER BY created_at DESC;
