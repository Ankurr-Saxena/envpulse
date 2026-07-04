# EnvPulse Development Guide

Contributing to EnvPulse and extending its capabilities.

## Development Environment Setup

### Prerequisites
- Python 3.9+
- AWS CLI configured
- Docker (for running Grafana/Athena locally)
- Git

### Local Setup

```bash
# Clone repository
git clone https://github.com/your-org/envpulse.git
cd envpulse

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
pip install -r lambda/requirements.txt
pip install -r api-probes/requirements.txt
pip install -r ui-probes/requirements.txt

# Install dev dependencies
pip install pytest pytest-cov black flake8 mypy boto3-stubs
```

### Configure Local AWS Environment

```bash
# Use AWS CLI test credentials
export AWS_ACCESS_KEY_ID=testing
export AWS_SECRET_ACCESS_KEY=testing
export AWS_SECURITY_TOKEN=testing
export AWS_SESSION_TOKEN=testing
export AWS_DEFAULT_REGION=us-east-1

# Or use localstack for local AWS services
docker-compose -f docker/docker-compose.yml up
```

## Project Structure

```
envpulse/
├── lambda/
│   ├── monitor.py              # Main Lambda handler
│   ├── alerter.py              # Alert formatting
│   ├── queries.py              # SQL query templates
│   └── requirements.txt
├── api-probes/
│   ├── runner.py               # Probe executor
│   ├── probes/
│   │   ├── http_probe.py       # HTTP/REST checks
│   │   ├── graphql_probe.py    # GraphQL queries
│   │   └── custom_probe.py     # Custom probe logic
│   └── requirements.txt
├── ui-probes/
│   ├── runner.py               # Playwright runner
│   ├── tests/
│   │   ├── auth_flow.py        # Authentication tests
│   │   ├── checkout_flow.py    # Purchase flow
│   │   └── ui_tests.py         # UI component tests
│   └── requirements.txt
├── config/
│   ├── environments.yaml       # Environment definitions
│   ├── probes.yaml             # Probe configurations
│   └── thresholds.yaml         # Alert thresholds
├── athena/
│   ├── schema.sql              # Database schema
│   ├── queries/                # SQL queries
│   └── setup.sh                # Setup script
├── grafana/
│   ├── dashboards/             # Dashboard JSON
│   └── provisioning/           # Datasource configs
├── terraform/
│   ├── main.tf
│   ├── lambda.tf
│   ├── variables.tf
│   └── terraform.tfvars.example
├── tests/                      # Integration tests
│   ├── test_lambda.py
│   ├── test_probes.py
│   └── fixtures/
├── docs/                       # Documentation
└── README.md
```

## Code Style & Standards

### Python Code Style (PEP 8)

```bash
# Format code with Black
black --line-length 88 lambda/ api-probes/ ui-probes/

# Lint with Flake8
flake8 lambda/ api-probes/ ui-probes/ --max-line-length=88

# Type checking with mypy
mypy lambda/ api-probes/ ui-probes/
```

### Naming Conventions

- **Functions**: `snake_case` - `run_query()`, `send_alert()`
- **Classes**: `PascalCase` - `ProbeRunner`, `AthenaClient`
- **Constants**: `UPPER_SNAKE_CASE` - `ALERT_THRESHOLD`, `MAX_RETRIES`
- **Private methods**: `_leading_underscore` - `_parse_result()`

### Documentation

All functions must have docstrings:

```python
def analyze_failures(signals: List[Dict]) -> List[Alert]:
    """
    Analyze signals and identify failures requiring alerts.
    
    Args:
        signals: List of signal dictionaries from Athena
        
    Returns:
        List of Alert objects to be sent
        
    Raises:
        ValueError: If signal format is invalid
        
    Example:
        >>> signals = [{'status': 'FAIL', 'environment': 'prod'}]
        >>> alerts = analyze_failures(signals)
        >>> len(alerts)
        1
    """
    # Implementation
    pass
```

## Testing

### Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=lambda --cov=api-probes --cov=ui-probes

