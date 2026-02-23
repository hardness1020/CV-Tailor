# Testing Environments Guide

**⚠️ This document has been consolidated. For comprehensive testing guidance, see:**

## Primary Testing Documentation

📖 **[Backend Testing Guide](../testing/test-backend-guide.md)** - Complete testing reference

The Backend Testing Guide covers:
- ✅ Test execution strategies (fast, integration, e2e)
- ✅ **Proper mocking for unit tests** (critical for fast execution)
- ✅ Test organization and tagging
- ✅ Environment-specific testing
- ✅ Performance benchmarks
- ✅ Troubleshooting common issues
- ✅ CI/CD integration examples

## Quick Reference

### Test Commands

```bash
# Fast unit tests (< 1 minute with proper mocking)
docker-compose exec backend uv run python manage.py test --tag=fast --tag=unit --keepdb

# Integration tests
docker-compose exec backend uv run python manage.py test --tag=medium --tag=integration --keepdb

# All tests excluding slow ones (CI/CD recommended)
docker-compose exec backend uv run python manage.py test --exclude-tag=slow --exclude-tag=real_api --keepdb
```

### Environment-Specific Testing

Testing works across all Django environments (development, test, production):

- **Development**: Uses PostgreSQL + Redis (Docker)
- **Test**: Uses SQLite (in-memory) for speed
- **Production**: Uses RDS + ElastiCache (with mock secrets for testing)

All tests automatically use the `test` environment settings which are optimized for:
- Fast execution (in-memory database)
- No external dependencies (mocked APIs)
- Minimal logging (reduce noise)

---

**For detailed testing instructions, examples, and best practices:**

👉 **See [Backend Testing Guide](../testing/test-backend-guide.md)**

---

## Related Documentation

- **[Local Development](./local-development.md)** - Development environment setup
- **[Deployment Guide](./README.md)** - Production deployment
- **[Architecture Overview](./architecture.md)** - System architecture

---

**Last Updated**: October 2025
**Status**: Consolidated - Primary testing documentation moved to ../testing/test-backend-guide.md
