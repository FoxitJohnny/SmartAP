# Release Notes Template

Use this template when creating manual release notes.

---

## SmartAP v{VERSION}

**Release Date:** {DATE}

### Highlights

{Brief summary of the most important changes in this release}

### ✨ New Features

- {Feature 1}
- {Feature 2}

### 🐛 Bug Fixes

- {Bug fix 1}
- {Bug fix 2}

### ⚡ Performance Improvements

- {Performance improvement 1}

### 🔒 Security Updates

- {Security update 1}

### 📚 Documentation

- {Documentation update 1}

### 🔧 Other Changes

- {Other change 1}

### ⚠️ Breaking Changes

- {Breaking change 1 - include migration guide}

### 📦 Dependencies

- Updated {dependency} from {old_version} to {new_version}

---

### Docker Images

```bash
# Pull the latest images
docker pull ghcr.io/smartap/backend:{VERSION}
docker pull ghcr.io/smartap/frontend:{VERSION}

# Or use docker-compose
docker-compose pull
docker-compose up -d
```

### Helm Chart

```bash
# Add/update the Helm repository
helm repo add smartap https://smartap.github.io/smartap
helm repo update

# Install/upgrade
helm upgrade --install smartap smartap/smartap --version {VERSION}
```

### Upgrade Guide

1. **Backup your data**
   ```bash
   pg_dump -h localhost -U smartap smartap > backup.sql
   ```

2. **Update images**
   ```bash
   docker-compose pull
   docker-compose up -d
   ```

3. **Run migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

4. **Verify the upgrade**
   - Check the health endpoint: `GET /api/health`
   - Verify version: `GET /api/version`

### Known Issues

- {Known issue 1}

### Contributors

Thanks to all contributors who made this release possible!

{@contributor1, @contributor2, ...}

---

**Full Changelog**: https://github.com/smartap/smartap/compare/v{PREVIOUS_VERSION}...v{VERSION}
