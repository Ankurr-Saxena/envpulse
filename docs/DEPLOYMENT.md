# EnvPulse Deployment Guide

Production deployment and best practices for EnvPulse.

## Deployment Strategies

### Strategy 1: Terraform (Recommended for IaC)

```bash
cd terraform/
terraform init
terraform plan -out=tfplan
# Review plan carefully
terraform apply tfplan
```

**Benefits:**
- Infrastructure as code, version-controlled
- Reproducible deployments
- Easy rollback with state management
- Cost estimation

### Strategy 2: AWS SAM (for serverless)

```bash
sam build
sam deploy --guided --capabilities CAPABILITY_IAM
```

### Strategy 3: AWS CloudFormation (for existing stacks)

```bash
aws cloudformation create-stack \
  --stack-name envpulse-stack \
  --template-body file://cloudformation/template.yaml \
  --parameters ParameterKey=Environment,ParameterValue=prod
```

## Pre-Deployment Checklist

- [ ] AWS credentials configured and tested
- [ ] All secrets stored in AWS Secrets Manager
- [ ] S3 buckets created and versioning enabled
- [ ] Athena database and tables created
- [ ] Slack webhook configured and tested
- [ ] Lambda IAM role policies reviewed
- [ ] VPC and security groups configured (if using VPC)
- [ ] CloudWatch alarms set up
- [ ] Backup strategy defined
- [ ] Runbooks and documentation completed

## Deployment Architecture

### Multi-Environment Setup

```
Production
├── Lambda: envpulse-monitor-prod
├── S3: envpulse-signals-prod
├── Athena: envpulse_prod_db
└── Alerts: prod-alerts Slack channel

Staging
├── Lambda: envpulse-monitor-staging
├── S3: envpulse-signals-staging
├── Athena: envpulse_staging_db
└── Alerts: staging-alerts Slack channel

Development
├── Lambda: envpulse-monitor-dev
├── S3: envpulse-signals-dev
├── Athena: envpulse_dev_db
└── Alerts: dev-alerts Slack channel
```

## Environment-Specific Configurations

### Production Configuration

```bash
export ENVIRONMENT=production
export ALERT_THRESHOLD=2
export FAILURE_WINDOW_MINUTES=60
export QUERY_TIMEOUT_SECONDS=120
export LOG_LEVEL=WARNING  # Less verbose in production
export SLACK_CHANNEL="#envpulse-prod-alerts"
```

Configuration for aggressive alerting:
```yaml
environments:
  production:
    alert_threshold: 2
    failure_window_minutes: 60
    slack_channel: "#envpulse-prod-alerts"
    oncall_notification: true
    pagerduty_integration: true
    retry_count: 3
```

### Staging Configuration

```yaml
environments:
  staging:
    alert_threshold: 3
    failure_window_minutes: 120
    slack_channel: "#envpulse-staging-alerts"
    oncall_notification: false
    pagerduty_integration: false
    retry_count: 2
```

### Development Configuration

```yaml
environments:
  development:
    alert_threshold: 5
    failure_window_minutes: 240
    slack_channel: "#envpulse-dev-alerts"
    oncall_notification: false
    pagerduty_integration: false
    retry_count: 1
```

## Security Hardening

### 1. IAM Least Privilege

