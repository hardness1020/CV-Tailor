# ADR: LangChain for Multi-Format Document Processing

**File:** docs/adrs/adr-001-document-processing-framework.md
**Status:** Draft

## Context

CV Tailor needs to process diverse artifact types (PDF documents, GitHub repositories, web profiles) into structured content for LLM analysis. Current system has basic PDF extraction using PyPDF2 and GitHub API calls, but lacks unified processing pipeline for scalable multi-format support.

Requirements:
- Support PDF, DOCX, Markdown, HTML, plain text extraction
- GitHub repository content analysis (README, code structure)
- Web content scraping and processing
- Chunking strategies for large documents
- Integration with existing Django/Celery architecture

## Decision

Adopt **LangChain** as the primary document processing framework with targeted loaders:

1. **UnstructuredPDFLoader** for PDF document extraction
2. **GitHubIssuesLoader** and **GithubFileLoader** for repository analysis
3. **UnstructuredHTMLLoader** for web profile processing
4. **Custom content extractors** wrapped in LangChain document format
5. **CharacterTextSplitter** for chunking large content

Integration approach:
- LangChain processors called from existing Celery tasks
- Document objects serialized to JSON for database storage
- Gradual migration from current PyPDF2 implementation

## Consequences

### Positive
+ **Unified interface**: Consistent Document objects across all formats
+ **Rich ecosystem**: 700+ document loaders available
+ **Chunking strategies**: Built-in text splitting optimized for LLM context windows
+ **Community support**: Active development and extensive documentation
+ **Future extensibility**: Easy addition of new document types (DOCX, PPT, etc.)

### Negative
− **Dependency weight**: Large library with many unused components
− **Upgrade complexity**: Framework updates may break existing processors
− **Performance overhead**: Additional abstraction layers vs. direct libraries
− **Learning curve**: Team needs familiarity with LangChain patterns

## Alternatives

1. **Custom extractors**: Direct use of PyPDF2, Markdown parsers, web scrapers
   - Pros: Lightweight, full control
   - Cons: Significant development effort, maintenance burden

2. **Unstructured.io**: Specialized document processing service
   - Pros: High-quality extraction, API-based
   - Cons: External dependency, per-document costs

3. **Apache Tika**: Java-based universal document processor
   - Pros: Mature, supports many formats
   - Cons: JVM dependency, Python integration complexity

## Rollback Plan

- **Gradual rollback**: Keep existing PyPDF2 processors as fallback
- **Document compatibility**: JSON serialization allows processor switching
- **Performance monitoring**: Revert if processing latency exceeds thresholds
- **Custom extraction**: Implement direct processors if LangChain proves inadequate

## Links

- **TECH-SPEC**: `spec-20240924-llm-artifacts.md`
- **Feature**: `ft-llm-001-content-extraction.md` (pending)