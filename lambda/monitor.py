"""
EnvPulse Monitor Lambda Function
================================
Analyzes environment signals from AWS Athena and triggers alerts when instability is detected.

Configuration via environment variables:
- ATHENA_DB: Athena database name (default: envpulse_db)
- ATHENA_TABLE: Signals table name (default: signals)
- S3_OUTPUT: S3 bucket for Athena results (default: s3://athena-results/)
- SLACK_WEBHOOK_URL: Slack webhook for alerts (required from AWS Secrets Manager or env)
- ALERT_THRESHOLD: Min failures to trigger alert (default: 2)
- FAILURE_WINDOW_MINUTES: Lookback window for failures (default: 60)
- LOG_LEVEL: Logging level - DEBUG, INFO, WARNING, ERROR (default: INFO)
"""

import os
import json
import time
import logging
import boto3
import urllib3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from botocore.exceptions import BotoCoreError, ClientError

# Configure logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
logger = logging.getLogger()
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
formatter = logging.Formatter(
    '[%(asctime)s] %(levelname)s - %(funcName)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
handler = logger.handlers[0] if logger.handlers else logging.StreamHandler()
handler.setFormatter(formatter)
if not logger.handlers:
    logger.addHandler(handler)

# Configuration
ATHENA_DB = os.getenv('ATHENA_DB', 'envpulse_db')
ATHENA_TABLE = os.getenv('ATHENA_TABLE', 'signals')
S3_OUTPUT = os.getenv('S3_OUTPUT', 's3://athena-results/')
SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL')
ALERT_THRESHOLD = int(os.getenv('ALERT_THRESHOLD', '2'))
FAILURE_WINDOW_MINUTES = int(os.getenv('FAILURE_WINDOW_MINUTES', '60'))
QUERY_TIMEOUT_SECONDS = int(os.getenv('QUERY_TIMEOUT_SECONDS', '60'))
MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
RETRY_DELAY_SECONDS = int(os.getenv('RETRY_DELAY_SECONDS', '2'))

# AWS clients
athena_client = boto3.client('athena')
http_client = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=5.0, read=10.0),
    maxsize=10
)

logger.info(f"Configuration: DB={ATHENA_DB}, Table={ATHENA_TABLE}, Threshold={ALERT_THRESHOLD}, Window={FAILURE_WINDOW_MINUTES}m")


class EnvPulseException(Exception):
    """Base exception for EnvPulse errors"""
    pass


class AthenaQueryException(EnvPulseException):
    """Athena query execution error"""
    pass


class AlertException(EnvPulseException):
    """Alert delivery error"""
    pass


def validate_config() -> bool:
    """Validate required configuration."""
    if not SLACK_WEBHOOK_URL:
        logger.warning("SLACK_WEBHOOK_URL not configured - alerts will not be sent")
        return False
    if not S3_OUTPUT.startswith('s3://'):
        logger.error(f"Invalid S3_OUTPUT: {S3_OUTPUT}")
        raise EnvPulseException("S3_OUTPUT must be a valid S3 path")
    return True


def run_query(query: str) -> str:
    """
    Execute Athena query and return query execution ID.
    
    Args:
        query: SQL query string
        
    Returns:
        Query execution ID
        
    Raises:
        AthenaQueryException: If query execution fails
    """
    try:
        logger.debug(f"Executing Athena query: {query[:100]}...")
        response = athena_client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': ATHENA_DB},
            ResultConfiguration={'OutputLocation': S3_OUTPUT}
        )
        query_id = response['QueryExecutionId']
        logger.info(f"Query started with ID: {query_id}")
        return query_id
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to start Athena query: {str(e)}")
        raise AthenaQueryException(f"Athena query execution failed: {str(e)}")


