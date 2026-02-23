# Feature — 005 multi-source-artifact-preprocessing

**File:** docs/features/ft-005-multi-source-artifact-preprocessing.md
**Owner:** ML/Backend Team
**TECH-SPECs:** `spec-20250927-cv-generation.md`, `spec-20250923-api.md`, `spec-20250923-llm.md`
**Related ADRs:** [ADR-015-multi-source-artifact-preprocessing](../adrs/adr-015-multi-source-artifact-preprocessing.md)

## Acceptance Criteria

- [ ] Artifacts with multiple data sources are processed asynchronously when uploaded
- [ ] GitHub repositories are analyzed for languages, frameworks, metrics (commits, stars, contributors)
- [ ] PDF documents are parsed to extract text, achievements, technologies, and quantified metrics
- [ ] Video/audio files are transcribed and analyzed for key topics and technologies
- [ ] Web links are scraped and analyzed for relevant content
- [ ] All extracted content is unified into a single comprehensive description using LLM
- [ ] Technologies and achievements are extracted and normalized from all sources
- [ ] Embeddings are generated for vector similarity search
- [ ] Preprocessing completes within 5 minutes for P95 of artifacts
- [ ] Processing status is tracked and displayed to users in real-time
- [ ] Failed processing gracefully degrades with meaningful error messages
- [ ] Preprocessed data is stored efficiently with compression for raw content

## Design Changes

### API Endpoints
**New endpoints:**
```python
# Artifact preprocessing management
POST /api/v1/artifacts/{id}/preprocess/  # Trigger preprocessing
GET /api/v1/artifacts/{id}/preprocessing-status/  # Check status
POST /api/v1/artifacts/batch-preprocess/  # Batch processing

# Preprocessing results
GET /api/v1/artifacts/{id}/preprocessed/  # Get unified description
GET /api/v1/artifacts/{id}/extracted-technologies/  # Get tech list
GET /api/v1/artifacts/{id}/extracted-achievements/  # Get achievements
```

### Database Schema Changes
```sql
-- New preprocessing tables
CREATE TABLE artifact_preprocessing_jobs (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES artifacts(id),
    status VARCHAR(20) CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0
);

CREATE TABLE preprocessed_artifacts (
    id SERIAL PRIMARY KEY,
    artifact_id INTEGER REFERENCES artifacts(id) UNIQUE,
    unified_description TEXT NOT NULL,
    extracted_technologies JSONB,
    extracted_achievements JSONB,
    quantified_metrics JSONB,
    embedding_vector VECTOR(1536), -- pgvector for similarity search
    processing_confidence FLOAT CHECK (processing_confidence BETWEEN 0 AND 1),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE extracted_content (
    id SERIAL PRIMARY KEY,
    preprocessing_job_id INTEGER REFERENCES artifact_preprocessing_jobs(id),
    source_type VARCHAR(50), -- 'github', 'pdf', 'video', 'audio', 'link'
    raw_data JSONB, -- Compressed extracted content
    processed_summary TEXT,
    extraction_success BOOLEAN,
    extraction_confidence FLOAT,
    processing_duration_seconds INTEGER
);

-- Indexes for performance
CREATE INDEX idx_preprocessed_artifacts_embedding ON preprocessed_artifacts USING ivfflat (embedding_vector vector_cosine_ops);
CREATE INDEX idx_artifact_preprocessing_jobs_status ON artifact_preprocessing_jobs (status, created_at);
```

### UI Changes
**Artifact Upload Flow:**
- Real-time processing status indicator with progress bar
- Processing stages displayed: "Extracting GitHub data", "Analyzing documents", etc.
- Processing queue position for user awareness
- Preview of extracted technologies and achievements as they become available

**New Components:**
- `<PreprocessingStatusCard />` - Shows current processing status
- `<ExtractedContentPreview />` - Preview of unified description and extracted data
- `<ProcessingQueueIndicator />` - Shows position in processing queue

## Test & Eval Plan

