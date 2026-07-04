# EnvPulse Setup Guide

Complete step-by-step setup for EnvPulse environment monitoring platform.

## Prerequisites

- **AWS Account** with appropriate permissions
- **AWS CLI** v2.x+ (`aws --version`)
- **Python** 3.9+ (`python --version`)
- **Slack Workspace** with admin rights to create webhooks (for alerts)
- **Git** for cloning the repository
- **Terraform** 1.0+ (optional, for IaC deployment)

### AWS Permissions Required

Your IAM user needs these permissions:
- S3: Create/read buckets
- Athena: Execute queries, manage databases
- Lambda: Create/update functions
- EventBridge: Create rules
- CloudWatch: Create log groups
- IAM: Create roles and policies
- Secrets Manager: Store webhook URLs

Minimal IAM policy:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:*",
        "athena:*",
        "lambda:*",
        "events:*",
        "logs:*",
        "iam:*",
        "secretsmanager:*"
      ],
      "Resource": "*"
    }
  ]
}
```

## Step 1: Clone Repository

```bash
git clone https://github.com/your-org/envpulse.git
cd envpulse
```

## Step 2: Configure AWS CLI

```bash
aws configure
# Enter:
# AWS Access Key ID: [your-access-key]
# AWS Secret Access Key: [your-secret-key]
# Default region: us-east-1
# Default output format: json
```

Verify configuration:
```bash
aws sts get-caller-identity
# Should show your AWS account details
```

## Step 3: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r lambda/requirements.txt
pip install -r api-probes/requirements.txt  # If available
pip install -r ui-probes/requirements.txt   # If available
```

## Step 4: Create S3 Bucket for Signals

```bash
# Create bucket for signal logs
aws s3 mb s3://envpulse-signals-$(date +%s) --region us-east-1

# Create bucket for Athena results
aws s3 mb s3://envpulse-athena-results-$(date +%s) --region us-east-1

# Enable versioning (optional but recommended)
aws s3api put-bucket-versioning \
  --bucket envpulse-signals-xxx \
  --versioning-configuration Status=Enabled
```

Save bucket names for later use.

## Step 5: Set Up Athena Database

```bash
# Create Athena database and signals table
aws athena start-query-execution \
  --query-string "CREATE DATABASE IF NOT EXISTS envpulse_db" \
  --query-execution-context Database=default \
  --result-configuration OutputLocation=s3://envpulse-athena-results-xxx/

# Wait a moment, then create signals table
aws athena start-query-execution \
  --query-string "
    CREATE TABLE IF NOT EXISTS envpulse_db.signals (
      probe_id STRING,
      environment STRING,
      service STRING,
      signal_type STRING,
      status STRING,
      response_time_ms INT,
      error_message STRING,
      timestamp STRING,
      metadata STRING
    )
    PARTITIONED BY (year INT, month INT, day INT)
    STORED AS PARQUET
    LOCATION 's3://envpulse-signals-xxx/signals/'
  " \
  --query-execution-context Database=envpulse_db \
  --result-configuration OutputLocation=s3://envpulse-athena-results-xxx/
```

Or run the setup script:
```bash
bash athena/setup.sh
```

## Step 6: Configure Slack Webhook

1. Go to Slack App Directory: https://api.slack.com/apps
2. Click "Create New App" → "From scratch"
3. Name: `EnvPulse` → Select workspace
4. Go to "Incoming Webhooks" → Enable it
5. Click "Add New Webhook to Workspace"
6. Select channel: `#alerts` (or create one)
7. Copy the webhook URL

Store it securely in AWS Secrets Manager:
```bash
aws secretsmanager create-secret \
  --name envpulse/slack-webhook \
  --secret-string "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

Or set as environment variable:
```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

## Step 7: Deploy Lambda Function

### Option A: Manual Deployment

```bash
cd lambda/

# Create deployment package
pip install -r requirements.txt -t package/
cp monitor.py alerter.py package/
cd package/
zip -r ../function.zip . -x '*.git*' '__pycache__*'
cd ..

# Create Lambda execution role
aws iam create-role \
  --role-name envpulse-lambda-role \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Principal": {
          "Service": "lambda.amazonaws.com"
        },
        "Action": "sts:AssumeRole"
      }
    ]
  }'

# Attach policies
aws iam attach-role-policy \
  --role-name envpulse-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name envpulse-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonAthenaFullAccess

aws iam attach-role-policy \
  --role-name envpulse-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess

# Create Lambda function
aws lambda create-function \
  --function-name envpulse-monitor \
  --runtime python3.11 \
  --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/envpulse-lambda-role \
  --handler monitor.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 120 \
  --memory-size 512 \
  --environment "Variables={
    ATHENA_DB=envpulse_db,
    S3_OUTPUT=s3://envpulse-athena-results-xxx/,
    SLACK_WEBHOOK_URL=$(aws secretsmanager get-secret-value --secret-id envpulse/slack-webhook --query SecretString --output text | jq -r '.'),
    ALERT_THRESHOLD=2,
    FAILURE_WINDOW_MINUTES=60,
    LOG_LEVEL=INFO
  }"
```