Lambda execution role should only have:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "athena:StartQueryExecution",
        "athena:GetQueryExecution",
        "athena:GetQueryResults"
      ],
      "Resource": "arn:aws:athena:REGION:ACCOUNT:workgroup/primary"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": "arn:aws:s3:::envpulse-athena-results/*"
    },
    {
      "Effect": "Allow",
      "Action": "logs:CreateLogGroup",
      "Resource": "arn:aws:logs:REGION:ACCOUNT:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:REGION:ACCOUNT:log-group:/aws/lambda/envpulse-monitor:*"
    }
  ]
}
```

### 2. Secrets Management

Store sensitive data in AWS Secrets Manager:
```bash
aws secretsmanager create-secret \
  --name envpulse/prod/slack-webhook \
  --secret-string '{"url":"https://hooks.slack.com/..."}'

aws secretsmanager create-secret \
  --name envpulse/prod/db-credentials \
  --secret-string '{"username":"admin","password":"..."}'
```

Update Lambda to fetch secrets:
```python
import boto3
import json

secrets_client = boto3.client('secretsmanager')

def get_secret(secret_name):
    response = secrets_client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

slack_webhook = get_secret('envpulse/prod/slack-webhook')['url']
```

### 3. VPC Isolation

Deploy Lambda in VPC for private endpoint access:
```hcl
# Terraform example
resource "aws_lambda_function" "envpulse" {
  vpc_config {
    subnet_ids         = [aws_subnet.private.id]
    security_group_ids = [aws_security_group.lambda.id]
  }
}
```

### 4. Encryption

Enable encryption at rest and in transit:
```bash
# S3 bucket encryption
aws s3api put-bucket-encryption \
  --bucket envpulse-signals-prod \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Enable SSL/TLS for all communications
```

### 5. Audit Logging

Enable CloudTrail for all API calls:
```bash
aws cloudtrail create-trail \
  --name envpulse-trail \
  --s3-bucket-name envpulse-audit-logs

aws cloudtrail start-logging --trail-name envpulse-trail
```

## Monitoring the Monitor

### CloudWatch Alarms

```bash
# Alert if Lambda fails
aws cloudwatch put-metric-alarm \
  --alarm-name envpulse-lambda-errors \
  --alarm-description "Alert on Lambda function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --evaluation-periods 1 \
  --dimensions Name=FunctionName,Value=envpulse-monitor

# Alert if Lambda times out
aws cloudwatch put-metric-alarm \
  --alarm-name envpulse-lambda-timeout \
  --alarm-description "Alert on Lambda timeouts" \
  --metric-name Duration \
  --namespace AWS/Lambda \
  --statistic Maximum \
  --period 300 \
  --threshold 110000 \  # 110 seconds in ms
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1
```

### Custom Metrics

Log custom metrics for monitoring:
```python
import boto3

cloudwatch = boto3.client('cloudwatch')

def log_metric(name, value, unit='Count'):
    cloudwatch.put_metric_data(
        Namespace='EnvPulse',
        MetricData=[{
            'MetricName': name,
            'Value': value,
            'Unit': unit
        }]
    )

# In Lambda handler:
log_metric('AlertsTriggered', len(alerts), 'Count')
log_metric('QueryExecutionTime', elapsed_seconds, 'Seconds')
```

## Cost Optimization

### 1. Athena Query Costs

**Partition your data** to scan less:
```sql
-- Good: Scanned only today's data
SELECT * FROM signals
WHERE year=2024 AND month=1 AND day=28
AND status='FAIL'

-- Bad: Scans entire table
SELECT * FROM signals
WHERE status='FAIL'
```

**Use columnar format**:
- Parquet: ~80% cost savings vs CSV
- ORC: ~70% cost savings vs CSV

### 2. Lambda Costs

- **Memory allocation**: 512MB is usually optimal
- **Execution frequency**: Use appropriate intervals (10-60 min, not every minute)
- **Batch processing**: Process multiple signals in one invocation

### 3. S3 Costs

Lifecycle policies:
```json
{
  "Rules": [
    {
      "Id": "Archive old signals",
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
```

## Rollback Procedures

### Lambda Rollback

```bash
# Get previous version
aws lambda list-versions-by-function \
  --function-name envpulse-monitor \
  --query 'Versions[*].[FunctionArn,LastModified]'

# Rollback to previous version
aws lambda update-alias \
  --function-name envpulse-monitor \
  --name PROD \
  --function-version 5
```

### Infrastructure Rollback (Terraform)

```bash
# View previous state
terraform state list
terraform state show

# Rollback previous deployment
git checkout HEAD~1 terraform/
terraform plan -out=rollback.plan
terraform apply rollback.plan
```

## Troubleshooting Deployments

### Lambda won't start

```bash
# Check function configuration
aws lambda get-function-configuration --function-name envpulse-monitor

# Check recent invocations
aws lambda list-events --function-name envpulse-monitor

# View logs
aws logs tail /aws/lambda/envpulse-monitor --follow
```

### High error rates

```bash
# Check metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=envpulse-monitor \
  --start-time 2024-01-01T00:00:00Z \
  --end-time 2024-01-02T00:00:00Z \
  --period 300 \
  --statistics Sum
```

### Slow query execution

```bash
# Check Athena query history
aws athena list-query-executions \
  --query-execution-context Database=envpulse_db

# Analyze query plan
EXPLAIN SELECT ... FROM signals ...
```

## Maintenance Schedule

### Daily
- Monitor CloudWatch dashboards
- Check Slack alerts for patterns

### Weekly
- Review Lambda error rates
- Analyze Athena query costs
- Update probe configurations

### Monthly
- Optimize Athena queries
- Review and rotate credentials
- Analyze trends and SLAs

### Quarterly
- Update dependencies
- Security audit
- Capacity planning review
- Disaster recovery drill

## Going Live

### Pre-launch Validation

```bash
# 1. Run smoke tests
python tests/smoke_tests.py --environment prod

# 2. Load test Athena
python tests/load_test_athena.py --environment prod

# 3. Verify Slack integration
curl -X POST $SLACK_WEBHOOK_URL \
  -d '{"text":"🚀 EnvPulse production deployment"}'

# 4. Check all metrics and alarms
aws cloudwatch describe-alarms --alarm-names $(aws cloudwatch describe-alarms --query 'MetricAlarms[*].AlarmName' --output text)
```

### Launch Steps

1. Deploy to development ✓
2. Deploy to staging ✓
3. Get stakeholder approval
4. Deploy to production
5. Monitor closely for 24 hours
6. Document any issues
7. Plan improvements

## Support & Escalation

**Escalation path:**
1. Check logs: `aws logs tail /aws/lambda/envpulse-monitor`
2. Review CloudWatch metrics
3. Check AWS service health dashboard
4. Contact AWS support (if infrastructure issue)
5. Post to internal #envpulse-support channel

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.
