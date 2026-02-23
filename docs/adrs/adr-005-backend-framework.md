# ADR: Choose Django DRF over FastAPI for Backend Framework

**File:** docs/adrs/adr-005-backend-framework.md
**Status:** Draft

## Context

The CV & Cover-Letter Auto-Tailor system requires a robust backend framework that can handle:
- Complex user authentication and authorization
- File upload and processing workflows
- Integration with external LLM APIs
- Database operations with transactions
- Admin interface for content management
- API documentation and testing

The main candidates are Django DRF (Django REST Framework) and FastAPI. The team needs to decide which framework will best support the system's requirements for rapid development, maintainability, and long-term scalability while handling 10,000+ concurrent users.

Key considerations:
- Development velocity and time-to-market
- Built-in admin and authentication systems
- ORM stability and migration management
- Async processing capabilities
- Community ecosystem and documentation
- Performance under load

## Decision

Adopt **Django DRF** as the primary backend framework for the CV Auto-Tailor system.

Rationale:
1. **Rapid Development**: Django's batteries-included approach provides immediate access to admin interface, user authentication, and ORM without additional configuration
2. **Mature Ecosystem**: Extensive third-party packages for file handling, API documentation, and Celery integration
3. **Built-in Security**: CSRF protection, SQL injection prevention, and secure user session management out of the box
4. **Admin Interface**: Essential for managing users, artifacts, and monitoring system health without building custom tooling
5. **ORM Stability**: Django's mature ORM with robust migration system handles complex schema evolution better than SQLAlchemy alternatives
6. **Team Familiarity**: Development team has extensive Django experience, reducing ramp-up time

## Consequences

### Positive
+ **Faster MVP Development**: Built-in admin, auth, and ORM reduce initial development time by ~40%
+ **Security by Default**: Django's security model prevents common vulnerabilities without additional configuration
+ **Rich Ecosystem**: Extensive packages for file uploads (django-storages), API docs (drf-spectacular), and async tasks (django-celery-beat)
+ **Scalability Proven**: Django handles high-traffic applications (Instagram, Pinterest) with proper architecture
+ **Testing Framework**: Comprehensive testing tools with database transaction rollback and factory patterns

### Negative
- **Slightly Higher Memory Footprint**: Django's feature richness increases baseline memory usage vs FastAPI
- **Async Complexity**: While Django 4+ supports async views, full async adoption requires careful ASGI configuration
- **Opinionated Structure**: Django's conventions may limit architectural flexibility for some microservice patterns
- **Learning Curve**: New team members need Django-specific knowledge vs more generic Python patterns

## Alternatives

### FastAPI
**Pros**: Native async support, automatic OpenAPI docs, better raw performance, modern Python typing
**Cons**: No built-in admin, requires additional packages for auth/ORM, smaller ecosystem, team ramp-up time

**Verdict**: FastAPI's performance benefits don't outweigh Django's development velocity advantages for this use case

### Flask + Extensions
**Pros**: Lightweight, flexible, modular approach
**Cons**: Requires assembling many components, no built-in admin, more configuration overhead

**Verdict**: Too much assembly required for rapid MVP development

### Node.js + Express
**Pros**: JavaScript ecosystem, good async performance
**Cons**: Different language from AI/ML components, less mature for complex business logic

**Verdict**: Increases complexity with multiple languages in the stack

## Rollback Plan

If Django DRF proves inadequate for performance requirements:

1. **Phase 1**: Optimize Django deployment (database connection pooling, Redis caching, async views for I/O-bound operations)
2. **Phase 2**: Extract high-throughput endpoints to FastAPI microservices while keeping Django for admin/auth
3. **Phase 3**: If full migration needed, service boundaries already defined in current architecture allow gradual replacement

**Trigger Criteria**:
- P95 response times >2s under load testing
- Memory usage >512MB per worker under normal load
- Unable to handle target 10,000 concurrent users with reasonable infrastructure

## Links

- **PRD**: `prd-20250923.md` - System requirements and scale targets
- **TECH-SPECs**: `spec-20250923-api.md`, `spec-20250923-system.md` - Backend architecture definition
- **Related ADRs**: `adr-006-database-choice.md` - PostgreSQL selection complements Django ORM choice