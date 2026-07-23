# 🚀 EnvPulse – Environment Observability & Alerting Platform

## 🔍 Overview
EnvPulse is a **cloud-native environment observability platform built on AWS**, designed to monitor environment availability, detect instability, and provide proactive alerting across Development, UAT, and Production environments.

## 🎯 Objectives
- ✅ Monitor environment availability continuously
- ✅ Detect instability and degradation in real-time
- ✅ Provide observable dashboards with historical trends
- ✅ Trigger intelligent, context-rich alerts
- ✅ Enable correlation between environments and services


## 🧠 Signal Types

EnvPulse processes multiple signal categories:

| Signal Type | Description | Frequency | Sample Data |
|---|---|---|---|
| **UI Availability Probe** | Synthetic browser tests using Playwright | Every 5 min | Response time, page load, element detection |
| **API Health Probe** | HTTP/REST endpoint checks | Every 2 min | Status code, latency, payload validation |
| **Synthetic Transaction** | End-to-end workflow validation | Every 10 min | Multi-step process success rate |
| **Response Time Monitoring** | Latency tracking & thresholds | Continuous | p50, p95, p99 metrics |
| **Service Health Check** | Infrastructure & dependency status | Every 5 min | CPU, memory, disk, network |
| **Data Integrity Signal** | Lightweight database/cache validation | Hourly | Record count, checksum mismatches |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        EnvPulse Data Flow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [API Probes]  [UI Probes]  [Synthetic Tests]                   │
│        │             │              │                            │
│        └─────────────┴──────────────┘                            │
│                     ↓                                             │
│            [AWS CodeBuild Jobs]                                   │
│              (Every 5 minutes)                                   │
│                     ↓                                             │
│          [S3 Signal Logs Bucket]                                 │
│          (Partitioned by date/env)                               │
│                     ↓                                             │
│            [AWS Athena Queries]                                  │
│          (SQL analysis on signals)                               │
│                     ↓                                             │
│         [Lambda Analysis Function]                               │
│        (Every 10 min via EventBridge)                            │
│      • Failure trend analysis                                    │
│      • Threshold breaches                                        │
│      • Pattern detection                                         │
│                     ↓                                             │
│        ┌────────────┴────────────┐                               │
│        ↓                         ↓                               │
│   [Slack Alerts]           [CloudWatch Logs]                     │
│   (Rich, actionable)       (For monitoring)                      │
│        │                         │                               │
│        └────────────┬────────────┘                               │
│                     ↓                                             │
│         [Grafana Dashboard]                                      │
│      (Real-time visualization)                                   │
│      • Uptime trends                                             │
│      • Failure heatmaps                                          │
│      • Performance curves                                        │
│      • Multi-env comparison                                      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## 📊 Observability & Reporting

**Dashboards provide:**
- Environment uptime % by service
- Failure trends with root cause indicators
- Response time distribution (p50, p95, p99)
- Multi-environment comparison views
- Alert history and acknowledgments
- SLA compliance tracking

## 🚨 Alerting Logic

Alerts trigger when:
- **Consecutive failures**: ≥2 failures in last hour per environment
- **Performance degradation**: Response time > threshold for >5 min
- **Service unavailability**: Health checks fail for entire environment
- **Data anomalies**: Integrity checks exceed tolerance

Each alert includes:
- Environment name & affected service
- Current status & historical context
- Recommended action
- Runbook link (if configured)

## 📋 Prerequisites

- **AWS Account** with permissions for: IAM, S3, Athena, Lambda, EventBridge, CloudWatch
- **AWS CLI** v2+ configured
- **Python** 3.9+
- **Git** for version control
- **Slack Workspace** (for alerts) or email fallback
- **Grafana** instance (cloud or self-hosted) for dashboards

## 🚀 Quick Start

### 1. Clone & Setup
```bash
git clone https://github.com/your-org/envpulse.git
cd envpulse
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure AWS
```bash
aws configure
# Enter: Access Key ID, Secret Access Key, Region (us-east-1), Output (json)
```

### 3. Deploy Infrastructure
```bash
# Option A: Using AWS SAM
sam build
sam deploy --guided

# Option B: Using Terraform
cd terraform/
terraform init
terraform plan
terraform apply
```

### 4. Deploy Lambda Function
```bash
cd lambda/
pip install -r requirements.txt -t .
zip -r function.zip . -x '*.git*'
aws lambda update-function-code --function-name envpulse-monitor --zip-file fileb://function.zip
```

### 5. Configure Alerts
```bash
# Set environment variables in Lambda console or local .env:
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
export ALERT_THRESHOLD=2  # Failures to trigger alert
export FAILURE_WINDOW_MINUTES=60
```

### 6. Run Probes
```bash
# Trigger API probes
python api-probes/runner.py --environment dev