# Run specific test
pytest tests/test_lambda.py::test_lambda_handler -v
```

### Test Examples

```python
# tests/test_monitor.py
import pytest
from lambda import monitor

def test_lambda_handler_success(monkeypatch):
    """Test Lambda handler with successful query."""
    mock_event = {'source': 'aws.events'}
    mock_context = type('Context', (), {'function_name': 'envpulse-monitor'})()
    
    # Mock Athena response
    monkeypatch.setenv('SLACK_WEBHOOK_URL', 'https://hooks.slack.com/test')
    
    response = monitor.lambda_handler(mock_event, mock_context)
    
    assert response['statusCode'] == 200
    assert 'status' in response['body']

def test_lambda_handler_athena_failure(monkeypatch):
    """Test Lambda handler when Athena query fails."""
    monkeypatch.setenv('SLACK_WEBHOOK_URL', '')
    
    response = monitor.lambda_handler({}, None)
    
    assert response['statusCode'] in [400, 502]

def test_parse_results():
    """Test result parsing from Athena."""
    rows = [
        {'Data': [{'VarCharValue': 'environment'}, {'VarCharValue': 'count'}]},
        {'Data': [{'VarCharValue': 'prod'}, {'VarCharValue': '5'}]},
    ]
    
    alerts = monitor.parse_results(rows)
    
    assert len(alerts) == 1
    assert alerts[0] == ('prod', 5)
```

### Integration Tests

```bash
# Test with localstack
docker-compose -f docker/docker-compose.yml up

# Run integration tests
pytest tests/integration/ -v
```

## Adding New Features

### Adding a New Probe Type

1. **Create probe module**:

```python
# api-probes/probes/soap_probe.py

from abc import ABC, abstractmethod
from typing import Dict, Any

class Probe(ABC):
    """Base class for all probes."""
    
    @abstractmethod
    def run(self) -> Dict[str, Any]:
        """Execute probe and return results."""
        pass

class SoapProbe(Probe):
    """SOAP service endpoint probe."""
    
    def __init__(self, endpoint_url: str, method: str, payload: str):
        self.endpoint_url = endpoint_url
        self.method = method
        self.payload = payload
    
    def run(self) -> Dict[str, Any]:
        """Execute SOAP request."""
        # Implementation
        return {
            'status': 'PASS',
            'response_time_ms': 123,
            'timestamp': datetime.utcnow().isoformat()
        }
```

2. **Register probe in runner**:

```python
# api-probes/runner.py

PROBE_TYPES = {
    'http': HttpProbe,
    'graphql': GraphqlProbe,
    'soap': SoapProbe,  # Add new type
}
```

3. **Add configuration**:

```yaml
# config/probes.yaml

probes:
  - id: legacy-soap-service
    type: soap
    environment: production
    endpoint_url: https://legacy.example.com/service
    method: GetStatus
    payload: |
      <soap:Envelope>...</soap:Envelope>
```

4. **Test the probe**:

```python
# tests/test_soap_probe.py

def test_soap_probe():
    probe = SoapProbe(
        endpoint_url='https://legacy.example.com/service',
        method='GetStatus',
        payload='<soap:Envelope>...</soap:Envelope>'
    )
    
    result = probe.run()
    
    assert result['status'] == 'PASS'
    assert 'response_time_ms' in result
```

### Adding New Athena Queries

1. **Add query to queries.py**:

```python
# lambda/queries.py

QUERY_UPTIME_BY_SERVICE = """
    SELECT
        environment,
        service,
        ROUND(100.0 * SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) / COUNT(*), 2) as uptime_pct
    FROM signals
    WHERE year = {year} AND month = {month} AND day = {day}
    GROUP BY environment, service
"""

def get_uptime_query(year: int, month: int, day: int) -> str:
    return QUERY_UPTIME_BY_SERVICE.format(year=year, month=month, day=day)
```

2. **Use in Lambda handler**:

```python
# lambda/monitor.py

from queries import get_uptime_query

