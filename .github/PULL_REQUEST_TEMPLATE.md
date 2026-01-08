## Description

<!-- Provide a brief description of your changes -->

## Related Issues

<!-- Link any related issues using "Fixes #123" or "Closes #123" -->

Fixes #

## Type of Change

<!-- Mark the appropriate option with an "x" -->

- [ ] 🐛 Bug fix (non-breaking change that fixes an issue)
- [ ] ✨ New feature (non-breaking change that adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update
- [ ] 🔧 Configuration change
- [ ] ♻️ Code refactoring (no functional changes)
- [ ] 🎨 Style/UI changes
- [ ] ⚡ Performance improvement
- [ ] ✅ Test updates
- [ ] 🔒 Security fix

## Changes Made

<!-- Describe your changes in detail -->

- Change 1
- Change 2
- Change 3

## Screenshots / Demo

<!-- If applicable, add screenshots or a short video demonstrating your changes -->

| Before | After |
|--------|-------|
| (screenshot) | (screenshot) |

## Testing

<!-- Describe how you tested your changes -->

### Test Configuration

- **OS:** 
- **Python version:** 
- **Node version:** 
- **Docker version:** 

### Tests Performed

- [ ] Unit tests pass locally (`pytest`)
- [ ] Integration tests pass locally
- [ ] Manual testing performed
- [ ] Tested with sample invoices
- [ ] Tested in Docker environment

### Test Commands Run

```bash
# Commands you ran to test
pytest tests/
npm run test
docker-compose up --build
```

## Checklist

### Code Quality

- [ ] My code follows the project's code style guidelines
- [ ] I have run `black` and `flake8` for Python code
- [ ] I have run `prettier` and `eslint` for TypeScript/JavaScript code
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] My changes generate no new warnings or errors

### Documentation

- [ ] I have updated the documentation accordingly
- [ ] I have updated the README if needed
- [ ] I have added/updated docstrings for new/modified functions
- [ ] I have updated the API documentation if endpoints changed

### Testing

- [ ] I have added tests that prove my fix is effective or my feature works
- [ ] New and existing unit tests pass locally with my changes
- [ ] Test coverage has not decreased

### Database

- [ ] No database migrations required
- [ ] I have created necessary database migrations (Alembic)
- [ ] Migrations are backward compatible
- [ ] I have tested migrations (up and down)

### Security

- [ ] I have not introduced any security vulnerabilities
- [ ] Sensitive data is not logged or exposed
- [ ] Input validation is properly implemented
- [ ] Authentication/authorization is properly checked

### Breaking Changes

<!-- If this is a breaking change, describe the impact and migration path -->

- [ ] This PR does NOT contain breaking changes
- [ ] This PR contains breaking changes (described below)

**Breaking change description:**

**Migration guide:**

## Performance Impact

<!-- If applicable, describe any performance implications -->

- [ ] No significant performance impact
- [ ] Performance improvement (describe below)
- [ ] Potential performance regression (describe and justify below)

## Dependencies

<!-- List any new dependencies added -->

- [ ] No new dependencies
- [ ] New dependencies added (listed below)

**New dependencies:**
- `package-name` - Reason for adding

## Deployment Notes

<!-- Any special deployment considerations? -->

- [ ] No special deployment steps required
- [ ] Special deployment steps required (described below)

**Deployment steps:**

## Additional Notes

<!-- Any additional information that reviewers should know -->

---

## Reviewer Checklist

<!-- For reviewers to complete -->

- [ ] Code follows project conventions
- [ ] Tests are adequate and pass
- [ ] Documentation is updated
- [ ] No security concerns
- [ ] Changes are backward compatible (or properly documented)
- [ ] PR title follows conventional commits format