# Trigger UI probes
python ui-probes/runner.py --environment dev
```

## 📁 Directory Structure

```
envpulse/
├── api-probes/              # HTTP/REST endpoint monitors
│   ├── runner.py            # Probe orchestrator
│   ├── probes.yaml          # Endpoint configurations
│   └── requirements.txt
├── ui-probes/               # Browser-based synthetic tests (Playwright)
│   ├── runner.py            # Browser test orchestrator
│   ├── tests/               # Playwright test files
│   └── requirements.txt
├── lambda/                  # Analysis & alerting function
│   ├── monitor.py           # Main Lambda handler
│   ├── alerter.py           # Alert formatting & delivery
│   ├── queries.py           # Athena query templates
│   └── requirements.txt
├── athena/                  # Database schema & queries
│   ├── schema.sql           # Signals table definition
│   ├── queries/             # Reusable SQL templates
│   └── setup.sh             # Athena database setup
├── grafana/                 # Dashboard definitions
│   ├── dashboards/          # JSON dashboard exports
│   └── provisioning/        # Grafana datasource configs
├── config/                  # Configuration templates
│   ├── environments.yaml    # Environment definitions
│   ├── thresholds.yaml      # Alert thresholds
│   └── probes.yaml          # Probe configurations
├── terraform/               # Infrastructure as Code
│   ├── main.tf
│   ├── variables.tf
│   ├── lambda.tf
│   ├── athena.tf
│   └── terraform.tfvars.example
├── docs/                    # Documentation
│   ├── SETUP.md
│   ├── DEPLOYMENT.md
│   ├── DEVELOPMENT.md
│   └── TROUBLESHOOTING.md
└── sample-signals/          # Example data for testing
    ├── signals.json
    └── load-test.py
```

## ⚙️ Tech Stack

| Component | Technology | Purpose |
|---|---|---|
| **Probes** | Playwright, Python requests | Synthetic monitoring |
| **Orchestration** | AWS CodeBuild | Scheduled probe execution |
| **Data Storage** | AWS S3 | Signal logs & metadata |
| **Analysis** | AWS Athena | SQL queries on signals |
| **Processing** | AWS Lambda | Trend analysis & alerts |
| **Notifications** | Slack Webhooks, SNS | Alert delivery |
| **Visualization** | Grafana, CloudWatch | Real-time dashboards |
| **IaC** | Terraform, AWS SAM | Infrastructure automation |

## 🌍 Environment Support

Designed for multi-environment monitoring:
- **Development** - Frequent changes, relaxed thresholds
- **QA/UAT** - Staging validation, moderate thresholds
- **Staging** - Production-like, strict thresholds
- **Production** - Mission-critical, immediate alerts
- **Custom** - Any environment with defined probes

## 🔐 Security Best Practices

- ✅ **Secrets Management**: Use AWS Secrets Manager for Slack webhooks, API keys
- ✅ **IAM Least Privilege**: Lambda role has minimal S3, Athena permissions
- ✅ **VPC Isolation**: Lambda can run in VPC for private endpoint access
- ✅ **Encryption**: S3 buckets use SSE-S3, Athena results encrypted
- ✅ **Audit Logging**: CloudTrail enabled for all Lambda executions
- ✅ **No Hardcoded Secrets**: Configuration via environment variables

## 📈 Scaling & Performance

- **Probe Frequency**: Configurable (2-60 min intervals)
- **Parallel Execution**: CodeBuild runs multiple probes simultaneously
- **Query Optimization**: Athena partitioned by date/environment
- **Lambda Efficiency**: Batch processing, connection pooling
- **Cost Optimization**: Partition pruning, S3 lifecycle policies

## 🐛 Troubleshooting

Common issues & solutions:

| Issue | Cause | Solution |
|---|---|---|
| Lambda timeout | Athena query slow | Optimize queries, reduce time window |
| Missing alerts | Slack webhook invalid | Verify webhook URL in Secrets Manager |
| High AWS costs | Too frequent probes | Increase probe interval in CodeBuild schedule |
| No data in dashboards | Athena table not created | Run `athena/setup.sh` |

See [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) for more.

## 📚 Documentation

- **[SETUP.md](docs/SETUP.md)** - Detailed setup instructions
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Production deployment guide
- **[DEVELOPMENT.md](docs/DEVELOPMENT.md)** - Contributing & extending
- **[API.md](docs/API.md)** - Lambda & probe APIs
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Deep dive into design decisions

## 🤝 Contributing

We welcome contributions! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [DEVELOPMENT.md](docs/DEVELOPMENT.md) for development guidelines.

## 📝 License

This project is licensed under the MIT License - see LICENSE file for details.

## ⚠️ Disclaimer

This is a **generalized prototype** showcasing architecture and approach. No proprietary systems are used. It's designed as a foundation for:
- Enterprise observability platforms
- Environment health dashboards
- Multi-tenant monitoring systems
- Custom alert orchestration

**Production Use**: Requires:
- Security hardening (secrets management, IAM policies)
- Load testing & performance tuning
- Disaster recovery planning
- Team training & runbooks

## 🆘 Support

- 💬 **LinkedIn**: [Ankurr Saxena](https://www.linkedin.com/in/ankurr-saxena/)
