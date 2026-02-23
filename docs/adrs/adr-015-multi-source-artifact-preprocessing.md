# ADR — Multi-Source Artifact Preprocessing Strategy

**Status:** Draft
**Date:** 2025-09-27
**Deciders:** Engineering, ML Team, Product
**Technical Story:** Design preprocessing pipeline for artifacts containing multiple data sources

## Context and Problem Statement

Artifacts in the CV generation system contain multiple data sources (GitHub repositories, PDF documents, videos, presentations, external links). To generate effective CV bullet points and perform accurate artifact selection, we need to extract meaningful information from these diverse sources and create a unified representation.

**Core Challenge:** Processing multi-source artifacts on-the-fly during CV generation would be:
- **Too slow** (GitHub API calls, PDF parsing, video processing)
- **Inconsistent** (network failures, API rate limits, varying data quality)
- **Resource intensive** (CPU/memory spikes during CV generation)
- **Poor UX** (users waiting 30+ seconds for processing)

We need to decide when and how to process these multi-source artifacts to balance performance, accuracy, and system resources.

## Decision Drivers

- **Response Time:** CV generation must complete within 30 seconds
- **Consistency:** Same artifact should produce same results across generations
- **Accuracy:** Unified representation must capture key information from all sources
- **Resource Efficiency:** Processing shouldn't overload the system during peak usage
- **Data Freshness:** Balance between current data and processing overhead
- **Error Handling:** Graceful degradation when some sources are unavailable
- **Scalability:** Support 1000+ users with 10+ artifacts each
- **Cost Management:** Minimize LLM API calls and computational resources

## Considered Options

### Option A: Real-Time Processing During CV Generation
- **Approach:** Process all data sources when user requests CV generation
- **Pros:** Always current data, no storage overhead, simple architecture
- **Cons:** Very slow response times (60+ seconds), unreliable, resource spikes

### Option B: Batch Processing Overnight
- **Approach:** Process all artifacts in daily/weekly batch jobs
- **Pros:** Predictable resource usage, can handle complex processing
- **Cons:** Stale data, inflexible timing, all-or-nothing approach

### Option C: Async Preprocessing on Upload (Recommended)
- **Approach:** Process artifacts asynchronously when uploaded, store unified representation
- **Pros:** Fast CV generation, consistent results, fresh data, graceful error handling, early positive feedback
- **Cons:** Additional storage requirements, complex preprocessing pipeline

### Option D: Hybrid: Cache + On-Demand
- **Approach:** Cache processed results, refresh on-demand with fallback
- **Pros:** Balance of freshness and performance
- **Cons:** Complex cache invalidation, still has latency issues

## Decision Outcome

**Chosen Option: Option C - Async Preprocessing on Upload**

### Rationale

1. **Performance:** Enables sub-30-second CV generation by preprocessing heavy operations
2. **User Experience:** Users get immediate feedback on upload status and processing progress
3. **Reliability:** Network failures during preprocessing don't affect CV generation
4. **Resource Management:** Spreads computational load across time rather than peaks
5. **Data Quality:** Allows for quality validation and error correction during preprocessing
6. **Scalability:** Processing queue can scale independently from CV generation

### Preprocessing Pipeline Design

