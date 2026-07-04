# Contributing to EnvPulse

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing.

## Code of Conduct

- Be respectful and inclusive
- Focus on the code, not the person
- Welcome diverse perspectives
- Help others learn and grow

## Getting Started

1. **Fork** the repository
2. **Clone** your fork: `git clone https://github.com/YOUR-USERNAME/envpulse.git`
3. **Create** a feature branch: `git checkout -b feature/amazing-feature`
4. **Setup** dev environment: See [DEVELOPMENT.md](docs/DEVELOPMENT.md)

## Development Workflow

### Before You Start

- Check existing issues and PRs
- Open an issue to discuss major changes
- For small fixes, you can go straight to PR

### Code Standards

- **Python**: PEP 8 style via Black (88 char line length)
- **Type hints**: All functions should have type hints
- **Docstrings**: Google-style docstrings required
- **Tests**: 80%+ code coverage target
- **Logging**: Use structured logging

### Testing

```bash
# Run all tests
pytest tests/ -v --cov

# Run specific test
pytest tests/test_monitor.py::test_lambda_handler -v

# Check coverage
pytest --cov=lambda --cov-report=html
```

### Committing Changes

Use conventional commits:
```
feat: Add new feature
fix: Fix bug
docs: Update documentation
test: Add tests
chore: Update dependencies
refactor: Restructure code
```

Examples:
```bash
git commit -m "feat: Add PagerDuty alerting support"
git commit -m "fix: Handle missing environment in results"
git commit -m "docs: Update SETUP.md with new steps"
```

### Pull Request Process

1. **Update** documentation if needed
2. **Add** tests for new features
3. **Run** linting and tests locally
4. **Create** PR with clear description
5. **Link** related issues
6. **Await** review (be patient!)

### PR Requirements

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted with Black
- [ ] No hardcoded secrets
- [ ] Follows code standards
- [ ] CI/CD passes
- [ ] 2+ approvals required

## Reporting Bugs

Create an issue with:
- **Title**: Clear, descriptive
- **Reproduction**: Step-by-step
- **Expected**: What should happen
- **Actual**: What actually happened
- **Environment**: OS, Python version, AWS region
- **Logs**: Error logs, screenshots, etc.

## Feature Requests

Describe:
- **Problem**: What problem does this solve?
- **Solution**: How would you implement it?
- **Alternatives**: Other approaches considered?
- **Impact**: Who benefits? Effort required?

## Documentation

- **README.md**: Project overview
- **docs/SETUP.md**: Setup instructions
- **docs/DEPLOYMENT.md**: Deployment guide
- **docs/DEVELOPMENT.md**: Developer guide
- **Code comments**: Explain WHY, not WHAT

## Review Process

Maintainers will:
1. Check code quality and tests
2. Verify security (no hardcoded secrets)
3. Ensure documentation is updated
4. Request changes if needed
5. Merge when approved

## Community

- 📧 **Email**: devops@example.com
- 💬 **Slack**: #envpulse-community
- 🐛 **Issues**: GitHub Issues
- 💡 **Discussions**: GitHub Discussions

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for making EnvPulse better! 🎉
