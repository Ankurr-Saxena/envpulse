#!/bin/bash
# EnvPulse Athena Database Setup Script
# Creates database, tables, and partitions for signal storage

set -e

# Configuration
ATHENA_DB="${ATHENA_DB:-envpulse_db}"
S3_BUCKET="${S3_BUCKET:-envpulse-signals}"
ATHENA_RESULTS="${ATHENA_RESULTS:-s3://athena-results/}"

echo "=================================================="
echo "EnvPulse Athena Setup"
echo "=================================================="
echo "Database: $ATHENA_DB"
echo "S3 Bucket: $S3_BUCKET"
echo "Athena Results: $ATHENA_RESULTS"
echo "=================================================="

# Create database
echo "[1/3] Creating Athena database..."
aws athena start-query-execution \
  --query-string "CREATE DATABASE IF NOT EXISTS $ATHENA_DB COMMENT 'EnvPulse monitoring database'" \
  --query-execution-context Database=default \
  --result-configuration OutputLocation=$ATHENA_RESULTS \
  --output text

sleep 2

# Create signals table
echo "[2/3] Creating signals table..."
aws athena start-query-execution \
  --query-string "
    CREATE TABLE IF NOT EXISTS $ATHENA_DB.signals (
      probe_id VARCHAR COMMENT 'Unique probe identifier',
      probe_name VARCHAR COMMENT 'Probe human-readable name',
      environment VARCHAR COMMENT 'Environment name',
      service VARCHAR COMMENT 'Service being monitored',
      signal_type VARCHAR COMMENT 'Signal type: api, ui, synthetic, health, data',
      status VARCHAR COMMENT 'Status: PASS, FAIL, TIMEOUT, ERROR',
      url VARCHAR COMMENT 'Endpoint URL',
      method VARCHAR COMMENT 'HTTP method',
      status_code INT COMMENT 'HTTP status code',
      response_time_ms INT COMMENT 'Response time in milliseconds',
      error_message VARCHAR COMMENT 'Error message if failed',
      validation_passed BOOLEAN COMMENT 'Validation result',
      timestamp VARCHAR COMMENT 'ISO 8601 timestamp',
      execution_id VARCHAR COMMENT 'Execution identifier'
    )
    PARTITIONED BY (year INT, month INT, day INT)
    STORED AS PARQUET
    LOCATION 's3://$S3_BUCKET/signals/'
    TBLPROPERTIES (
      'classification' = 'parquet',
      'compressionType' = 'snappy'
    )
  " \
  --query-execution-context Database=$ATHENA_DB \
  --result-configuration OutputLocation=$ATHENA_RESULTS \
  --output text

sleep 2

# Create daily summary table
echo "[3/3] Creating daily summary table..."
aws athena start-query-execution \
  --query-string "
    CREATE TABLE IF NOT EXISTS $ATHENA_DB.daily_summary (
      date DATE COMMENT 'Summary date',
      environment VARCHAR COMMENT 'Environment',
      service VARCHAR COMMENT 'Service',
      signal_type VARCHAR COMMENT 'Signal type',
      total_probes INT COMMENT 'Total probe executions',
      successful_probes INT COMMENT 'Successful probes',
      failed_probes INT COMMENT 'Failed probes',
      timeout_probes INT COMMENT 'Timed out probes',
      success_rate DOUBLE COMMENT 'Success rate percentage',
      avg_response_time_ms DOUBLE COMMENT 'Average response time',
      max_response_time_ms INT COMMENT 'Maximum response time'
    )
    PARTITIONED BY (year INT, month INT, day INT)
    STORED AS PARQUET
    LOCATION 's3://$S3_BUCKET/daily-summary/'
  " \
  --query-execution-context Database=$ATHENA_DB \
  --result-configuration OutputLocation=$ATHENA_RESULTS \
  --output text

echo "=================================================="
echo "✓ Athena database setup completed!"
echo "=================================================="
echo ""
echo "Next steps:"
echo "1. Verify tables: aws athena list-table-metadata --catalog-name AwsDataCatalog --database-name $ATHENA_DB"
echo "2. Create partitions: aws athena start-query-execution --query-string 'MSCK REPAIR TABLE $ATHENA_DB.signals' --query-execution-context Database=$ATHENA_DB --result-configuration OutputLocation=$ATHENA_RESULTS"
echo "3. Test query: aws athena start-query-execution --query-string 'SELECT COUNT(*) FROM $ATHENA_DB.signals' --query-execution-context Database=$ATHENA_DB --result-configuration OutputLocation=$ATHENA_RESULTS"
