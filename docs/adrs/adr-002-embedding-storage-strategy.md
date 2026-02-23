# ADR: PostgreSQL with pgvector for Embedding Storage

**File:** docs/adrs/adr-002-embedding-storage-strategy.md
**Status:** ~~Draft~~ **Superseded by ADR-028** (2025-10-16)

---
> **⚠️ SUPERSEDED:** This ADR is superseded by [ADR-028: Remove Embeddings and Implement Manual Artifact Selection](adr-028-remove-embeddings-manual-selection.md) dated 2025-10-16. pgvector extension and all embedding infrastructure were removed in favor of keyword-based ranking with manual selection.
---

## Context

Enhanced artifact processing requires storing and querying vector embeddings for semantic similarity calculations between job requirements and artifact content. System needs to support:

- 1536-dimensional OpenAI embeddings per artifact
- Similarity search across user's artifact collection (~50-200 artifacts per user)
- Real-time ranking during CV generation
- Future scaling to 10k+ users with 100k+ artifacts

Current infrastructure includes Redis for caching and PostgreSQL for primary storage.

## Decision

Implement **PostgreSQL with pgvector extension** for embedding storage and similarity search:

**Implementation**:
- Add pgvector extension to existing PostgreSQL database
- Create VECTOR(1536) columns for artifact and job description embeddings
- Use native similarity functions: `<->` (L2), `<#>` (inner product), `<=>` (cosine)
- Create GIN indexes for efficient similarity queries
- Django integration via raw SQL and custom model fields

## Consequences

### Positive
+ **Single database**: Leverages existing PostgreSQL infrastructure
+ **Native similarity search**: Built-in vector operations and indexing
+ **ACID compliance**: Transactional consistency with artifact metadata
+ **SQL integration**: Easy Django ORM integration and complex queries
+ **Mature extension**: pgvector is production-ready and well-maintained
+ **Cost efficient**: No external vector database subscription needed

### Negative
− **Extension dependency**: Requires PostgreSQL 11+ with pgvector installed
− **Learning curve**: Team needs familiarity with vector operations and indexing
− **Index maintenance**: Vector indexes require tuning for optimal performance
− **Storage overhead**: Vector columns increase database size significantly

## Alternatives

1. **Redis-based embedding storage**
   - Pros: Fast access, existing infrastructure
   - Cons: In-memory limitations, no native similarity search

2. **Dedicated vector database (Pinecone)**
   - Pros: Purpose-built for embeddings, excellent performance
   - Cons: External dependency, monthly costs, vendor lock-in

3. **Self-hosted Weaviate**
   - Pros: Open-source, full control, GraphQL interface
   - Cons: Infrastructure complexity, operational overhead

4. **PostgreSQL JSON storage**
   - Pros: Simple implementation, existing database
   - Cons: Poor query performance, custom similarity algorithms required

## Rollback Plan

- **Extension issues**: Fallback to keyword-based ranking (existing system)
- **Performance degradation**: Add query optimization and index tuning
- **Storage constraints**: Implement embedding archival for inactive artifacts
- **Index corruption**: Rebuild vector indexes with minimal downtime

## Performance Monitoring

Monitor and optimize when:
- Similarity query latency > 500ms p95
- Vector index size > 10GB
- Database storage growth > 50% due to embeddings
- Query plan shows sequential scans on vector columns

## Links

- **TECH-SPEC**: `spec-20240924-llm-artifacts.md`
- **ADR**: `adr-003-llm-provider-selection.md`
- **Feature**: `ft-llm-001-content-extraction.md` (pending)