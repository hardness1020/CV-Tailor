# Architecture Patterns — Source of Truth for Architectural Decisions

**Purpose**: This document is the **authoritative source of truth** for all architectural patterns, design principles, and implementation standards in the CV Tailor codebase. It defines HOW to implement features consistently across the application.

**Scope**: Principle-based architectural guidance (implementation patterns, not system architecture)

**When to Use**: Reference during Stage B (Codebase Discovery), Stage C (TECH SPEC), and Stage E (FEATURE planning)

**Related Documentation**:
- **System Architecture**: See `docs/specs/spec-system.md` (WHAT exists: infrastructure, topology, SLOs)
- **API Contracts**: See `docs/specs/spec-api.md` (API endpoint specifications)
- **Multi-Environment Rationale**: See `docs/adrs/adr-029-multi-environment-settings.md`
- **Testing Guide**: See `docs/testing/test-backend-guide.md` (testing procedures)

---

## Table of Contents

### 1. Foundation Patterns (Infrastructure & Configuration)
- 1.1 [Multi-Environment Settings Pattern](#11-multi-environment-settings-pattern) ⭐ CRITICAL
- 1.2 [Custom Middleware Pattern](#12-custom-middleware-pattern)
- 1.3 [Configuration Management Pattern](#13-configuration-management-pattern)
- 1.4 [Logging & Structured Logging Pattern](#14-logging--structured-logging-pattern)

### 2. Service Layer Patterns (Business Logic Organization)
- 2.1 [Service Layer Architecture](#21-service-layer-architecture)
- 2.2 [Base Service Pattern](#22-base-service-pattern)
- 2.3 [Custom Exception Hierarchy Pattern](#23-custom-exception-hierarchy-pattern) ⭐ CRITICAL

### 3. Reliability & Resilience Patterns
- 3.1 [Circuit Breaker Pattern](#31-circuit-breaker-pattern)
- 3.2 [Task Executor Pattern](#32-task-executor-pattern)
- 3.3 [Idempotency Pattern](#33-idempotency-pattern)

### 4. Data Access Patterns
- 4.1 [Database ORM Best Practices](#41-database-orm-best-practices)
- 4.2 [Prefetch Optimization Pattern](#42-prefetch-optimization-pattern)
- 4.3 [Transaction Management Pattern](#43-transaction-management-pattern)
- 4.4 [Vector Search Pattern](#44-vector-search-pattern)
- 4.5 [File Storage & Upload Pattern](#45-file-storage--upload-pattern)

### 5. API & Serialization Patterns
- 5.1 [DRF ViewSet Pattern](#51-drf-viewset-pattern)
- 5.2 [Serializer Design Patterns](#52-serializer-design-patterns) ⭐ CRITICAL
- 5.3 [API Response Pattern](#53-api-response-pattern)

### 6. Authentication & Authorization Patterns
- 6.1 [JWT Authentication Pattern](#61-jwt-authentication-pattern) ⭐ CRITICAL
- 6.2 [Permission Classes Pattern](#62-permission-classes-pattern)
- 6.3 [OAuth Integration Pattern](#63-oauth-integration-pattern)

### 7. Async & Background Processing Patterns
- 7.1 [Celery Task Pattern](#71-celery-task-pattern)
- 7.2 [Progress Callback Pattern](#72-progress-callback-pattern)

### 8. LLM-Specific Patterns
- 8.1 [Model Registry & Selection Pattern](#81-model-registry--selection-pattern)
- 8.2 [LLM Task Configuration Pattern](#82-llm-task-configuration-pattern)
- 8.3 [Confidence Scoring Pattern](#83-confidence-scoring-pattern)
- 8.4 [Prompt Engineering Pattern](#84-prompt-engineering-pattern)

### 9. Testing Patterns
- 9.1 [Test Organization Pattern](#91-test-organization-pattern)
- 9.2 [Mocking Pattern for External Services](#92-mocking-pattern-for-external-services)

### 10. Anti-Patterns to Avoid
- 10.1 [Business Logic in Views](#101-business-logic-in-views)
- 10.2 [Hardcoded Configuration Values](#102-hardcoded-configuration-values)
- 10.3 [Success/Failure Dict Returns](#103-successfailure-dict-returns)
- 10.4 [N+1 Query Problems](#104-n1-query-problems)
- 10.5 [Duplicate Service Implementations](#105-duplicate-service-implementations)

### 11. Pattern Selection Decision Tree
### 12. Pattern Compatibility Matrix

---

## 1. Foundation Patterns (Infrastructure & Configuration)

### 1.1 Multi-Environment Settings Pattern

**⭐ CRITICAL PATTERN — Used in all deployments**

**Reference**: `backend/cv_tailor/settings/` | ADR-029

**Problem**: Need different configs for dev/test/prod without code changes or security risks.

**Solution**: Environment-based settings modules with automatic detection and inheritance.

**Principles**:
1. **Auto-Detection**: Settings auto-detect `DJANGO_ENV` (development/test/production)
2. **Inheritance**: All environments extend `base.py`
3. **Environment-Specific**: Dev (`.env`, PostgreSQL, Redis), Test (in-memory SQLite, DummyCache), Prod (Secrets Manager, RDS, ElastiCache, S3)

**Architecture**:
```
settings/
├── __init__.py     # Auto-detects DJANGO_ENV
├── base.py         # Shared (REST, JWT, Auth, LLM)
├── development.py  # DEBUG=True, Docker DB/cache, .env secrets
├── test.py         # SQLite in-memory, DummyCache, mocks
└── production.py   # DEBUG=False, RDS, ElastiCache, S3, Secrets Manager
```

**Key Differences**: Dev (local DB/cache, .env), Test (in-memory, fast), Prod (AWS services, secrets manager, HTTPS enforced)

**When to Use**: All Django projects with multiple environments, cloud deployments, fast test execution

**Benefits**: Same codebase all environments, no secrets in git, fast tests, production security defaults

**Related**: ADR-029, `docs/deployment/local-development.md`

---

### 1.2 Custom Middleware Pattern

**Reference**: `backend/cv_tailor/middleware.py`

**Problem**: Need to intercept HTTP requests for health checks, security validation, or request processing without modifying views.

**Solution**: Django middleware components that process requests before they reach views.

**Principles**:
1. **Health Check Bypass**: Skip authentication for ALB/load balancer health checks
2. **Security Headers**: Add CORS, CSP, or security headers
3. **Request Context Enrichment**: Add common data to requests (user context, tenant ID)

**Use Cases**: Health check bypass, CORS handling, request/response logging, JWT validation, security headers

**Pattern**:
```python
class CustomMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process REQUEST (before view)
        response = self.get_response(request)
        # Process RESPONSE (after view)
        return response
```

**When to Use**: Cross-cutting concerns affecting all requests, health checks, logging, security headers

**Reference Implementation**: `HealthCheckMiddleware` (backend/cv_tailor/middleware.py:18)

---

### 1.3 Configuration Management Pattern

**Reference**: `llm_services/services/base/settings_manager.py`

**Problem**: Need type-safe access to environment variables with defaults and validation.

**Solution**: Settings manager with typed getters and validation.

**Principles**:
1. **Type-Safe Access**: Separate methods for int, float, string, boolean
2. **Default Values**: Optional defaults for non-critical settings
3. **Required Settings Validation**: Fail fast on missing critical configuration
4. **Environment Variable Only**: Never hardcode secrets or environment-specific values

**Pattern**:
```python
# Type-safe configuration access
settings.get_string('DEFAULT_MODEL', default='gpt-4')
settings.get_int('MAX_RETRIES', default=3)
settings.get_float('API_TIMEOUT', default=30.0)
settings.get_bool('ENABLE_FEATURE', default=False)
```

**When to Use**:
- Reading environment variables
- Configuration with type requirements
- Optional vs required settings

**Anti-Pattern**: `os.environ.get('KEY')` without type conversion or validation

---

### 1.4 Logging & Structured Logging Pattern

**Reference**: `backend/cv_tailor/settings/development.py:177`, `production.py:334`, `middleware.py:68`

**Problem**: Need consistent logging across environments with appropriate detail, context, and security.

**Solution**: Environment-specific logging with structured formats and context injection.

**Principles**:
1. **Environment-Specific**: Dev (DEBUG, console+file), Test (ERROR, minimal), Production (INFO, JSON to CloudWatch)
2. **Structured**: JSON for production (machine-readable), readable for development
3. **Context Injection**: Include user_id, job_id, request_id in all log messages
4. **Security**: Never log secrets, PII, full request bodies, API keys, or tokens
5. **Performance**: Minimal logging in tests for speed

**What to Log**: Security events, external API calls, errors (with stack traces), performance metrics, circuit breaker states
**What NOT to Log**: Secrets, PII, full request/response bodies, credentials

**Pattern**:
```python
logger = logging.getLogger(__name__)

# Basic with context
logger.info(f"Processing artifact {artifact_id} for user {user_id}")

# Error with exception
try:
    external_api.call()
except ExternalAPIError as e:
    logger.error(f"API failed", exc_info=True, extra={"user_id": user_id})
    raise

# Performance
logger.warning(f"Slow operation: {duration:.2f}s", extra={"duration": duration})
```

**When to Use**: All services, error handling, external API calls, performance-critical operations

**Benefits**: Consistent format, environment-appropriate verbosity, searchable (CloudWatch), security-compliant

---

## 2. Service Layer Patterns (Business Logic Organization)

### 2.1 Service Layer Architecture

**Reference**: `llm_services/services/` (best practice), `generation/services/` (in progress)

**Problem**: Business logic mixed into views/serializers creates tight coupling, duplication, and testing difficulties.

**Solution**: Layered service architecture with clear separation of concerns.

**Principles**:
1. **Four-Layer Architecture**: base → core → infrastructure → reliability
2. **Dependency Direction**: Upper layers depend on lower layers only
3. **Single Responsibility**: Each service has one clear purpose
4. **Separation**: Pure I/O separate from business logic separate from LLM operations

**Layers**:
- **base/**: Foundation abstractions (BaseService, TaskExecutor, ExceptionHandler) | No dependencies
- **core/**: Business logic (TailoredContentService, BulletGenerationService) | Uses base/, infrastructure/
- **infrastructure/**: Technical services (ModelRegistry, DocumentLoader) | Uses base/
- **reliability/**: Fault tolerance (CircuitBreaker, PerformanceTracker) | Uses base/

**Migration**: Current (flat `services/`) → Target (layered like `llm_services/services/`) | Extract progressively: base → infrastructure → core → reliability

**Benefits**: Clear separation, easy testing (mock layers), reusable components, isolated fault tolerance

**Reference**: `llm_services/services/` for canonical implementation

---

### 2.2 Base Service Pattern

**Reference**: `llm_services/services/base/base_service.py`

**Problem**: Every service reimplements common functionality (logging, error handling, client management).

**Solution**: Abstract base service class with shared functionality that all services inherit.

**Principles**:
1. **Inheritance Model**: All services extend BaseLLMService or BaseService
2. **Shared Functionality**: Logging, client lifecycle, error handling in base class
3. **Template Method Pattern**: Base class defines workflow, subclasses implement details
4. **No Direct Instantiation**: Base classes are abstract (ABC)

**Common Base Service Responsibilities**:
- Logger initialization
- Client/connection lifecycle management
- Common error handling
- Performance/cost tracking hooks
- Validation utilities

**When to Use**:
- Creating new service classes
- Standardizing service behavior
- Sharing utilities across services

**Benefits**:
- Consistent service behavior
- Reduced code duplication
- Centralized updates to common functionality

---

### 2.3 Custom Exception Hierarchy Pattern

**⭐ CRITICAL PATTERN — Used in all error handling**

**Reference**: `backend/common/exceptions.py`

**Problem**: Generic exceptions don't convey intent, making error handling difficult.

**Solution**: Domain-specific exception hierarchy with meaningful types.

**Principles**:
1. **Single Base**: All exceptions inherit from `ServiceError`
2. **Domain-Specific**: Separate types per domain (EnrichmentError, GenerationError, LLMAPIError)
3. **Wrap Externals**: Wrap external exceptions with context
4. **Never Return Dicts**: Raise exceptions, not `{"success": False}`
5. **Include Context**: Add user_id, job_id, artifact_id to messages

**Hierarchy**: `ServiceError` → `EnrichmentError` (EmbeddingGenerationError, ContentExtractionError), `GenerationError` (BulletGenerationError, ValidationError), `LLMAPIError` (OpenAIAPIError, AnthropicAPIError), `CircuitBreakerOpen`, `ConfigurationError`

**When to Use**: Always instead of generic exceptions, external API failures, validation failures, business logic failures

**Anti-Pattern**:
```python
# ❌ DON'T: return {"success": False, "error": "..."}
# ✅ DO: raise GenerationError("...", context={"user_id": user.id})
```

**Benefits**: Clear intent, catchable by domain, full stack traces, specific error handling

**Reference**: `common/exceptions.py:1`

---

## 3. Reliability & Resilience Patterns

### 3.1 Circuit Breaker Pattern

**Reference**: `llm_services/services/reliability/circuit_breaker.py`

**Problem**: External services can fail/degrade, causing cascading failures and wasted retry attempts.

**Solution**: Circuit breaker detects failures and fails fast when service is unavailable.

**Principles**:
1. **Three States**: CLOSED (normal) → OPEN (failing) → HALF_OPEN (testing recovery)
2. **Failure Threshold**: Open after N failures (default: 5)
3. **Recovery Timeout**: Wait M seconds before testing (default: 60s)
4. **Fail Fast**: When OPEN, reject immediately without calling service
5. **Auto Recovery**: Test if service recovered (HALF_OPEN → CLOSED if success)

**When to Use**: All external APIs (OpenAI, Anthropic, GitHub, web scraping), I/O with failure potential

**Configuration**: `failure_threshold=5`, `recovery_timeout=60`, `expected_exception` (e.g., OpenAIError)

**Benefits**: Prevents cascading failures, reduces wasted API calls/costs, fast failure feedback, automatic recovery

**Reference**: `llm_services/services/reliability/circuit_breaker.py:15`

---

### 3.2 Task Executor Pattern

**Reference**: `llm_services/services/base/task_executor.py`

**Problem**: Retry logic, timeout handling, and error reporting duplicated across async operations.

**Solution**: Unified task executor with exponential backoff, timeout handling, and structured error reporting.

**Principles**:
1. **Exponential Backoff**: Retry delays increase exponentially (2s → 4s → 8s)
2. **Configurable Timeouts**: Per-task timeout limits
3. **Structured Error Logging**: Include task name, context, retry count
4. **Circuit Breaker Integration**: Respects circuit breaker state
5. **Context Propagation**: Pass user_id, job_id through execution chain

**Configuration**:
- `max_retries`: Maximum retry attempts (default: 3)
- `timeout`: Task timeout in seconds (default: 30)
- `exponential_base`: Backoff multiplier (default: 2)

**When to Use**:
- All LLM API calls
- External service integrations
- Long-running background tasks
- Any operation requiring retry logic

**Benefits**:
- Consistent retry behavior
- Reduced code duplication
- Proper timeout handling
- Integrated error logging

**Reference**: See `llm_services/services/base/task_executor.py:20`

---

### 3.3 Idempotency Pattern

**Reference**: `artifacts/tasks.py`, `generation/tasks.py`

**Problem**: Async tasks can be retried/duplicated, causing duplicate processing or data corruption.

**Solution**: Status-based idempotency guards that skip if already processed.

**Principles**:
1. **Status Guards**: Check status before processing (`if status == 'completed': skip`)
2. **Stale Detection**: Mark jobs failed if timeout exceeded
3. **Force Flag**: Allow manual override (`force=True`)
4. **Atomic Updates**: Use `select_for_update()` to prevent race conditions

**Pattern**:
```python
def process_entity(entity_id, force=False):
    entity = Entity.objects.select_for_update().get(id=entity_id)

    if entity.status == 'completed' and not force:
        logger.info(f"Skipping {entity_id}: already completed")
        return

    if entity.created_at < timezone.now() - timedelta(hours=1):
        entity.status = 'failed'
        entity.save()
        return

    entity.status = 'processing'
    entity.save()
    # ... do work ...
    entity.status = 'completed'
    entity.save()
```

**When to Use**: All Celery tasks, webhook handlers, operations with side effects (payments, emails)

**Benefits**: Safe retries, clear logging, stale cleanup, force override

**Reference**: `artifacts/tasks.py:45`, `generation/tasks.py:78`

---

## 4. Data Access Patterns

### 4.1 Database ORM Best Practices

**Problem**: Inefficient database queries cause N+1 problems, slow API responses, and high database load.

**Solution**: Use Django ORM features to minimize queries and optimize access patterns.

**Principles**:
1. **select_related for Foreign Keys**: Use joins for forward foreign key relationships
2. **prefetch_related for Reverse FKs and M2M**: Use separate queries for reverse/many relationships
3. **Query Optimization**: Always check query count in tests (`assertNumQueries`)
4. **Lazy Loading Awareness**: Avoid accessing relationships in loops
5. **Index Coverage**: Ensure filters and lookups have database indexes

**When to Use**:
- `select_related`: Forward foreign keys (artifact.user, cv.job)
- `prefetch_related`: Reverse foreign keys (user.artifacts_set), M2M relationships
- `only/defer`: When loading partial model data
- `annotate`: When computing aggregates (counts, sums)

**Anti-Pattern**: Accessing relationships in loops without prefetch
```python
# ❌ N+1 problem
for artifact in Artifact.objects.all():
    print(artifact.user.email)  # Extra query per artifact!
```

**Best Practice**:
```python
# ✅ Single query with join
for artifact in Artifact.objects.select_related('user'):
    print(artifact.user.email)  # No extra queries
```

**Reference**: Django ORM documentation

---

### 4.2 Prefetch Optimization Pattern

**Problem**: Serializers access related objects, causing N+1 queries in list views.

**Solution**: Prefetch-aware queryset design coordinated with serializers.

**Principles**:
1. **Prefetch in ViewSet**: Override `get_queryset()` with `select_related`/`prefetch_related`
2. **SerializerMethodField Awareness**: Prefetch data accessed in methods
3. **Annotate for Counts**: Use `annotate(count=Count('relation'))` instead of `.count()` in loops

**Pattern**:
```python
class ArtifactViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        return Artifact.objects.select_related('user').prefetch_related('bullet_points', 'selected_jobs')

class ArtifactSerializer(serializers.ModelSerializer):
    user_email = serializers.SerializerMethodField()
    def get_user_email(self, obj):
        return obj.user.email  # Uses prefetched data
```

**When to Use**: All list endpoints, serializers with nested relationships, SerializerMethodFields accessing relationships

**Testing**: `with self.assertNumQueries(2): self.client.get('/api/artifacts/')`

**Benefits**: Fast endpoints (constant queries), predictable performance, lower DB load

**Reference**: `artifacts/views.py:42`, `generation/views.py:67`

---

### 4.3 Transaction Management Pattern

**Problem**: Multi-step operations can leave data in inconsistent state if errors occur.

**Solution**: Use database transactions for atomic operations.

**Principles**:
1. **Atomic Decorator/Context**: `@transaction.atomic` or `with transaction.atomic():`
2. **Auto Rollback**: Transactions rollback on exceptions
3. **Avoid for Long Tasks**: Don't use for long-running Celery tasks (locks DB rows)

**Pattern**:
```python
@transaction.atomic
def create_cv_with_bullets(user, job, artifacts):
    cv = CV.objects.create(user=user, job=job)
    for artifact in artifacts:
        BulletPoint.objects.create(cv=cv, artifact=artifact)
    cv.generate_content()  # If fails, all rolled back
    return cv
```

**When to Use**: Creating multiple related objects, multi-table updates, payment operations | **Avoid**: Long Celery tasks

**Benefits**: Data consistency, automatic rollback, simplified error handling

---

### 4.4 Vector Search Pattern

**Reference**: `llm_services/services/core/embedding_service.py`

**Problem**: Need semantic similarity search for artifacts, not just keyword matching.

**Solution**: Use pgvector for cosine similarity search on embeddings.

**Principles**:
1. **Embedding Generation**: Generate embeddings for all searchable content
2. **Cosine Distance**: Use `CosineDistance` for similarity (lower = more similar)
3. **Threshold Filtering**: Filter by similarity threshold (e.g., `distance < 0.3`)
4. **Limit Results**: Always limit results (e.g., top 5)
5. **Index for Performance**: Create pgvector index on embedding columns

**When to Use**:
- Artifact relevance ranking
- Semantic search
- Content recommendation
- Duplicate detection

**Pattern**:
```python
from pgvector.django import CosineDistance

similar_artifacts = Artifact.objects.annotate(
    similarity=CosineDistance('embedding', query_embedding)
).filter(
    similarity__lt=0.3  # Cosine distance < 0.3 (higher similarity)
).order_by('similarity')[:5]  # Top 5 most similar
```

**Benefits**:
- Semantic search (not just keywords)
- Fast with proper indexes
- Scalable to large datasets

**Reference**: See `llm_services/models.py:87`, `llm_services/services/core/embedding_service.py:45`

---

### 4.5 File Storage & Upload Pattern

**Reference**: `artifacts/models.py:94-97`, `cv_tailor/settings/production.py:31-32`

**Problem**: Need secure file uploads that work locally (filesystem) and in production (S3) without code changes.

**Solution**: Multi-environment storage backend with validation and automatic cleanup.

**Principles**:
1. **Environment-Based Storage**: Local filesystem (dev/test), S3 (production) — see Pattern 1.1
2. **File Validation**: Check size, MIME type, extension using `python-magic` (not just extension)
3. **Security**: Reject executables, validate content matches extension, limit sizes (DoS prevention)
4. **Signed URLs**: Time-limited S3 URLs (1 hour default) for secure access
5. **Automatic Cleanup**: Delete files when parent record is deleted
6. **Unique Filenames**: UUIDs prevent collisions

**Model Pattern**:
```python
def artifact_upload_path(instance, filename):
    ext = os.path.splitext(filename)[1]
    return f"artifacts/{instance.user.id}/{uuid.uuid4()}{ext}"

class Artifact(models.Model):
    file_path = models.FileField(upload_to=artifact_upload_path)
    def delete(self, *args, **kwargs):
        if self.file_path:
            self.file_path.delete(save=False)
        super().delete(*args, **kwargs)
```

**Validation Pattern** (use `python-magic` for MIME detection):
```python
def validate_uploaded_file(uploaded_file):
    if uploaded_file.size > settings.MAX_UPLOAD_SIZE:
        raise ValidationError("File too large")
    mime = magic.from_buffer(uploaded_file.read(2048), mime=True)
    if mime not in settings.ALLOWED_MIME_TYPES:
        raise ValidationError(f"Invalid type: {mime}")
```

**Signed URLs**: `default_storage.url(file_path, expire=3600)` — production generates time-limited S3 URLs

**When to Use**: User uploads, generated downloads, security-sensitive files

**Benefits**: Environment-agnostic, secure validation, automatic cleanup, scalable (S3)

---

## 5. API & Serialization Patterns

### 5.1 DRF ViewSet Pattern

**Problem**: Need RESTful API endpoints with standard CRUD plus custom actions.

**Solution**: Django REST Framework ViewSets with custom actions.

**Principles**:
1. **ModelViewSet for CRUD**: Standard CRUD on resources
2. **Custom Actions**: `@action` decorator for non-CRUD operations
3. **Service Layer Delegation**: Views call services, no business logic in views
4. **Serializer Validation**: Use serializers, not manual checks

**Pattern**:
```python
class CVViewSet(viewsets.ModelViewSet):
    queryset = CV.objects.all()
    serializer_class = CVSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def generate(self, request, pk=None):
        serializer = GenerateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = cv_generation_service.generate(self.get_object(), serializer.validated_data)
        return Response(CVSerializer(result).data)
```

**When to Use**: All API endpoints, CRUD operations, custom actions

**Benefits**: Standard RESTful structure, automatic routing, built-in pagination/filtering, clear separation

---

### 5.2 Serializer Design Patterns

**⭐ CRITICAL PATTERN — Used in all APIs**

**Problem**: Need different serialization for read vs write, nested objects, computed fields, and validation.

**Solution**: Purpose-specific serializers for common scenarios.

**Principles**:
1. **Read vs Write Serializers**: Separate for list/retrieve (read) vs create/update (write)
2. **Nested Serializers**: For related objects (requires prefetch in ViewSet — see Pattern 4.2)
3. **SerializerMethodField**: For computed/derived fields
4. **Custom Validation**: `validate_<field>()` for field-level, `validate()` for object-level
5. **Transaction Safety**: `@transaction.atomic` in create/update methods
6. **Backward Compatibility**: Map deprecated fields to new fields in `validate()`

**Patterns**:
```python
# Read (detailed) vs Write (minimal)
class ArtifactSerializer(serializers.ModelSerializer):  # Read
    user_email = serializers.SerializerMethodField()
class ArtifactUpdateSerializer(serializers.ModelSerializer):  # Write
    fields = ['title', 'description']

# Nested (requires ViewSet prefetch!)
class CVSerializer(serializers.ModelSerializer):
    bullet_points = BulletPointSerializer(many=True, read_only=True)

# Custom Validation
def validate_url(self, value):
    if not value.startswith('https://'):
        raise serializers.ValidationError("HTTPS required")

# Backward Compatibility
def validate(self, data):
    if 'old_field' in data:
        data['new_field'] = data.pop('old_field')
    return data
```

**When to Use**: Read/write separation for complex models, nested for related objects, custom validation for rules, backward compat for API migrations.

**Benefits**: Clean API contracts, proper validation, no N+1 queries

**Reference**: `artifacts/serializers.py:15`, `generation/serializers.py:28`

---

### 5.3 API Response Pattern

**Problem**: Inconsistent API response formats confuse frontend developers and make error handling difficult.

**Solution**: Standardized response format for success and error cases.

**Principles**:
1. **HTTP Status Codes**: Use proper status codes (200, 201, 400, 404, 500)
2. **Consistent Structure**: Same response structure for all endpoints
3. **Error Details**: Include error code, message, and details object
4. **No Success Booleans**: Don't use `{"success": true/false}`, use HTTP status codes

**Success Response Format**:
```json
{
  "id": "uuid",
  "field1": "value",
  "field2": "value",
  "created_at": "2025-01-15T10:30:00Z"
}
```

**Error Response Format** (DRF default):
```json
{
  "detail": "Error message",
  "field_errors": {
    "email": ["This field is required"],
    "password": ["Password too short"]
  }
}
```

**When to Use**:
- All API endpoints
- Custom error handlers
- Exception serializers

**Anti-Pattern**:
```json
// ❌ Don't use success boolean
{"success": false, "error": "Something failed"}

// ✅ Use HTTP status codes + DRF error format
// HTTP 400 Bad Request
{"detail": "Validation failed", "field_errors": {...}}
```

**Benefits**:
- Frontend can rely on HTTP status codes
- Consistent error handling
- Better debugging

**Reference**: DRF response documentation

---

## 6. Authentication & Authorization Patterns

### 6.1 JWT Authentication Pattern

**⭐ CRITICAL PATTERN — Used in all authenticated APIs**

**Reference**: `backend/cv_tailor/settings/base.py` (JWT configuration), `accounts/views.py`

**Problem**: Need stateless, secure authentication for React frontend and mobile apps.

**Solution**: JWT authentication with access (5 min) + refresh tokens (7 days).

**Principles**:
1. **Access + Refresh**: Short-lived access tokens, long-lived refresh tokens
2. **Token Blacklist**: Revoke refresh tokens on logout
3. **Stateless**: No server-side sessions (JWT is self-contained)
4. **HTTPS Only (Prod)**: Tokens transmitted over HTTPS
5. **HttpOnly Cookies**: Refresh tokens in HttpOnly cookies (XSS protection)

**Lifecycle**: Login → access+refresh tokens | API calls use access token | 401 → refresh for new access | Logout blacklists refresh

**Configuration**: `ACCESS_TOKEN_LIFETIME=5min`, `REFRESH_TOKEN_LIFETIME=7days`, `ROTATE_REFRESH_TOKENS=True`, `BLACKLIST_AFTER_ROTATION=True` (see `settings/base.py:145`)

**When to Use**: All authenticated APIs, React frontend, mobile apps

**Benefits**: Stateless (scales), secure (short-lived), revocable (blacklist), mobile-friendly

**Reference**: `accounts/views.py:12`, `cv_tailor/settings/base.py:145`

---

### 6.2 Permission Classes Pattern

**Reference**: `accounts/views.py`, DRF permission classes

**Problem**: Need granular access control (resource ownership, role-based access).

**Solution**: Django REST Framework permission classes.

**Principles**:
1. **Class-Level Permissions**: Apply to all actions (e.g., `IsAuthenticated`)
2. **Action-Level Permissions**: Override for specific actions (e.g., admin-only delete)
3. **Object-Level Permissions**: Check ownership (e.g., user can only edit their own artifacts)
4. **Custom Permission Classes**: Create reusable permission logic

**Common Permission Classes**:
- `IsAuthenticated`: Require logged-in user
- `IsAdminUser`: Require admin/staff user
- `AllowAny`: Public access
- `IsOwner` (custom): User owns the object

**Pattern**:
```python
from rest_framework.permissions import IsAuthenticated, BasePermission

class IsOwner(BasePermission):
    """User must own the object"""
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user

class ArtifactViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsOwner]  # All actions

    def get_permissions(self):
        # Override for specific actions
        if self.action == 'create':
            return [IsAuthenticated()]  # No ownership check for create
        return super().get_permissions()
```

**When to Use**:
- All API endpoints (minimum: IsAuthenticated)
- Object ownership checks
- Role-based access control
- Multi-tenancy

**Benefits**:
- Declarative access control
- Reusable permission logic
- Automatic 403 responses

**Reference**: DRF permissions documentation

---

### 6.3 OAuth Integration Pattern

**Reference**: `accounts/views.py`, django-allauth configuration

**Problem**: Users want to sign in with Google/GitHub instead of creating passwords.

**Solution**: OAuth 2.0 integration with django-allauth.

**Principles**:
1. **Social Provider Config**: Configure OAuth apps in provider's developer console (client ID/secret, redirect URIs)
2. **Allauth Integration**: Use django-allauth for provider management
3. **Email Verification**: Verify emails from OAuth provider
4. **Account Linking**: Link OAuth accounts to existing email-matched accounts
5. **Fallback**: Support both OAuth and traditional email/password login

**Flow**: User clicks "Sign in with Google" → OAuth redirect → User grants permission → Backend exchanges code for token → Fetch profile → Create/link account → Return JWT

**When to Use**: Social login (Google, GitHub, Microsoft), enterprise SSO, reducing password management

**Benefits**: Better UX (no password), verified emails, trusted identity providers

**Reference**: `accounts/views.py:78`, django-allauth docs

---

## 7. Async & Background Processing Patterns

### 7.1 Celery Task Pattern

**Reference**: `artifacts/tasks.py`, `generation/tasks.py`, `llm_services/tasks.py`

**Problem**: Long-running operations block HTTP requests and cause timeouts.

**Solution**: Celery async tasks with Redis broker.

**Principles**:
1. **Shared Task Decorator**: Use `@shared_task` for reusable tasks
2. **Retry + Exponential Backoff**: `max_retries=3`, `countdown=60 * (2 ** self.request.retries)`
3. **Idempotency**: Always implement guards (see Pattern 3.3)
4. **Status Tracking**: pending → processing → completed/failed

**Pattern**:
```python
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def process_artifact_task(self, artifact_id):
    try:
        artifact = Artifact.objects.select_for_update().get(id=artifact_id)
        if artifact.status == 'completed':
            return  # Idempotency guard
        artifact.status = 'processing'
        artifact.save()
        service.process(artifact)
        artifact.status = 'completed'
        artifact.save()
    except Exception as exc:
        artifact.status = 'failed'
        artifact.save()
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))

# Invocation
process_artifact_task.delay(artifact.id)  # Fire and forget
result = process_artifact_task.apply_async(args=[artifact.id])  # With tracking
```

**When to Use**: LLM calls (>5s), file processing, bulk operations, scheduled jobs

**Benefits**: Non-blocking responses, retry logic, scalable (add workers)

**Reference**: `artifacts/tasks.py:12`, `generation/tasks.py:45`

---

### 7.2 Progress Callback Pattern

**Reference**: `generation/tasks.py`

**Problem**: Long-running tasks need to report progress to frontend for better UX.

**Solution**: Progress callback functions that update entity status percentage.

**Principles**:
1. **Callback Function**: Accept callback parameter for progress updates
2. **Progress Percentage**: Report 0-100% progress
3. **Database Persistence**: Store progress in entity (e.g., `progress_pct` field)
4. **Frontend Polling**: Frontend polls entity status endpoint for progress
5. **WebSocket Alternative**: For real-time, use WebSocket/SSE instead of polling

**Pattern**:
```python
def process_with_progress(entity_id, progress_callback=None):
    steps = ['load', 'process', 'validate', 'save']
    total_steps = len(steps)

    for i, step in enumerate(steps):
        # Do work
        perform_step(step)

        # Report progress
        if progress_callback:
            progress_pct = int((i + 1) / total_steps * 100)
            progress_callback(progress_pct)

# In Celery task
@shared_task
def process_entity_task(entity_id):
    def update_progress(pct):
        Entity.objects.filter(id=entity_id).update(progress_pct=pct)

    process_with_progress(entity_id, progress_callback=update_progress)
```

**When to Use**:
- Long-running tasks (> 10 seconds)
- Multi-step processes
- Better UX for waiting users

**Benefits**:
- User feedback during processing
- Allows cancellation
- Better perceived performance

**Reference**: See `generation/tasks.py:123`

---

## 8. LLM-Specific Patterns

### 8.1 Model Registry & Selection Pattern

**Reference**: `llm_services/services/infrastructure/model_registry.py`, `model_selector.py`

**Problem**: Need centralized model configuration with intelligent fallback and cost optimization.

**Solution**: Model registry with metadata (context window, cost, capabilities, provider) and selection logic.

**Principles**:
1. **Central Registry**: Single source of truth for all LLM model configurations
2. **Intelligent Selection**: Select based on task requirements (context length, capabilities, budget)
3. **Fallback Cascade**: Automatic fallback to alternative models on failure
4. **Never Hardcode**: Always use registry/selector, never `model="gpt-4"`

**Pattern**:
```python
# Automatic selection by requirements
model = selector.select_model(
    task_type="content_generation",
    context_length=5000,
    required_capabilities=["reasoning"],
    budget_constraint=0.02
)

# Or with fallback cascade
model = selector.select_with_fallback(
    primary="gpt-4", fallbacks=["claude-3-5-sonnet", "gpt-3.5-turbo"]
)
```

**When to Use**: Always for LLM operations (never hardcode model names)

**Benefits**: Cost optimization, reliability (fallback), maintainability (single source)

**Reference**: `llm_services/services/infrastructure/model_registry.py:12`, `model_selector.py:45`

---

### 8.2 LLM Task Configuration Pattern

**Reference**: `llm_services/services/base/config_registry.py`

**Problem**: Different LLM tasks require different configurations (temperature, max tokens, reasoning effort).

**Solution**: Task-specific configuration registry with validation.

**Principles**:
1. **Task Types**: Enum of task types (CONTENT_GENERATION, EXTRACTION, VALIDATION)
2. **Task-Specific Config**: Different config per task type
3. **Parameter Validation**: Validate parameters (e.g., reasoning_effort for GPT-5)
4. **Deprecated Parameter Removal**: Remove unsupported parameters (e.g., temperature for GPT-5)
5. **Default Overrides**: Allow per-call overrides of defaults

**When to Use**:
- LLM API calls with task-specific requirements
- Different temperature/top_p per task
- GPT-5 reasoning effort configuration

**Benefits**:
- Consistent task configurations
- Parameter validation
- Easy tuning

**Reference**: See `llm_services/services/base/config_registry.py:18`

---

### 8.3 Confidence Scoring Pattern

**Reference**: `generation/services/confidence_calculator.py`

**Problem**: Need to assess quality of generated content to filter low-quality outputs.

**Solution**: Multi-criteria confidence scoring system.

**Principles**:
1. **Multiple Criteria**: Length, specificity, keyword presence, structure
2. **Weighted Scoring**: Different criteria have different weights
3. **Threshold Filtering**: Reject content below confidence threshold
4. **Explainable Scores**: Return score breakdown for debugging
5. **Calibration**: Adjust weights based on user feedback

**Scoring Criteria Examples**:
- Length (too short/too long = low score)
- Specificity (vague words = low score)
- Keyword presence (required terms missing = low score)
- Structure (missing required sections = low score)

**When to Use**:
- Generated bullet points quality check
- CV content validation
- Cover letter quality assessment

**Benefits**:
- Filter low-quality outputs
- Automatic quality assurance
- User trust (only show quality content)

**Reference**: See `generation/services/confidence_calculator.py:25`

---

### 8.4 Prompt Engineering Pattern

**Reference**: `llm_services/services/core/tailored_content_service.py:361`, `evidence_content_extractor.py:1347`

**Problem**: LLM prompts lack structure, producing variable quality outputs without proper formatting.

**Solution**: Structured prompts with system/user separation, JSON schemas, and versioning.

**Principles**:
1. **System vs User Separation**: System defines role/constraints, user provides task input
2. **Structured Output**: Request JSON schema for parseable results
3. **Context Length Management**: Truncate to fit model limits (4 chars ≈ 1 token)
4. **Few-Shot Examples**: Include 2-3 examples for complex tasks
5. **Prompt Versioning**: Track changes with semantic version IDs
6. **Output Validation**: Validate responses against Pydantic schema

**Pattern**:
```python
# System: Role + constraints + output format
system = """You are a CV writer. Use action verbs, include metrics.
OUTPUT: {"bullets": [{"content": "str", "confidence": float}]}"""

# User: Task-specific input
user = f"Generate bullets for {job_title} at {company}"

response = llm.generate(system=system, user=user)
```

**Structured Output with Pydantic**:
```python
class BulletResponse(BaseModel):
    bullets: list[BulletPoint]

prompt = """Generate JSON: {"bullets": [{"content": "...", "confidence": 0.95}]}
Content: {content}"""
validated = BulletResponse.model_validate_json(llm.generate(prompt))
```

**Context Truncation**: `max_chars = max_tokens * 4; content[:max_chars] + "[truncated...]"`

**Few-Shot**: Include 2-3 input/output examples before the actual task (e.g., "Input: X → Output: Y")

**Versioning**: Include `PROMPT_VERSION = "v2.1.0"` in prompt and log it for debugging/reproducibility

**When to Use**: All LLM calls, content generation, extraction tasks

**Benefits**: Consistent quality, parseable responses, reproducible results, easier debugging

**Anti-Pattern**:
```python
# ❌ DON'T: Unstructured
prompt = f"Write bullets about {content}"

# ✅ DO: Structured with JSON schema
prompt = f"""JSON: {{"bullets": ["point1", "point2"]}}
Content: {content}"""
```

---

## 9. Testing Patterns

### 9.1 Test Organization Pattern

**Reference**: `llm_services/tests/`, `generation/tests/`, `docs/testing/test-backend-guide.md`

**Problem**: Need fast test feedback loops while still covering integration and real API scenarios.

**Solution**: Three-tier test organization with tags and gating.

**Principles**:
1. **Unit Tests**: Fast (milliseconds), all external dependencies mocked, run on every commit
2. **Integration Tests**: Medium (seconds), real database + mocked external APIs, run pre-merge
3. **Real API Tests**: Slow (minutes), real LLM APIs, gated by `FORCE_REAL_API_TESTS`, run pre-deployment
4. **Test File Naming**: `test_models.py`, `test_services.py`, `test_integration.py`, `test_real_*.py`
5. **Proper Mocking**: Always mock LLM APIs in unit/integration tests (30x faster)

**Test Categories**:

| Category | Scope | Speed | Dependencies | Tags | When to Run |
|----------|-------|-------|--------------|------|-------------|
| **Unit** | Single function/class | Milliseconds | All mocked | `@tag('unit', 'fast')` | Every commit |
| **Integration** | API endpoints, DB | Seconds | Real DB, mocked APIs | `@tag('integration')` | Pre-merge |
| **Real API** | End-to-end with real APIs | Minutes | Real everything | `@tag('real_api', 'slow')` | Pre-deployment, manual |

**Running Tests**:
```bash
# Fast unit tests (recommended for pre-commit, ~1 minute)
docker-compose exec backend uv run python manage.py test --tag=fast --tag=unit --keepdb

# All tests excluding slow real API tests (CI/CD)
docker-compose exec backend uv run python manage.py test --exclude-tag=slow --exclude-tag=real_api --keepdb

# Real API tests (costs money, requires API keys)
FORCE_REAL_API_TESTS=true docker-compose exec backend uv run python manage.py test --tag=real_api --keepdb -v 2
```

**When to Use Each Category**:
- **Unit**: Test service methods, model methods, utilities
- **Integration**: Test API endpoints, serializers, database operations
- **Real API**: Validate LLM integrations before production release

**Benefits**:
- Fast feedback (unit tests in ~1 minute)
- Comprehensive coverage (integration + real API)
- Cost control (real API tests gated)

**Reference**: See `docs/testing/test-backend-guide.md`, `llm_services/tests/test_services.py:12`

---

### 9.2 Mocking Pattern for External Services

**Reference**: `docs/testing/test-backend-guide.md`, `llm_services/tests/test_services.py`

**Problem**: Unit tests calling real LLM APIs are slow (30+ min), expensive, and flaky (30x slower than mocked).

**Solution**: Mock external service calls with unittest.mock.

**Principles**:
1. **Mock at Service Boundary**: Mock external API clients (OpenAI, Anthropic), not internal services
2. **Realistic Returns**: Return data structures matching real API responses
3. **Test Success and Failure**: Mock both successful calls and exceptions
4. **Patch at Usage Location**: `@patch` where object is used, not where defined
5. **Side Effects for Sequences**: `side_effect` for multiple calls with different returns

**Patterns**:
```python
# Mock LLM API Call
@patch('llm_services.services.core.tailored_content_service.OpenAI')
def test_generate(self, mock_openai):
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content="Generated"))]
    )
    mock_openai.return_value = mock_client
    result = service.generate_content(prompt="Test")
    self.assertEqual(result, "Generated")

# Mock Exception
@patch('service.openai_client.generate')
def test_error(self, mock_gen):
    mock_gen.side_effect = OpenAIError("API failure")
    with self.assertRaises(LLMAPIError):
        service.generate_content(prompt="Test")

# Mock Sequence (retry logic)
@patch('service.api_call')
def test_retry(self, mock_api):
    mock_api.side_effect = [Exception("Fail"), Exception("Fail"), "Success"]
    result = service.call_with_retry()
    self.assertEqual(mock_api.call_count, 3)
```

**When to Use**: All unit/integration tests calling external APIs (not for real API tests)

**Benefits**: Fast tests (158 in ~1 min), no API costs, reliable, predictable

**Reference**: `docs/testing/test-backend-guide.md:45`, `llm_services/tests/test_services.py:78`

---

## 10. Anti-Patterns to Avoid

### 10.1 Business Logic in Views

**❌ Anti-Pattern**: Business logic in views/ViewSets instead of service layer.

**Problem**: Tight coupling to HTTP, difficult to test/reuse, violates single responsibility.

```python
# ❌ DON'T: 100 lines of business logic in view
def generate(self, request, pk=None):
    artifacts = Artifact.objects.filter(user=request.user)
    embeddings = [generate_embedding(a) for a in artifacts]
    content = llm_api.generate(rank_by_similarity(embeddings))
    ...

# ✅ DO: Delegate to service layer
def generate(self, request, pk=None):
    result = cv_generation_service.generate(cv, serializer.validated_data)
    return Response(CVSerializer(result).data)
```

**Benefits**: Reusable logic, easy testing, clear separation of concerns.

---

### 10.2 Hardcoded Configuration Values

**❌ Anti-Pattern**: Hardcoded model names, endpoints, environment values.

**Problem**: Cannot switch models/config without code changes, violates DRY.

```python
# ❌ DON'T: Hardcoded values
model="gpt-4"  # Hardcoded!
DATABASE_URL = "postgresql://localhost:5432/cv_tailor"

# ✅ DO: Use registry and environment variables
model = model_selector.select_model(task_type="content_generation")
DATABASE_URL = os.environ.get('DATABASE_URL')
```

---

### 10.3 Success/Failure Dict Returns

**❌ Anti-Pattern**: Returning `{"success": True/False}` instead of raising exceptions.

**Problem**: Caller must check boolean (easy to forget), no stack traces, violates Python conventions.

```python
# ❌ DON'T: Return error dicts
def generate_content(prompt):
    try:
        return {"success": True, "content": llm_api.generate(prompt)}
    except Exception as e:
        return {"success": False, "error": str(e)}

# ✅ DO: Raise exceptions
def generate_content(prompt):
    try:
        return llm_api.generate(prompt)
    except OpenAIError as e:
        raise LLMAPIError(f"Generation failed: {e}") from e
```

**Benefits**: Cannot ignore errors, full stack traces, standard error handling.

---

### 10.4 N+1 Query Problems

**❌ Anti-Pattern**: Accessing relationships in loops without prefetch.

**Problem**: Queries scale linearly (1 + N queries), slow responses, high database load.

```python
# ❌ DON'T: N+1 queries
for artifact in Artifact.objects.filter(user=user):  # 1 + N queries
    print(artifact.user.email)  # Query per artifact!

# ✅ DO: Prefetch optimization
artifacts = Artifact.objects.filter(user=user).select_related('user')
for artifact in artifacts:  # No extra queries
    print(artifact.user.email)  # Uses prefetched data
```

**Detection**: `with self.assertNumQueries(2): response = self.client.get('/api/artifacts/')`

**Reference**: See Pattern 4.2 (Prefetch Optimization)

---

### 10.5 Duplicate Service Implementations

**❌ Anti-Pattern**: Creating new service when similar functionality exists.

**Problem**: Code duplication, inconsistent patterns, reimplementing circuit breaker/retry logic.

```python
# ❌ DON'T: Reimplement everything
class MyNewLLMService:
    def __init__(self):
        self.client = OpenAI()
        # Reimplementing retry/error handling/circuit breaker...

# ✅ DO: Extend base service
class MyNewLLMService(BaseLLMService):
    def generate(self, prompt):
        return self.execute_with_retry(lambda: self.client.generate(prompt))
```

**Discovery Checklist**: Search for similar services, identify reusable base classes, confirm no duplication.

**Reference**: See Pattern 2.2 (Base Service Pattern)

---

## 11. Pattern Selection Decision Tree

**Use during Stage B (Discovery) and Stage E (Feature Planning).**

### Q1: What are you building?

**A: New API endpoint** → Patterns: 5.1, 5.2, 5.3, 6.1, 6.2 | Discovery: Check existing ViewSets | Next: Q2 if external calls

**B: Background task** → Patterns: 7.1, 3.3, 7.2 | Discovery: Check `*/tasks.py` | Next: Q3 if LLM calls

**C: Business logic/service** → Patterns: 2.1, 2.2, 2.3 | Discovery: Check `*/services/` | Next: Q2 if external calls

**D: Database query** → Patterns: 4.1, 4.2, 4.3, 4.4 (vector search) | Discovery: Check for N+1 patterns

**E: Auth** → Patterns: 6.1, 6.2, 6.3 | Discovery: Check `accounts/` app

**F: Testing** → Patterns: 9.1, 9.2 | Discovery: Check `*/tests/`

---

### Q2: Does your code call external services?

**YES** → Required: 3.1 (Circuit Breaker), 3.2 (Task Executor), 2.3 (Exception Hierarchy)
Discovery: Check if circuit breaker exists, what retry logic, what error types

**NO** → Skip

---

### Q3: Does your code call LLM APIs?

**YES** → Required: 8.1 (Model Registry), 8.2 (LLM Config), 3.1 (Circuit Breaker), 3.2 (Task Executor) | Optional: 8.3 (Confidence)
Discovery: Task type, model criteria, fallback models

**NO** → Skip

---

### Q4: Is this a new Django app or major refactor?

**YES** → Required: 1.1 (Multi-Environment Settings), 1.2 (Middleware), 2.1 (Service Layer)
Discovery: Review app structures, identify config needs

**NO** → Use patterns as needed

---

## 12. Pattern Compatibility Matrix

**Use this matrix to determine which patterns work well together.**

| Pattern | Compatible With | Incompatible With | Notes |
|---------|----------------|-------------------|-------|
| **1.1 Multi-Environment Settings** | All patterns | None | Foundation pattern |
| **2.1 Service Layer Architecture** | All service patterns (2.2, 2.3, 3.x, 8.x) | None | Organize services in layers |
| **2.2 Base Service** | 2.3, 3.1, 3.2, 8.1 | None | Inherit for all services |
| **2.3 Exception Hierarchy** | All patterns | 10.3 (Success/Failure Dicts) | Use exceptions, not dicts |
| **3.1 Circuit Breaker** | 3.2, 8.1, 7.1 | None | REQUIRED for external APIs |
| **3.2 Task Executor** | 3.1, 7.1 | None | Complements circuit breaker |
| **3.3 Idempotency** | 7.1, 7.2 | None | REQUIRED for Celery tasks |
| **4.2 Prefetch Optimization** | 5.2 (Serializers) | 10.4 (N+1 Queries) | Use together with serializers |
| **4.3 Transaction Management** | 5.2 (Serializers), 7.1 (Celery) | Long-running tasks | Avoid in Celery (locks DB) |
| **5.1 DRF ViewSet** | 5.2, 5.3, 6.1, 6.2 | 10.1 (Business Logic in Views) | Delegate to services |
| **5.2 Serializer Design** | 4.2 (Prefetch), 5.1 (ViewSet) | None | Coordinate with prefetch |
| **6.1 JWT Authentication** | 5.1, 6.2 | None | Use with ViewSets |
| **7.1 Celery Task** | 3.2, 3.3, 7.2 | 4.3 (long transactions) | Always use idempotency |
| **8.1 Model Registry** | 8.2, 3.1 | 10.2 (Hardcoded Models) | REQUIRED for LLM calls |
| **9.2 Mocking** | 9.1 (Test Organization) | Real API tests | Mock in unit/integration |

**Pattern Stacks** (Common Combinations):

| Use Case | Required Patterns | Optional Patterns |
|----------|------------------|-------------------|
| **New LLM Feature** | 2.1, 2.2, 2.3, 3.1, 3.2, 8.1, 8.2 | 8.3 (confidence scoring) |
| **New API Endpoint** | 5.1, 5.2, 5.3, 6.1, 6.2 | 4.2 (if nested relations) |
| **Background Task** | 7.1, 3.3, 2.3 | 3.2 (if external APIs), 7.2 (progress) |
| **External API Integration** | 3.1, 3.2, 2.3 | None |
| **Database-Heavy Feature** | 4.1, 4.2, 4.3 | 4.4 (if semantic search) |

---

## Enforcement

**During Stage B (Codebase Discovery)**:

**Required Checks**:
- [ ] Identified which patterns apply to this feature (use Decision Tree above)
- [ ] Searched for existing implementations of these patterns
- [ ] Confirmed no duplicate pattern implementations will be created
- [ ] Documented pattern compliance in discovery file (`docs/discovery/disco-<ID>.md`)
- [ ] Listed specific services/components to reuse
- [ ] Checked Pattern Compatibility Matrix for conflicts

**Blockers**:
- Implementation without pattern analysis → **BLOCK** (return to Stage B)
- Duplicate service when reusable one exists → **BLOCK** (refactor to reuse)
- Missing circuit breaker on external API → **BLOCK** (add circuit breaker)
- Business logic in views/serializers → **BLOCK** (extract to service layer)
- Hardcoded model names in LLM calls → **BLOCK** (use model registry)
- N+1 queries in list endpoints → **BLOCK** (add prefetch optimization)
- Success/failure dict returns → **BLOCK** (raise exceptions)

**During Stage C (TECH SPEC)**:
- [ ] Reference applicable patterns in spec
- [ ] Document deviations from patterns (if any) with justification

**During Stage E (FEATURE Planning)**:
- [ ] List patterns to be used in feature file
- [ ] Include pattern compliance in implementation checklist

**During Stage H (Implementation)**:
- [ ] Verify pattern implementation matches specification
- [ ] Run tests to validate pattern correctness (e.g., query count tests for prefetch)

---

**Document Version**: 2.0.0
**Last Updated**: 2025-01-15

**Maintained By**: Architecture Team
**Referenced In**:
- `rules/00-workflow.md` (Stage B, Stage C, Stage E)
- `rules/02-discovery/policy.md` (Pattern discovery phase)
- `docs/specs/spec-system.md` (System architecture reference)