def wait_for_query(query_id: str, timeout_seconds: int = QUERY_TIMEOUT_SECONDS) -> str:
    """
    Wait for Athena query to complete with timeout.
    
    Args:
        query_id: Athena query execution ID
        timeout_seconds: Maximum time to wait
        
    Returns:
        Query status: 'SUCCEEDED' or 'FAILED'
        
    Raises:
        AthenaQueryException: If query fails or times out
    """
    start_time = time.time()
    attempt = 0
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            logger.error(f"Query timeout after {elapsed:.1f}s")
            raise AthenaQueryException(f"Query {query_id} timed out after {timeout_seconds}s")
        
        try:
            response = athena_client.get_query_execution(QueryExecutionId=query_id)
            state = response['QueryExecution']['Status']['State']
            
            if state == 'SUCCEEDED':
                logger.info(f"Query succeeded after {elapsed:.1f}s")
                return 'SUCCEEDED'
            elif state == 'FAILED':
                status_reason = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown')
                logger.error(f"Query failed: {status_reason}")
                raise AthenaQueryException(f"Query failed: {status_reason}")
            elif state == 'CANCELLED':
                logger.error("Query was cancelled")
                raise AthenaQueryException("Query was cancelled")
            else:
                logger.debug(f"Query status: {state} (elapsed: {elapsed:.1f}s)")
                
        except (BotoCoreError, ClientError) as e:
            attempt += 1
            if attempt > MAX_RETRIES:
                logger.error(f"Max retries exceeded checking query status: {str(e)}")
                raise AthenaQueryException(f"Failed to check query status: {str(e)}")
            logger.warning(f"Retry {attempt}/{MAX_RETRIES} after error: {str(e)}")
        
        time.sleep(RETRY_DELAY_SECONDS)


def get_query_results(query_id: str) -> List[Dict]:
    """
    Retrieve results from completed Athena query.
    
    Args:
        query_id: Athena query execution ID
        
    Returns:
        List of result rows
        
    Raises:
        AthenaQueryException: If result retrieval fails
    """
    try:
        response = athena_client.get_query_results(QueryExecutionId=query_id)
        rows = response['ResultSet']['Rows']
        logger.info(f"Retrieved {len(rows)} rows from query")
        return rows
    except (BotoCoreError, ClientError, KeyError) as e:
        logger.error(f"Failed to get query results: {str(e)}")
        raise AthenaQueryException(f"Failed to retrieve query results: {str(e)}")


def parse_results(rows: List[Dict]) -> List[Tuple[str, int]]:
    """
    Parse Athena query results into (environment, failure_count) tuples.
    
    Args:
        rows: Raw result rows from Athena
        
    Returns:
        List of (environment, failure_count) tuples
    """
    alerts = []
    
    if len(rows) <= 1:  # Only header row
        logger.info("No failure data in query results")
        return alerts
    
    for i, row in enumerate(rows[1:], start=1):  # Skip header
        try:
            data = row.get('Data', [])
            if len(data) < 2:
                logger.warning(f"Row {i}: Insufficient data columns")
                continue
                
            env = data[0].get('VarCharValue', 'UNKNOWN')
            failure_count_str = data[1].get('VarCharValue', '0')
            
            if not env or env == 'UNKNOWN':
                logger.warning(f"Row {i}: Missing environment name")
                continue
            
            try:
                failure_count = int(failure_count_str)
                if failure_count >= ALERT_THRESHOLD:
                    alerts.append((env, failure_count))
                    logger.info(f"Alert triggered: {env} - {failure_count} failures")
            except ValueError:
                logger.warning(f"Row {i}: Invalid failure count '{failure_count_str}'")
                
        except Exception as e:
            logger.warning(f"Row {i}: Error parsing result: {str(e)}")
    
    return alerts


def format_alert_message(alerts: List[Tuple[str, int]]) -> str:
    """
    Format alerts into a Slack message.
    
    Args:
        alerts: List of (environment, failure_count) tuples
        
    Returns:
        Formatted message string
    """
    timestamp = datetime.utcnow().isoformat() + 'Z'
    header = f"🚨 EnvPulse Alert - {timestamp}"
    header += f"\nThreshold breached: ≥{ALERT_THRESHOLD} failures in last {FAILURE_WINDOW_MINUTES}m\n"
    
    alert_lines = []
    for env, count in alerts:
        emoji = "🔴" if count >= 5 else "🟡"
        alert_lines.append(f"{emoji} *{env}*: {count} failures")
    
    return header + "\n".join(alert_lines)