### Unit Tests
- GitHub repository extractor with mock API responses
- PDF document parser with sample documents
- Video/audio transcription with test media files
- LLM unified description generation with known inputs
- Embedding generation consistency checks
- Database schema validation and constraints

### Integration Tests
- End-to-end preprocessing pipeline with multi-source artifacts
- Error handling for failed extractions (network timeouts, API rate limits)
- Celery task processing with Redis broker
- Database transaction integrity during concurrent processing
- Preprocessing queue management under load

### AI Evaluation Thresholds
**Unified Description Quality:**
- User satisfaction rating ≥8/10 for description accuracy
- Description coherence score ≥0.8 (using sentence transformer evaluation)
- Technology extraction accuracy ≥85% compared to manual review
- Achievement extraction relevance ≥80% based on user validation

**Processing Performance:**
- P95 processing time ≤300 seconds for complete multi-source analysis
- Processing success rate ≥95% across all source types
- Queue throughput ≥20 artifacts per minute during peak load

### Golden Test Cases
```python
# Test case: Multi-source React project
input_artifact = {
    "sources": [
        {"type": "github", "url": "https://github.com/user/react-dashboard"},
        {"type": "pdf", "file": "project_documentation.pdf"},
        {"type": "video", "file": "demo_presentation.mp4"}
    ]
}
expected_technologies = ["React", "TypeScript", "Node.js", "PostgreSQL", "AWS"]
expected_achievements = [
    "Built responsive dashboard serving 10k+ daily users",
    "Reduced page load time by 40% through optimization",
    "Implemented automated testing with 90% code coverage"
]
```

## Telemetry & Metrics

### Processing Metrics
**Dashboards:**
- Processing success rate by source type (GitHub, PDF, video, etc.)
- Average processing duration per source type
- Queue depth and processing throughput
- LLM API usage and token consumption
- Storage utilization for preprocessed artifacts

**Alerts:**
- Processing success rate <95% (P1 alert)
- Average processing time >300 seconds (P2 alert)
- Queue backlog >100 artifacts (P1 alert)
- Storage utilization >80% (P2 alert)
- LLM API error rate >5% (P1 alert)

### Quality Metrics
- User satisfaction ratings for unified descriptions
- Technology extraction accuracy (manual validation sample)
- Achievement relevance scoring (user feedback)
- Processing confidence scores distribution

### Performance Monitoring
```python
# Prometheus metrics
processing_duration = Histogram(
    'artifact_preprocessing_duration_seconds',
    'Time spent preprocessing artifacts',
    ['source_type', 'success']
)

extraction_success_rate = Counter(
    'artifact_extraction_total',
    'Total extraction attempts',
    ['source_type', 'status']
)
```

## Edge Cases & Risks

### Processing Failures
**Risk:** GitHub API rate limits or network failures during processing
**Mitigation:** Exponential backoff retry with 3 attempts, fallback to basic artifact data

**Risk:** PDF parsing failures for corrupted or image-only documents
**Mitigation:** OCR fallback for image PDFs, graceful degradation with error logging

**Risk:** Video transcription failures for poor audio quality
**Mitigation:** Audio enhancement preprocessing, confidence scoring for transcription quality

### Data Quality Issues
**Risk:** LLM generates inaccurate unified descriptions
**Mitigation:** Confidence scoring, user validation feedback loop, prompt optimization

**Risk:** Technology extraction misses domain-specific tools
**Mitigation:** Expandable technology dictionary, user correction interface

### Scalability Concerns
**Risk:** Processing queue backlog during peak usage
**Mitigation:** Auto-scaling Celery workers, priority queues for premium users

**Risk:** Storage growth for preprocessed artifacts
**Mitigation:** Data retention policies, content compression, archived storage tiers

### System Reliability
**Risk:** Single point of failure in preprocessing pipeline
**Mitigation:** Distributed task processing, dead letter queues for failed jobs

**Risk:** Database performance degradation with vector similarity searches
**Mitigation:** pgvector index optimization, query result caching, read replicas