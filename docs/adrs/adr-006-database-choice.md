# ADR: Choose PostgreSQL over MongoDB/MySQL for Primary Database

**File:** docs/adrs/adr-006-database-choice.md
**Status:** Draft

## Context

The CV Auto-Tailor system requires a robust database solution that can handle:
- **Relational Data**: Users, artifacts, evidence links, labels with complex relationships
- **JSON Storage**: Flexible schema for job descriptions, generated content, and LLM responses
- **Full-Text Search**: Skill matching and artifact search capabilities
- **ACID Transactions**: Ensuring data consistency during generation workflows
- **Scalability**: Supporting 10,000+ concurrent users with millions of artifacts
- **Performance**: Sub-second query response times for user-facing operations

Key considerations:
- Schema evolution and migration management
- Django ORM compatibility and performance
- Backup and disaster recovery capabilities
- Operational complexity and monitoring
- Cost at scale
- Team expertise and tooling

The main candidates are PostgreSQL, MySQL, and MongoDB, with evaluation of cloud-managed vs self-hosted options.

## Decision

Adopt **PostgreSQL 15** as the primary database, using cloud-managed service (AWS RDS/Azure Database) with read replicas for scale.

Rationale:
1. **Hybrid Data Model**: Native JSON support (JSONB) combined with strong relational features handles both structured and semi-structured data
2. **Django Integration**: Excellent ORM support with advanced features (ArrayField, JSONField, full-text search)
3. **Performance**: Superior query optimizer and extensive indexing options (GIN, GiST, partial indexes)
4. **ACID Compliance**: Strong consistency guarantees essential for financial/user data integrity
5. **Advanced Features**: Built-in full-text search, regex support, and array operations reduce need for external services
6. **Ecosystem Maturity**: Extensive tooling, monitoring, and operational knowledge base

## Consequences

### Positive
+ **Rich Data Types**: JSONB, arrays, and custom types handle complex artifact metadata efficiently
+ **Query Flexibility**: Advanced SQL features support complex reporting and analytics
+ **Full-Text Search**: Built-in search capabilities reduce dependency on external search engines
+ **Django Synergy**: PostgreSQL-specific Django features (ArrayField, HStoreField) optimize development
+ **Scalability Path**: Read replicas, connection pooling, and partitioning provide clear scaling options
+ **Operational Maturity**: Extensive monitoring tools (pg_stat, pganalyze) and backup solutions

### Negative
- **Memory Usage**: Higher memory requirements than MySQL for similar workloads
- **Setup Complexity**: More configuration options require deeper database expertise
- **Cost**: Generally more expensive than MySQL in cloud environments
- **Learning Curve**: Advanced features require PostgreSQL-specific knowledge

## Alternatives

### MySQL 8.0
**Pros**: Lower resource usage, simpler operations, broad hosting support, JSON support added
**Cons**: Weaker JSON capabilities, less sophisticated query optimizer, limited array support
**Verdict**: Good option but PostgreSQL's JSON and array features are superior for our use case

### MongoDB
**Pros**: Native JSON storage, horizontal scaling, flexible schema
**Cons**: No ACID transactions across documents, weaker consistency, poor Django integration
**Verdict**: Schema flexibility doesn't outweigh relational data advantages and Django compatibility

### SQLite
**Pros**: Simplicity, no server setup, good for development
**Cons**: No concurrent writes, limited scalability, unsuitable for production web application
**Verdict**: Development/testing only

## Implementation Details

### Database Architecture
```sql
-- Key PostgreSQL-specific features utilized
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- Full-text search
CREATE EXTENSION IF NOT EXISTS btree_gin;  -- Composite indexes

-- Example: Artifact table with JSON metadata
CREATE TABLE artifacts (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES auth_user(id),
    title VARCHAR(255) NOT NULL,
    technologies TEXT[] DEFAULT '{}',  -- Array type
    metadata JSONB DEFAULT '{}',       -- JSON with indexing
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))
    ) STORED
);

-- GIN index for JSON queries
CREATE INDEX idx_artifacts_metadata_gin ON artifacts USING GIN (metadata);

-- Full-text search index
CREATE INDEX idx_artifacts_search ON artifacts USING GIN (search_vector);

-- Array containment index
CREATE INDEX idx_artifacts_technologies ON artifacts USING GIN (technologies);
```

### Performance Optimizations
- **Connection Pooling**: PgBouncer for connection management
- **Read Replicas**: Separate read traffic for reporting and search
- **Partitioning**: Table partitioning for large datasets (generated documents)
- **Materialized Views**: Pre-computed aggregations for dashboard queries

### Backup and Recovery
- **Automated Backups**: Daily full backups with point-in-time recovery
- **Cross-Region Replication**: Disaster recovery setup in secondary region
- **Backup Testing**: Monthly restore testing to verify backup integrity

## Rollback Plan

If PostgreSQL proves inadequate for performance or operational requirements:

1. **Phase 1**: Optimize PostgreSQL (query tuning, indexing, connection pooling, read replicas)
2. **Phase 2**: Migrate specific high-volume tables to specialized databases (Redis for caching, Elasticsearch for search)
3. **Phase 3**: If full migration needed, prioritize migration order: MySQL → MongoDB → NewSQL solutions

**Migration Strategy**: Database abstraction layer in Django allows gradual migration of individual models

**Trigger Criteria**:
- Query response times consistently >2s despite optimization
- Inability to handle target concurrent load with reasonable infrastructure costs
- Operational complexity exceeding team capabilities

## Operational Considerations

### Monitoring and Alerting
- **Performance Metrics**: Query performance, connection counts, lock contention
- **Health Checks**: Automated failover detection and notification
- **Capacity Planning**: Disk space, memory usage, and growth projections

### Security
- **Encryption**: At-rest and in-transit encryption for all data
- **Access Control**: Role-based access with principle of least privilege
- **Audit Logging**: Database access and modification logging

### Development Workflow
- **Schema Migrations**: Django migration system with PostgreSQL-specific features
- **Testing**: Separate test databases with realistic data volumes
- **Local Development**: Docker containers for consistent development environment

## Links

- **PRD**: `prd-20250923.md` - Data requirements and scale targets
- **TECH-SPECs**: `spec-20250923-api.md`, `spec-20250923-system.md` - Database schema and architecture
- **Related ADRs**: `adr-005-backend-framework.md` - Django ORM integration requirements