```python
# Artifact Upload and Preprocessing Flow
class ArtifactPreprocessingPipeline:
    def __init__(self):
        self.extractors = {
            "github": GitHubRepositoryExtractor(),
            "pdf": PDFDocumentExtractor(),
            "video": VideoMediaExtractor(),
            "audio": AudioMediaExtractor(),
            "link": WebLinkExtractor()
        }
        self.llm_service = LLMDescriptionGenerator()
        self.embedding_service = EmbeddingGenerator()

    async def process_artifact(self, artifact_upload: ArtifactUpload) -> PreprocessedArtifact:
        """Complete preprocessing pipeline for multi-source artifact"""

        # Stage 1: Extract content from all sources
        extracted_content = await self._extract_all_sources(artifact_upload.sources)

        # Stage 2: Generate unified description AND extract technologies using LLM (single call)
        llm_analysis = await self._analyze_artifact_with_llm(extracted_content)

        # Stage 3: Generate embeddings for similarity search
        embedding_vector = await self._generate_embeddings(llm_analysis.unified_description)

        # Stage 4: Store preprocessed artifact
        preprocessed_artifact = await self._store_preprocessed_artifact(
            artifact_upload.user_id,
            llm_analysis.unified_description,
            llm_analysis.extracted_technologies,
            llm_analysis.extracted_achievements,
            llm_analysis.quantified_metrics,
            embedding_vector,
            extracted_content
        )

        return preprocessed_artifact

    async def _extract_all_sources(
        self,
        sources: List[DataSource]
    ) -> Dict[str, ExtractedContent]:
        """Extract content from all data sources in parallel"""

        extraction_tasks = []
        for source in sources:
            extractor = self.extractors.get(source.type)
            if extractor:
                task = self._extract_with_timeout(extractor, source)
                extraction_tasks.append(task)

        # Process all sources concurrently with timeout
        results = await asyncio.gather(*extraction_tasks, return_exceptions=True)

        # Handle extraction results and errors
        extracted_content = {}
        for i, result in enumerate(results):
            source = sources[i]
            if isinstance(result, Exception):
                logger.warning(f"Failed to extract {source.type}: {result}")
                extracted_content[source.type] = ExtractedContent(
                    success=False,
                    error=str(result),
                    confidence=0.0
                )
            else:
                extracted_content[source.type] = result

        return extracted_content

    async def _extract_with_timeout(
        self,
        extractor: ContentExtractor,
        source: DataSource
    ) -> ExtractedContent:
        """Extract content with timeout and error handling"""
        try:
            # Set timeout based on source type
            timeout = self._get_extraction_timeout(source.type)

            return await asyncio.wait_for(
                extractor.extract(source),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            raise ExtractionTimeoutError(f"{source.type} extraction timed out")
        except Exception as e:
            raise ExtractionError(f"Failed to extract {source.type}: {str(e)}")

    def _get_extraction_timeout(self, source_type: str) -> int:
        """Get appropriate timeout for different source types"""
        timeouts = {
            "github": 60,    # GitHub API calls can be slow
            "pdf": 30,       # PDF parsing is usually fast
            "video": 120,    # Video processing can be slow
            "audio": 90,     # Audio transcription takes time
            "link": 45       # Web scraping varies
        }
        return timeouts.get(source_type, 30)
```

### Content Extraction Components

