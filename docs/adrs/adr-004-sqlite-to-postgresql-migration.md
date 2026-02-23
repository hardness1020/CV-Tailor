# ADR: Migrate from SQLite to PostgreSQL for Vector Search Support

**File:** docs/adrs/adr-004-sqlite-to-postgresql-migration.md
**Status:** Draft

## Context

CV Tailor currently uses SQLite for development and likely production, providing simplicity and ease of deployment. However, the enhanced artifact processing system with semantic similarity search requires pgvector extension, which is only available for PostgreSQL.

Current database usage:
- **Development**: SQLite with Django ORM
- **Models**: accounts, artifacts, generation, export
- **Current data size**: Estimated <100MB for development
- **Concurrent users**: Currently low, but planning for scale

Requirements driving the change:
- Vector similarity search for artifact-job matching
- 1536-dimensional embeddings storage and indexing
- Native similarity functions (cosine, L2, inner product)
- ACID compliance with vector operations

## Decision

Migrate from **SQLite to PostgreSQL** to enable pgvector extension:

**Migration Strategy**:
1. **Development first**: Update local development stack to PostgreSQL
2. **Docker Compose**: Add PostgreSQL service with pgvector pre-installed
3. **Data migration**: Django data migration scripts for existing data
4. **Production deployment**: Deploy PostgreSQL before vector features go live
5. **Backwards compatibility**: Maintain Django ORM abstraction layer

**Implementation Timeline**:
- Week 1: Development environment migration
- Week 2: CI/CD pipeline updates and testing
- Week 3: Production PostgreSQL deployment
- Week 4: Data migration and vector features activation

## Consequences

### Positive
+ **Vector support**: Enables pgvector extension for semantic search
+ **Production readiness**: PostgreSQL better suited for multi-user applications
+ **Advanced features**: JSON operators, full-text search, advanced indexing
+ **Scalability**: Better concurrent access and query optimization
+ **Ecosystem**: Rich tooling and monitoring solutions available

### Negative
− **Development complexity**: Local setup requires PostgreSQL installation
− **Migration effort**: Data migration and testing across environments
− **Resource usage**: Higher memory and CPU requirements vs SQLite
− **Operational overhead**: Database administration, backups, monitoring
− **Docker dependency**: Development now requires container orchestration

## Alternatives

1. **Hybrid approach**: Keep SQLite for non-vector data, add PostgreSQL for embeddings
   - Pros: Minimal migration effort, isolated vector functionality
   - Cons: Data consistency challenges, complex application logic

2. **External vector database**: Keep SQLite + dedicated vector DB (Pinecone)
   - Pros: No core database migration required
   - Cons: Additional external dependency, synchronization complexity

3. **Alternative vector libraries**: Explore SQLite vector extensions (sqlite-vss)
   - Pros: No database migration needed
   - Cons: Less mature ecosystem, limited similarity functions

4. **Delay vector search**: Implement keyword-based ranking improvements first
   - Pros: No infrastructure changes required
   - Cons: Compromises on core feature requirements

## Rollback Plan

- **Development rollback**: Maintain SQLite settings in Django configuration
- **Data export**: PostgreSQL data can be exported back to SQLite if needed
- **Feature flags**: Vector search features behind flags, can disable if issues arise
- **Parallel environments**: Run both databases during transition period

## Migration Checklist

### Development Environment
- [ ] Add PostgreSQL to Docker Compose with pgvector extension
- [ ] Update Django settings for PostgreSQL connection
- [ ] Create database initialization scripts
- [ ] Update developer documentation and setup guides

### CI/CD Pipeline
- [ ] Update GitHub Actions to use PostgreSQL service
- [ ] Modify test database setup for PostgreSQL
- [ ] Add database migration verification steps
- [ ] Update deployment scripts and infrastructure

### Data Migration
- [ ] Create Django management commands for data export/import
- [ ] Test migration with realistic data volumes
- [ ] Implement rollback procedures
- [ ] Plan production migration schedule and downtime

### Production Deployment
- [ ] Provision PostgreSQL instance with pgvector installed
- [ ] Configure connection pooling and performance settings
- [ ] Set up monitoring and backup procedures
- [ ] Execute data migration with minimal downtime

## Links

- **TECH-SPEC**: `spec-20240924-llm-artifacts.md`
- **Related ADRs**: `adr-002-embedding-storage-strategy.md`
- **Feature**: `ft-llm-001-content-extraction.md` (pending)