### Option B: Terraform Deployment

```bash
cd terraform/

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Apply configuration
terraform apply
```

## Step 8: Set Up EventBridge Schedule

```bash
# Create EventBridge rule to run Lambda every 10 minutes
aws events put-rule \
  --name envpulse-monitor-schedule \
  --schedule-expression "rate(10 minutes)" \
  --state ENABLED

# Add Lambda as target
aws events put-targets \
  --rule envpulse-monitor-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:$(aws sts get-caller-identity --query Account --output text):function:envpulse-monitor","RoleArn"="arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/service-role/EventBridgeInvokeEnvPulseRole"

# Add permission for EventBridge to invoke Lambda
aws lambda add-permission \
  --function-name envpulse-monitor \
  --statement-id AllowEventBridgeInvoke \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:$(aws sts get-caller-identity --query Account --output text):rule/envpulse-monitor-schedule
```

## Step 9: Configure Grafana Dashboards

### Option A: Cloud Grafana (SaaS)

1. Sign up at https://grafana.com/cloud/
2. Create AWS CloudWatch datasource
3. Import dashboard JSON from `grafana/dashboards/`

### Option B: Self-Hosted Grafana

```bash
docker run -d -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  --name grafana \
  grafana/grafana:latest

# Access at http://localhost:3000
# Add CloudWatch datasource
# Import dashboard from grafana/dashboards/envpulse-main.json
```

## Step 10: Configure API Probes

Create `config/api-probes.yaml`:
```yaml
probes:
  - id: dev-api-health
    environment: development
    url: https://api-dev.example.com/health
    method: GET
    interval_minutes: 5
    timeout_seconds: 10
    expected_status: 200
    
  - id: prod-api-health
    environment: production
    url: https://api-prod.example.com/health
    method: GET
    interval_minutes: 2
    timeout_seconds: 10
    expected_status: 200
```

## Step 11: Configure UI Probes

Create `config/ui-probes.yaml`:
```yaml
probes:
  - id: dev-ui-login
    environment: development
    url: https://app-dev.example.com
    tests:
      - name: "Login flow"
        steps:
          - action: navigate
            url: https://app-dev.example.com/login
          - action: fill
            selector: 'input[name="email"]'
            value: test@example.com
          - action: click
            selector: 'button[type="submit"]'
          - action: wait
            selector: '.dashboard'
            timeout_ms: 5000
```

## Step 12: Deploy CodeBuild Projects

```bash
# Create CodeBuild project for API probes
aws codebuild create-project \
  --name envpulse-api-probes \
  --source type=GITHUB,location=https://github.com/your-org/envpulse \
  --artifacts type=NO_ARTIFACTS \
  --environment type=LINUX_CONTAINER,image=aws/codebuild/standard:5.0,computeType=BUILD_GENERAL1_SMALL \
  --service-role arn:aws:iam::ACCOUNT:role/envpulse-codebuild-role
```

## Verification

Test your setup:

```bash
# 1. Test Slack connectivity
curl -X POST https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  -d '{"text":"EnvPulse test alert"}' \
  -H 'Content-Type: application/json'

# 2. Test Lambda function
aws lambda invoke \
  --function-name envpulse-monitor \
  --log-type Tail \
  response.json
cat response.json

# 3. Check Lambda logs
aws logs tail /aws/lambda/envpulse-monitor --follow

# 4. Verify Athena table
aws athena start-query-execution \
  --query-string "SELECT COUNT(*) FROM envpulse_db.signals LIMIT 10" \
  --query-execution-context Database=envpulse_db \
  --result-configuration OutputLocation=s3://envpulse-athena-results-xxx/
```

## Troubleshooting

### Lambda timeouts
- Increase Lambda timeout to 120+ seconds
- Optimize Athena queries

### No alerts sent
- Verify Slack webhook URL in Secrets Manager
- Check Lambda logs: `aws logs tail /aws/lambda/envpulse-monitor`
- Test webhook manually with curl

### Athena queries fail
- Verify database exists: `aws athena list-databases --catalog-name AwsDataCatalog`
- Check S3 bucket exists and Lambda has access
- Review Athena CloudTrail logs

### High AWS costs
- Partition Athena queries by date/environment
- Implement S3 lifecycle policies
- Review CloudWatch Logs retention

## Next Steps

1. **Add Probes**: Configure API and UI probes in `config/`
2. **Create Dashboards**: Import/customize Grafana dashboards
3. **Set Thresholds**: Tune alert thresholds for your environments
4. **Document Runbooks**: Create incident response procedures
5. **Enable CICD**: Set up GitHub Actions or CodePipeline

See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment.
