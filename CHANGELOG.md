# EnvPulse Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-28

### Added
- ✨ **API Probe Runner** - HTTP/REST endpoint monitoring with support for:
  - GET/POST/PUT/DELETE methods
  - Custom headers and authentication (Bearer, API Key, Basic Auth)
  - Response validation (status code, body, headers, JSON schema)
  - Automatic retries with configurable delays
  - Performance metrics collection
  - Error handling and detailed logging

- ✨ **UI Probe Runner** - Browser-based synthetic tests using Playwright:
  - Multi-browser support (Chromium, Firefox, WebKit)
  - 11+ action types (navigate, fill, click, wait, assert, etc.)
  - Screenshot capture on failure
  - Step-by-step execution tracking
  - Performance metrics

- ✨ **Lambda Monitor Function** - Production-grade analysis and alerting:
  - Athena query execution with timeout handling
  - Configurable alert thresholds
  - Rich Slack alert formatting with context
  - Comprehensive error handling (8 error types)
  - Structured JSON responses
  - Retry logic with exponential backoff
  - Full docstring documentation

- 📚 **Comprehensive Documentation**:
  - SETUP.md - 12-step setup guide
  - DEPLOYMENT.md - Multi-environment deployment strategies
  - DEVELOPMENT.md - Contributing and extending guide
  - SETUP.md - Database schema and queries

- ⚙️ **Configuration Management**:
  - environments.yaml - Environment definitions
  - probes.yaml - API probe configurations
  - ui-tests.yaml - UI test definitions
  - thresholds.yaml - Alert thresholds

- 📊 **Grafana Dashboards**:
  - Main dashboard with Lambda metrics
  - CloudWatch integration
  - Provisioning templates

- 📋 **Database Setup**:
  - Athena schema with partitioning
  - Daily summary tables
  - Example queries
  - setup.sh automation script

- 🎬 **Sample Data & Utilities**:
  - Sample signals generator
  - Pre-configured test data
  - CLI health check utility
  - Local test runner

### Features
- Zero hardcoded secrets (environment variable configuration)
- AWS Secrets Manager integration
- Multi-environment support (dev, staging, prod)
- S3 result storage with partitioning
- Structured logging with configurable levels
- Type hints for IDE support
- Full error traceability

### Security
- IAM least privilege patterns
- Secrets Manager usage examples
- VPC isolation recommendations
- SSL/TLS throughout
- CloudTrail audit logging

### Infrastructure
- Terraform examples (IaC-ready)
- CloudFormation templates
- AWS SAM support
- EventBridge scheduling

## [Unreleased]

### Planned
- [ ] PagerDuty integration
- [ ] Email alerting
- [ ] MS Teams webhooks
- [ ] Anomaly detection
- [ ] SLA tracking
- [ ] Machine learning-based thresholds
- [ ] Multi-cloud support (Azure, GCP)
- [ ] Advanced reporting
- [ ] Custom webhook support

---

For more information, visit:
- [GitHub Repository](https://github.com/your-org/envpulse)
- [Documentation](docs/)
- [Contributing Guide](docs/DEVELOPMENT.md)