```python
# GitHub Repository Extractor
class GitHubRepositoryExtractor(ContentExtractor):
    def __init__(self):
        self.github_client = GitHubAPIClient()

    async def extract(self, source: DataSource) -> ExtractedContent:
        """Extract comprehensive information from GitHub repository"""
        repo_url = source.url
        repo_info = await self.github_client.get_repository_info(repo_url)

        # Extract key information
        extracted_data = {
            "languages": repo_info.get("languages", []),
            "frameworks": await self._detect_frameworks(repo_info),
            "lines_of_code": repo_info.get("size", 0),
            "commit_count": repo_info.get("commits_count", 0),
            "contributors": repo_info.get("contributors_count", 1),
            "stars": repo_info.get("stargazers_count", 0),
            "forks": repo_info.get("forks_count", 0),
            "topics": repo_info.get("topics", []),
            "readme_content": await self._extract_readme(repo_info),
            "key_files": await self._analyze_key_files(repo_info),
            "tech_stack": await self._detect_tech_stack(repo_info)
        }

        # Generate summary
        summary = await self._generate_repo_summary(extracted_data)

        return ExtractedContent(
            type="github",
            raw_data=extracted_data,
            processed_summary=summary,
            technologies=extracted_data["languages"] + extracted_data["frameworks"],
            achievements=await self._extract_achievements_from_repo(extracted_data),
            confidence=self._calculate_extraction_confidence(extracted_data),
            success=True
        )

# PDF Document Extractor
class PDFDocumentExtractor(ContentExtractor):
    def __init__(self):
        self.pdf_parser = PDFParser()
        self.nlp_processor = NLPProcessor()

    async def extract(self, source: DataSource) -> ExtractedContent:
        """Extract information from PDF documents"""
        pdf_content = await self.pdf_parser.extract_text(source.file_path)

        # Process document content
        extracted_data = {
            "full_text": pdf_content.text,
            "page_count": pdf_content.page_count,
            "document_type": await self._classify_document_type(pdf_content.text),
            "key_sections": await self._extract_sections(pdf_content.text),
            "technologies_mentioned": await self._extract_technologies(pdf_content.text),
            "achievements": await self._extract_achievements(pdf_content.text),
            "metrics": await self._extract_quantified_metrics(pdf_content.text),
            "citations": await self._extract_citations(pdf_content.text)
        }

        # Generate summary
        summary = await self._generate_document_summary(extracted_data)

        return ExtractedContent(
            type="pdf",
            raw_data=extracted_data,
            processed_summary=summary,
            technologies=extracted_data["technologies_mentioned"],
            achievements=extracted_data["achievements"],
            confidence=self._calculate_extraction_confidence(extracted_data),
            success=True
        )

# Video/Media Extractor
class VideoMediaExtractor(ContentExtractor):
    def __init__(self):
        self.transcription_service = TranscriptionService()
        self.video_processor = VideoProcessor()

    async def extract(self, source: DataSource) -> ExtractedContent:
        """Extract information from video/audio files"""

        # Extract metadata
        metadata = await self.video_processor.extract_metadata(source.file_path)

        # Generate transcript if audio available
        transcript = None
        if metadata.has_audio:
            transcript = await self.transcription_service.transcribe(source.file_path)

        extracted_data = {
            "duration_seconds": metadata.duration,
            "file_size": metadata.size,
            "resolution": metadata.resolution,
            "has_audio": metadata.has_audio,
            "transcript": transcript.text if transcript else None,
            "key_topics": await self._extract_topics_from_transcript(transcript.text) if transcript else [],
            "mentioned_technologies": await self._extract_tech_from_transcript(transcript.text) if transcript else [],
            "presentation_type": await self._classify_presentation_type(metadata, transcript)
        }

        # Generate summary
        summary = await self._generate_media_summary(extracted_data)

        return ExtractedContent(
            type="video",
            raw_data=extracted_data,
            processed_summary=summary,
            technologies=extracted_data["mentioned_technologies"],
            achievements=await self._extract_achievements_from_transcript(transcript.text) if transcript else [],
            confidence=self._calculate_extraction_confidence(extracted_data),
            success=True
        )
```

### LLM-Based Unified Description Generation