query = get_uptime_query(2024, 1, 28)
query_id = run_query(query)
```

### Adding New Alert Channels

1. **Create alerter module**:

```python
# lambda/alerters/pagerduty.py

import requests

class PagerDutyAlerter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = 'https://api.pagerduty.com'
    
    def send_alert(self, alert: Alert) -> bool:
        payload = {
            'routing_key': self.api_key,
            'event_action': 'trigger',
            'payload': {
                'summary': alert.message,
                'severity': alert.severity,
                'source': 'EnvPulse'
            }
        }
        
        response = requests.post(
            f'{self.base_url}/enqueue',
            json=payload
        )
        
        return response.status_code == 202
```

2. **Register alerter**:

```python
# lambda/monitor.py

from alerters.pagerduty import PagerDutyAlerter

ALERTERS = {
    'slack': SlackAlerter,
    'pagerduty': PagerDutyAlerter,
}
```

## Git Workflow

### Branch Naming

```
feature/new-probe-type     # New feature
bugfix/alert-parsing       # Bug fix
hotfix/urgent-fix          # Production hotfix
docs/update-readme         # Documentation
```

### Commit Messages

```
feat: Add SOAP probe support
fix: Handle missing environment in results
docs: Update setup guide
test: Add unit tests for alerter
chore: Update dependencies
```

### Pull Request Process

1. Create feature branch: `git checkout -b feature/amazing-feature`
2. Make changes and test: `pytest tests/`
3. Format code: `black lambda/`
4. Commit: `git commit -m 'feat: Add feature'`
5. Push: `git push origin feature/amazing-feature`
6. Open pull request with:
   - Clear description
   - Link to related issue
   - Test coverage
   - Documentation updates

### Code Review Guidelines

- At least 2 approvals required
- All tests must pass
- Code coverage > 80%
- No hardcoded secrets
- Documentation updated

## Performance Optimization

### Athena Query Optimization

```python
# ❌ Bad: Scans entire table
SELECT * FROM signals WHERE status = 'FAIL'

# ✅ Good: Partition pruning
SELECT * FROM signals 
WHERE status = 'FAIL'
  AND year = 2024 AND month = 1 AND day = 28
  AND from_iso8601_timestamp(timestamp) > current_timestamp - interval '1' hour
```

### Lambda Performance Tuning

```python
# Use connection pooling
http = urllib3.PoolManager(
    timeout=urllib3.Timeout(connect=5.0, read=10.0),
    maxsize=10
)

# Batch process results
def batch_process(items, batch_size=100):
    for i in range(0, len(items), batch_size):
        yield items[i:i+batch_size]
```

## Debugging

### Local Lambda Testing

```bash
# Use AWS SAM to test locally
sam local start-api
sam local invoke -e event.json

# Or use LocalStack
docker-compose up
python -m lambda.monitor
```

### CloudWatch Logs

```bash
# View logs in real-time
aws logs tail /aws/lambda/envpulse-monitor --follow

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/envpulse-monitor \
  --filter-pattern "ERROR"
```

### Debug Configuration

```python
# Set debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Add tracing
import aws_lambda_powertools
logger = aws_lambda_powertools.Logger()
logger.info('Debug information', extra={'key': 'value'})
```

## Documentation

### Writing Documentation

- Use Markdown format
- Include examples
- Update table of contents
- Add diagrams where helpful
- Link to related docs

### Example Documentation

````markdown
# Feature: Custom Probes

## Overview
Custom probes allow...

## Configuration
```yaml
probe_type: custom
handler: my_probe.py:check_status
```

## Example
```python
def check_status():
    return {'status': 'PASS'}
```

## Testing
```bash
pytest tests/test_custom_probe.py
```
````

## Release Process

1. Update version: `__version__ = '1.2.0'`
2. Update CHANGELOG.md
3. Create git tag: `git tag v1.2.0`
4. Push: `git push origin --tags`
5. Create GitHub release with notes
6. Deploy to production

## Support & Questions

- Post questions in Slack #envpulse-dev
- File issues on GitHub
- Review existing PRs for examples
- Reach out to maintainers

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues.