def send_slack_alert(message: str) -> bool:
    """
    Send alert to Slack webhook.
    
    Args:
        message: Alert message
        
    Returns:
        True if successful, False otherwise
        
    Raises:
        AlertException: If Slack delivery fails
    """
    if not SLACK_WEBHOOK_URL:
        logger.warning("Slack webhook not configured - skipping alert")
        return False
    
    try:
        payload = {
            'text': message,
            'type': 'mrkdwn'
        }
        
        logger.debug(f"Sending Slack alert: {message[:100]}...")
        response = http_client.request(
            'POST',
            SLACK_WEBHOOK_URL,
            body=json.dumps(payload),
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status == 200:
            logger.info("Alert successfully sent to Slack")
            return True
        else:
            logger.error(f"Slack API returned status {response.status}")
            raise AlertException(f"Slack returned status {response.status}")
            
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {str(e)}")
        raise AlertException(f"Failed to deliver Slack alert: {str(e)}")


def build_query() -> str:
    """
    Build the Athena query for failure analysis.
    
    Returns:
        SQL query string
    """
    query = f"""
    SELECT 
        environment,
        COUNT(*) as failure_count,
        MAX(from_iso8601_timestamp(timestamp)) as last_failure
    FROM {ATHENA_TABLE}
    WHERE status = 'FAIL'
    AND from_iso8601_timestamp(timestamp) > current_timestamp - interval '{FAILURE_WINDOW_MINUTES}' minute
    GROUP BY environment
    ORDER BY failure_count DESC
    """
    return query


def lambda_handler(event, context):
    """
    Main Lambda handler for EnvPulse monitoring.
    
    Args:
        event: Lambda event (from EventBridge)
        context: Lambda context
        
    Returns:
        Response dict with statusCode and body
    """
    try:
        logger.info("=== EnvPulse Monitor Started ===")
        
        # Validate configuration
        validate_config()
        
        # Build and execute query
        query = build_query()
        logger.info(f"Query window: {FAILURE_WINDOW_MINUTES} minutes, threshold: {ALERT_THRESHOLD}")
        
        query_id = run_query(query)
        status = wait_for_query(query_id)
        
        if status != 'SUCCEEDED':
            raise AthenaQueryException(f"Query execution failed with status: {status}")
        
        # Parse results
        rows = get_query_results(query_id)
        alerts = parse_results(rows)
        
        # Send alerts if any threshold breaches detected
        if alerts:
            message = format_alert_message(alerts)
            send_slack_alert(message)
            
            response_body = {
                'status': 'alerts_sent',
                'alert_count': len(alerts),
                'alerts': [{'environment': env, 'failures': count} for env, count in alerts],
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        else:
            logger.info("No alerts to send - all environments healthy")
            response_body = {
                'status': 'healthy',
                'alert_count': 0,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        
        logger.info(f"=== EnvPulse Monitor Completed: {response_body['status']} ===")
        
        return {
            'statusCode': 200,
            'body': json.dumps(response_body)
        }
        
    except AthenaQueryException as e:
        logger.error(f"Athena query failed: {str(e)}")
        return {
            'statusCode': 502,
            'body': json.dumps({'error': 'Query execution failed', 'details': str(e)})
        }
        
    except AlertException as e:
        logger.error(f"Alert delivery failed: {str(e)}")
        return {
            'statusCode': 503,
            'body': json.dumps({'error': 'Alert delivery failed', 'details': str(e)})
        }
        
    except EnvPulseException as e:
        logger.error(f"Configuration error: {str(e)}")
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Configuration error', 'details': str(e)})
        }
        
    except Exception as e:
        logger.exception(f"Unexpected error in monitor: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error', 'details': str(e)})
        }