```python
# Comprehensive LLM Artifact Analyzer
@dataclass
class LLMAnalysisResult:
    unified_description: str
    extracted_technologies: List[str]
    extracted_achievements: List[str]
    quantified_metrics: Dict[str, Any]
    processing_confidence: float

class LLMArtifactAnalyzer:
    def __init__(self):
        self.llm_client = LLMClient()

    async def analyze_artifact_with_llm(
        self,
        extracted_content: Dict[str, ExtractedContent]
    ) -> LLMAnalysisResult:
        """Comprehensive analysis: generate description AND extract technologies/achievements in single LLM call"""

        # Build comprehensive prompt for unified analysis
        prompt = self._build_comprehensive_analysis_prompt(extracted_content)

        # Single LLM call for complete analysis
        response = await self.llm_client.complete(
            prompt=prompt,
            model="gpt-4",
            max_tokens=1500,
            temperature=0.3
        )

        # Parse the comprehensive response
        analysis_result = self._parse_comprehensive_response(response.content)

        return analysis_result

    def _build_comprehensive_analysis_prompt(
        self,
        extracted_content: Dict[str, ExtractedContent]
    ) -> str:
        """Build single comprehensive prompt for description + technology + achievement extraction"""

        prompt_parts = [
            "Analyze this project/artifact from multiple data sources and provide a comprehensive analysis.",
            ""
        ]

        # Add content from each source
        for source_type, content in extracted_content.items():
            if content.success and content.processed_summary:
                prompt_parts.extend([
                    f"=== {source_type.upper()} SOURCE ===",
                    f"Summary: {content.processed_summary}",
                    f"Raw Technologies: {', '.join(content.technologies)}",
                    f"Raw Achievements: {'; '.join(content.achievements)}",
                    ""
                ])

        prompt_parts.extend([
            "TASK: Provide a complete analysis in the following JSON format:",
            "",
            "{",
            '  "unified_description": "150-400 word professional description synthesizing all sources, emphasizing technical achievements and quantified impact",',
            '  "extracted_technologies": ["normalized", "technology", "names"],',
            '  "extracted_achievements": ["specific", "quantified", "achievements"],',
            '  "quantified_metrics": {"metric_type": "value", "improvement": "percentage"},',
            '  "processing_confidence": 0.0-1.0',
            "}",
            "",
            "REQUIREMENTS FOR UNIFIED DESCRIPTION:",
            "- Synthesize information from ALL sources into coherent narrative",
            "- Emphasize technical skills, quantified achievements, and project impact",
            "- Use professional language suitable for CV/resume content",
            "- Highlight unique aspects and differentiators",
            "- Include specific metrics and outcomes where available",
            "",
            "REQUIREMENTS FOR TECHNOLOGIES:",
            "- Extract ALL technical skills, frameworks, programming languages, tools",
            "- Include databases, cloud platforms, methodologies, development tools",
            "- Normalize names (e.g., 'React.js' → 'React', 'nodejs' → 'Node.js')",
            "- Remove duplicates and focus on CV-relevant skills",
            "",
            "REQUIREMENTS FOR ACHIEVEMENTS:",
            "- Extract specific, quantified accomplishments",
            "- Focus on measurable impact and results",
            "- Include performance improvements, user metrics, business value",
            "- Make achievements concrete and verifiable",
            "",
            "Generate the comprehensive analysis:"
        ])

        return "\n".join(prompt_parts)

    def _parse_comprehensive_response(self, response_content: str) -> LLMAnalysisResult:
        """Parse comprehensive LLM response into structured result"""
        try:
            import json

            # Try to parse JSON response
            analysis_data = json.loads(response_content.strip())

            return LLMAnalysisResult(
                unified_description=analysis_data.get("unified_description", ""),
                extracted_technologies=analysis_data.get("extracted_technologies", []),
                extracted_achievements=analysis_data.get("extracted_achievements", []),
                quantified_metrics=analysis_data.get("quantified_metrics", {}),
                processing_confidence=float(analysis_data.get("processing_confidence", 0.7))
            )

        except (json.JSONDecodeError, TypeError, ValueError) as e:
            # Fallback parsing for non-JSON responses
            logger.warning(f"Failed to parse LLM analysis response: {e}")

            # Extract description (usually the largest text block)
            lines = response_content.split('\n')
            description_lines = []
            technology_lines = []
            achievement_lines = []

            current_section = None
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Detect sections
                if any(keyword in line.lower() for keyword in ['description:', 'summary:']):
                    current_section = 'description'
                    continue
                elif any(keyword in line.lower() for keyword in ['technolog', 'skill', 'framework']):
                    current_section = 'technology'
                    continue
                elif any(keyword in line.lower() for keyword in ['achievement', 'accomplishment', 'result']):
                    current_section = 'achievement'
                    continue

                # Collect content based on current section
                if current_section == 'description':
                    description_lines.append(line)
                elif current_section == 'technology':
                    # Extract technology names
                    tech_items = line.replace('-', '').replace('•', '').replace('*', '').strip()
                    if tech_items and len(tech_items) < 50:
                        technology_lines.append(tech_items)
                elif current_section == 'achievement':
                    achievement_lines.append(line)

            return LLMAnalysisResult(
                unified_description=' '.join(description_lines) if description_lines else "Analysis unavailable",
                extracted_technologies=technology_lines[:15],  # Limit to reasonable number
                extracted_achievements=achievement_lines[:10],
                quantified_metrics={},
                processing_confidence=0.5  # Lower confidence for fallback parsing
            )
```

## Positive Consequences

- **Fast CV Generation:** Preprocessing eliminates 80%+ of processing time during CV generation (no real-time multi-source processing)
- **Consistent Results:** Same artifact always produces same unified description and extracted technologies
- **Dynamic Job Relevance:** Relevance calculated fresh for each job, ensuring accurate matching without stale pre-computed scores
- **Better Error Handling:** Network/API failures during preprocessing don't affect user-facing CV generation
- **Improved Accuracy:** Single comprehensive LLM call produces better coherence between description and extracted technologies
- **Scalable Architecture:** Processing queue can scale independently and handle load spikes
- **Efficient LLM Usage:** One comprehensive analysis call instead of multiple separate calls for description, technologies, and achievements
- **Fresh Similarity Matching:** Each job gets precise similarity calculation using current job description

## Negative Consequences

- **Storage Overhead:** Storing preprocessed artifacts increases database size
- **Processing Complexity:** More complex system with preprocessing pipeline and job queues
- **Data Freshness:** Some delay between artifact upload and availability for CV generation
- **Processing Failures:** Need robust error handling and retry mechanisms for preprocessing
- **Resource Requirements:** Background processing requires additional computational resources

## Mitigation Strategies

### Storage Optimization
```python
# Implement data retention policies
class PreprocessedArtifactManager:
    async def cleanup_old_versions(self):
        """Remove old preprocessed versions to manage storage"""
        # Keep only latest version per artifact
        # Archive or compress old versions
        # Implement LRU eviction for inactive users

# Compress stored content
class ContentCompressor:
    def compress_extracted_content(self, content: ExtractedContent) -> bytes:
        """Compress raw extracted content for storage efficiency"""
        return gzip.compress(json.dumps(content.raw_data).encode())
```

### Processing Reliability
```python
# Robust retry mechanism
class ProcessingJobManager:
    async def retry_failed_jobs(self):
        """Retry failed preprocessing jobs with exponential backoff"""
        failed_jobs = await ArtifactProcessingJob.objects.filter(
            status='failed',
            retry_count__lt=3
        )

        for job in failed_jobs:
            await self._schedule_retry(job)

# Graceful degradation
class FallbackProcessor:
    async def create_basic_preprocessed_artifact(
        self,
        artifact_upload: ArtifactUpload
    ) -> PreprocessedArtifact:
        """Create basic preprocessed artifact when full processing fails"""
        # Use artifact title and user-provided description as fallback
        # Generate basic embedding from available text
        # Set low confidence score to indicate limited processing
```

### Performance Monitoring
```python
# Processing metrics
class PreprocessingMetrics:
    def __init__(self):
        self.processing_duration = Histogram(
            'artifact_preprocessing_duration_seconds',
            'Time spent preprocessing artifacts',
            ['source_type', 'success']
        )

        self.processing_success_rate = Counter(
            'artifact_preprocessing_total',
            'Total preprocessing attempts',
            ['source_type', 'status']
        )
```

## Implementation Phases

### Phase 1: Basic Preprocessing (MVP)
- Simple text extraction from each source type
- Basic LLM-generated descriptions
- Simple embedding generation
- Essential storage schema

### Phase 2: Enhanced Processing
- Advanced content extraction (code analysis, document structure)
- Sophisticated unified description generation
- Pre-computed job relevance scores
- Processing quality metrics

### Phase 3: Optimization
- Parallel processing optimization
- Advanced error recovery
- Storage optimization
- Real-time processing status updates

## Monitoring and Success Metrics

- **Processing Success Rate:** ≥95% of artifacts successfully preprocessed
- **Processing Time:** P95 ≤5 minutes for complete multi-source analysis
- **Storage Efficiency:** <50MB average per preprocessed artifact
- **CV Generation Speed:** ≤30 seconds using preprocessed artifacts (no real-time job relevance calculation needed)
- **LLM Analysis Quality:** ≥90% user satisfaction with unified descriptions and extracted technologies
- **Technology Extraction Accuracy:** ≥85% of extracted technologies validated as relevant by users
- **Dynamic Similarity Performance:** Artifact selection completes in <5 seconds using vector similarity
- **System Reliability:** ≥99.5% preprocessing service uptime

## References

- **Async Processing Patterns:** Best practices for background job processing
- **Content Extraction Research:** Academic papers on multi-modal content analysis
- **LLM Optimization:** Studies on efficient prompt design for content synthesis

## Related ADRs

- [ADR-016-three-bullets-per-artifact](adr-016-three-bullets-per-artifact.md)
- [ADR-013-artifact-selection-algorithm](adr-013-artifact-selection-algorithm.md)
- [ADR-014-llm-prompt-design-strategy](adr-014-llm-prompt-design-strategy.md)

