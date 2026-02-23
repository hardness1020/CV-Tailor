# Feature — 013 GitHub Agent Traversal

**File:** docs/features/ft-013-github-agent-traversal.md
**Owner:** Engineering Team
**ID:** ft-013
**TECH-SPECs:** `spec-artifact-upload-enrichment-flow.md` (v1.3.0), `spec-llm.md` (v3.1.0)
**PRD:** `docs/prds/prd.md` (v1.3.0)
**ADR:** `adr-023-agent-style-github-traversal.md`
**Discovery:** `docs/discovery/ft-013-github-agent-codebase-discovery.md`
**Status:** In Development
**Type:** Large (BREAKING CHANGES - replaces legacy GitHub extraction)

---

## Summary

Replace legacy fixed-file GitHub repository extraction with intelligent agent-based traversal. The new system uses LLM-powered file prioritization, multi-format hybrid analysis, and 4-phase adaptive processing to extract comprehensive context from GitHub repositories.

**Key Impact:**
- Technology extraction accuracy: 60% → 85% (+40%)
- Enrichment confidence: 0.65 → 0.82 avg (+25%)
- Enrichment failure rate: 15% → 7.5% (-50%)
- Cost per repo: $0.015 → $0.025 (+$0.01, +67%)

**Deployment:** Direct replacement with canary rollout (1 pod → 25% → 100%)

---

## Existing Implementation Analysis

**From Stage B Discovery (`docs/discovery/ft-013-github-agent-codebase-discovery.md`):**

### Current Limitations

**Legacy Implementation:** `llm_services/services/core/document_loader_service.py:288-338`
- Fixed file selection: README + first 10 source files
- Arbitrary depth limit: path depth ≤ 3
- No config file parsing: Misses `package.json`, `requirements.txt`, `Cargo.toml`
- No CI/CD analysis: Ignores `.github/workflows/`, test coverage configs
- No documentation parsing: Skips `docs/`, `CONTRIBUTING.md`

**Quality Impact:**
- 60-80% of repository context never analyzed
- Config files with direct dependency listings ignored
- CI/CD metrics (test coverage, workflows) not extracted
- Architecture patterns not detected

### Reusable Components Identified

| Component | Location | Reuse Strategy |
|-----------|----------|----------------|
| **BaseLLMService** | `llm_services/services/base/base_service.py` | Inherit for circuit breaker + tracking |
| **APIClientManager** | `llm_services/services/base/client_manager.py` | Use for all LLM calls (GPT-5, GPT-5-mini) |
| **DocumentLoaderService** | `llm_services/services/core/document_loader_service.py` | Use `get_github_repo_stats()` method |
| **EvidenceContentExtractor** | `llm_services/services/core/evidence_content_extractor.py` | Replace `extract_github_content()` method |
| **PerformanceTracker** | `llm_services/services/reliability/performance_tracker.py` | Track agent metrics |
| **CircuitBreaker** | `llm_services/services/reliability/circuit_breaker.py` | Inherited via BaseLLMService |

### Patterns to Follow

**Service Layer Pattern** (from `llm_services/` architecture):
```
base/            # Foundation (BaseLLMService, APIClientManager)
  ↓
core/            # Business logic (NEW: GitHubRepositoryAgent, HybridFileAnalyzer)
  ↓
infrastructure/  # Supporting components (ModelSelector)
  ↓
reliability/     # Fault tolerance (CircuitBreaker, PerformanceTracker)
```

**Async Processing Pattern** (from `artifacts/tasks.py`):
- Service returns data (no DB saves)
- Task layer handles persistence + quality validation
- Separation of concerns: data transformation vs. storage

### Code to Replace

**File:** `llm_services/services/core/evidence_content_extractor.py:107`

**Method:** `extract_github_content()`
- **Action:** Complete replacement (no fallback)
- **Strategy:** Rewrite internals, keep signature unchanged
- **Risk:** No automatic fallback if agent fails

### Dependencies

**Hard Dependencies:**
- `DocumentLoaderService.get_github_repo_stats()` - GitHub API metadata
- `APIClientManager` - LLM calls (GPT-5 for file selection, GPT-5-mini for parsing)
- `EmbeddingService` - Generate embeddings for analysis results
- `PerformanceTracker` - Cost tracking, latency monitoring

**No Dependencies On:**
- `TailoredContentService` (CV generation, not extraction)
- `ArtifactRankingService` (job matching, not GitHub analysis)
- `BulletGenerationService` (generation app, separate from llm_services)

---

## Architecture Conformance

### Layer Assignment

**New Services (core layer):**
1. **`llm_services/services/core/github_repository_agent.py`**
   - Responsibility: 4-phase repository analysis orchestration
   - Inherits from: `BaseLLMService`
   - Uses: `APIClientManager`, `DocumentLoaderService`, `HybridFileAnalyzer`

2. **`llm_services/services/core/hybrid_file_analyzer.py`**
   - Responsibility: Multi-format file content parsing
   - Methods: `analyze_config_files()`, `analyze_source_code()`, `analyze_infrastructure()`, `analyze_documentation()`, `synthesize_insights()`

**Modified Services:**
3. **`llm_services/services/core/evidence_content_extractor.py`**
   - Change type: Method replacement
   - Method: `extract_github_content()` - complete rewrite, signature unchanged

### Pattern Compliance

✅ **Follows llm_services four-layer architecture**
- base → core → infrastructure → reliability

✅ **Service layer separation of concerns**
- GitHubRepositoryAgent: Pure data transformation, no DB saves
- Task layer (`artifacts/tasks.py`): Handles persistence after quality validation

✅ **Circuit breaker integration**
- Inherited via BaseLLMService, automatic fault tolerance

✅ **Performance tracking**
- Uses PerformanceTracker for cost + latency monitoring

✅ **Async processing**
- All methods async (`async def`), compatible with Celery async tasks

### Database Schema Changes

**New Table:** `github_repository_analysis`
```sql
CREATE TABLE github_repository_analysis (
    id UUID PRIMARY KEY,
    evidence_id INTEGER REFERENCES evidence(id),

    -- Phase 1: Reconnaissance
    repo_structure JSONB,
    detected_project_type VARCHAR(50),
    primary_language VARCHAR(50),
    languages_breakdown JSONB,

    -- Phase 2: File selection
    files_loaded JSONB,
    total_tokens_used INTEGER,
    selection_reasoning TEXT,

    -- Phase 3: Hybrid analysis
    config_analysis JSONB,
    source_analysis JSONB,
    infrastructure_analysis JSONB,
    documentation_analysis JSONB,

    -- Phase 4: Refinement
    refinement_iterations INTEGER DEFAULT 1,
    additional_files_loaded JSONB,

    -- Quality metrics
    analysis_confidence FLOAT,
    consistency_score FLOAT,
    processing_time_ms INTEGER,
    llm_cost_usd DECIMAL(10, 6),

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

**Extended Table:** `extracted_content`
```sql
ALTER TABLE extracted_content ADD COLUMN agent_analysis_id UUID
REFERENCES github_repository_analysis(id) ON DELETE SET NULL;
```

---

## Acceptance Criteria

### Phase 1: Reconnaissance

- [ ] **AC1.1:** Agent detects project type (web_app, library, cli_tool, framework) with ≥80% accuracy
- [ ] **AC1.2:** Agent extracts language breakdown from GitHub API within 2 seconds
- [ ] **AC1.3:** Agent builds directory tree (up to 3 levels deep) with file count by type
- [ ] **AC1.4:** Agent identifies key directories (`/src`, `/app`, `/pkg`, `/lib`) correctly

### Phase 2: Intelligent File Selection

- [ ] **AC2.1:** Agent prioritizes config files (package.json, requirements.txt, Cargo.toml, go.mod, pom.xml) as "critical"
- [ ] **AC2.2:** Agent respects token budget (loads 15-20 files within 8K tokens)
- [ ] **AC2.3:** Agent excludes vendor/node_modules/generated files automatically
- [ ] **AC2.4:** Agent selection reasoning is stored and human-readable
- [ ] **AC2.5:** LLM file selection call completes within 5 seconds (P95)

### Phase 3: Hybrid File Analysis

- [ ] **AC3.1:** Config parser extracts dependencies from package.json with versions (e.g., "react": "^18.2.0")
- [ ] **AC3.2:** Config parser extracts dependencies from requirements.txt, Cargo.toml, go.mod
- [ ] **AC3.3:** Source analyzer detects architecture patterns (microservices, monolith, serverless)
- [ ] **AC3.4:** Infrastructure analyzer parses Dockerfile and extracts base image
- [ ] **AC3.5:** Infrastructure analyzer extracts CI/CD workflows from `.github/workflows/*.yml`
- [ ] **AC3.6:** Documentation analyzer extracts quantitative metrics from README/docs (e.g., "99.9% uptime")
- [ ] **AC3.7:** Synthesis generates consistency score (0-1) based on cross-source agreement
- [ ] **AC3.8:** Hybrid analysis completes within 20 seconds (P95)

### Phase 4: Iterative Refinement (Optional)

- [ ] **AC4.1:** Agent evaluates confidence threshold (0.75) and decides if more files needed
- [ ] **AC4.2:** If confidence <0.75, agent requests 3-5 additional specific files
- [ ] **AC4.3:** Refinement stops after 2 iterations or when confidence ≥0.75
- [ ] **AC4.4:** Refinement iteration count is tracked in `github_repository_analysis.refinement_iterations`

### Quality & Performance

- [ ] **AC5.1:** Technology extraction accuracy ≥85% (measured on 50-repo golden set)
- [ ] **AC5.2:** Enrichment confidence average ≥0.80 (baseline: 0.65)
- [ ] **AC5.3:** Agent success rate ≥90% (max 10% failures)
- [ ] **AC5.4:** Total processing time ≤45 seconds P95 (baseline: 30s)
- [ ] **AC5.5:** LLM cost ≤$0.03 per repo (target: $0.025)
- [ ] **AC5.6:** No regressions in non-GitHub evidence sources (PDF, video, web links)

### Integration & Deployment

- [ ] **AC6.1:** Pre-production validation passes on 50+ diverse repos (Python, JS, Go, Rust, small/large)
- [ ] **AC6.2:** Canary deployment to 1 pod stable for 48 hours
- [ ] **AC6.3:** 25% pod deployment stable for 72 hours
- [ ] **AC6.4:** Full deployment (100%) runs 7 days without rollback
- [ ] **AC6.5:** Emergency rollback procedure documented and tested

### Data Quality

- [ ] **AC7.1:** Config file dependencies extracted with ≥95% accuracy (vs manual verification)
- [ ] **AC7.2:** Architecture pattern detection ≥80% accuracy (manual validation on 20 repos)
- [ ] **AC7.3:** CI/CD metrics extracted when present (test coverage, build status)
- [ ] **AC7.4:** Cross-source consistency score averages ≥0.75

---

## Design Changes

### API Changes

**Modified Endpoint:** `EvidenceContentExtractor.extract_github_content()`

**Before (Legacy):**
```python
async def extract_github_content(
    self,
    repo_url: str,
    repo_stats: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None
) -> ExtractedContent:
    # Load README + first 10 source files (fixed selection)
    documents = await document_loader._process_github_repository(repo_url)

    # Extract via LLM with limited context
    extraction_prompt = f"Analyze this repo: {readme[:3000]} + {code[:500 each]}"
    ...
```

**After (Agent-Based):**
```python
async def extract_github_content(
    self,
    repo_url: str,
    repo_stats: Optional[Dict[str, Any]] = None,
    user_id: Optional[int] = None
) -> ExtractedContent:
    """
    Agent-based GitHub repository analysis with intelligent file selection.

    Replaced legacy fixed-file approach in v1.3.0.

    Flow:
    1. Reconnaissance: Detect project type, language, structure
    2. File selection: LLM chooses 15-20 most relevant files (token-budget aware)
    3. Hybrid analysis: Multi-format parsing (config/source/infra/docs)
    4. Refinement: Optional iteration if confidence <0.75

    Args:
        repo_url: GitHub repository URL (https://github.com/owner/repo)
        repo_stats: Optional pre-fetched GitHub API metadata
        user_id: User ID for tracking and permissions

    Returns:
        ExtractedContent with:
            - technologies: List[str] with versions (e.g., ["React 18.2.0"])
            - achievements: List[str] with quantified metrics
            - description: Unified project summary
            - confidence: float (0-1) overall analysis quality
            - agent_analysis: Dict with phase results
    """
    agent = GitHubRepositoryAgent(
        client_manager=self.client_manager,
        document_loader=self.document_loader,
        performance_tracker=self.performance_tracker
    )

    return await agent.analyze_repository(
        repo_url=repo_url,
        user_id=user_id,
        token_budget=8000,
        repo_stats=repo_stats
    )
```

**Breaking Change:** Method signature unchanged, but behavior completely rewritten. No `use_agent` parameter.

### New Service: GitHubRepositoryAgent

**File:** `llm_services/services/core/github_repository_agent.py`

**Public Interface:**
```python
class GitHubRepositoryAgent(BaseLLMService):
    """
    Intelligent GitHub repository analysis with 4-phase adaptive processing.

    Phases:
    1. Reconnaissance: Project type, structure, languages
    2. File Selection: LLM-powered prioritization (token-budget aware)
    3. Hybrid Analysis: Multi-format parsing (config/source/infra/docs)
    4. Refinement: Optional iteration if confidence <0.75
    """

    async def analyze_repository(
        self,
        repo_url: str,
        user_id: int,
        token_budget: int = 8000,
        repo_stats: Optional[Dict] = None
    ) -> ExtractedContent:
        """Main entry point for agent analysis"""

    async def _phase1_reconnaissance(
        self,
        repo_url: str,
        repo_stats: Optional[Dict]
    ) -> RepoStructureAnalysis:
        """Fetch metadata and detect project characteristics"""

    async def _phase2_file_prioritization(
        self,
        structure: RepoStructureAnalysis,
        token_budget: int
    ) -> List[FileToLoad]:
        """LLM decides which files to load"""

    async def _phase3_hybrid_analysis(
        self,
        loaded_files: List[Document]
    ) -> HybridAnalysisResult:
        """Multi-format specialized parsing"""

    async def _phase4_refinement_check(
        self,
        current_analysis: HybridAnalysisResult,
        confidence_threshold: float = 0.75
    ) -> Optional[List[str]]:
        """Decide if more files needed"""
```

**Key Dataclasses:**
```python
@dataclass
class RepoStructureAnalysis:
    project_type: str  # 'web_app', 'library', 'cli_tool', 'framework'
    primary_language: str
    languages_breakdown: Dict[str, int]  # {language: percentage}
    directory_tree: Dict[str, Any]
    file_count_by_type: Dict[str, int]
    key_directories: List[str]
    stars: int
    forks: int
    contributors: int

@dataclass
class FileToLoad:
    path: str
    priority: str  # 'critical', 'high', 'medium', 'low'
    reason: str
    estimated_tokens: int

@dataclass
class HybridAnalysisResult:
    # Config analysis
    dependencies: Dict[str, str]  # {package: version}
    dev_dependencies: Dict[str, str]
    scripts: Dict[str, str]

    # Source analysis
    architecture_pattern: str
    api_endpoints: List[str]
    database_technologies: List[str]

    # Infrastructure analysis
    containerization: Dict[str, Any]
    ci_cd_setup: Dict[str, Any]
    deployment_targets: List[str]

    # Documentation analysis
    key_features: List[str]
    quantitative_metrics: List[str]
    project_vision: str

    # Quality
    consistency_score: float
    confidence: float
```

### New Service: HybridFileAnalyzer

**File:** `llm_services/services/core/hybrid_file_analyzer.py`

**Public Interface:**
```python
class HybridFileAnalyzer:
    """
    Multi-format file content parsing with specialized analyzers.

    Handles: JSON, YAML, TOML, source code, Markdown, Dockerfiles.
    """

    async def analyze_config_files(
        self,
        config_docs: List[Document]
    ) -> ConfigAnalysisResult:
        """Parse package.json, requirements.txt, Cargo.toml, etc."""

    async def analyze_source_code(
        self,
        source_docs: List[Document]
    ) -> SourceAnalysisResult:
        """LLM-powered pattern detection in source files"""

    async def analyze_infrastructure(
        self,
        infra_docs: List[Document]
    ) -> InfrastructureAnalysisResult:
        """Parse Dockerfile, CI/CD configs"""

    async def analyze_documentation(
        self,
        doc_docs: List[Document]
    ) -> DocumentationAnalysisResult:
        """LLM extracts features and metrics from docs"""

    async def synthesize_insights(
        self,
        config: ConfigAnalysisResult,
        source: SourceAnalysisResult,
        infra: InfrastructureAnalysisResult,
        docs: DocumentationAnalysisResult
    ) -> HybridAnalysisResult:
        """Cross-reference findings from all file types"""
```

### Database Migration

**File:** `llm_services/migrations/0XXX_add_github_repository_analysis.py`

```python
from django.db import migrations, models
import uuid

class Migration(migrations.Migration):
    dependencies = [
        ('llm_services', '0XXX_previous_migration'),
        ('artifacts', '0XXX_previous_migration'),
    ]

    operations = [
        # Create github_repository_analysis table
        migrations.CreateModel(
            name='GitHubRepositoryAnalysis',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4)),
                ('evidence', models.ForeignKey('artifacts.Evidence', on_delete=models.CASCADE)),
                ('repo_structure', models.JSONField(default=dict)),
                ('detected_project_type', models.CharField(max_length=50)),
                ('primary_language', models.CharField(max_length=50)),
                ('languages_breakdown', models.JSONField(default=dict)),
                ('files_loaded', models.JSONField(default=list)),
                ('total_tokens_used', models.IntegerField(default=0)),
                ('selection_reasoning', models.TextField(blank=True)),
                ('config_analysis', models.JSONField(default=dict)),
                ('source_analysis', models.JSONField(default=dict)),
                ('infrastructure_analysis', models.JSONField(default=dict)),
                ('documentation_analysis', models.JSONField(default=dict)),
                ('refinement_iterations', models.IntegerField(default=1)),
                ('additional_files_loaded', models.JSONField(default=list)),
                ('analysis_confidence', models.FloatField(default=0.0)),
                ('consistency_score', models.FloatField(default=0.0)),
                ('processing_time_ms', models.IntegerField(default=0)),
                ('llm_cost_usd', models.DecimalField(max_digits=10, decimal_places=6)),
                ('agent_version', models.CharField(max_length=20, default='v1.0')),
                ('feature_flag_sample_rate', models.FloatField(null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'db_table': 'github_repository_analysis'},
        ),

        # Add agent_analysis_id to extracted_content
        migrations.AddField(
            model_name='extractedcontent',
            name='agent_analysis',
            field=models.ForeignKey(
                'llm_services.GitHubRepositoryAnalysis',
                on_delete=models.SET_NULL,
                null=True,
                blank=True,
                related_name='extracted_contents'
            ),
        ),

        # Create indexes
        migrations.AddIndex(
            model_name='githubrepositoryanalysis',
            index=models.Index(fields=['evidence'], name='idx_github_repo_analysis_evidence'),
        ),
        migrations.AddIndex(
            model_name='githubrepositoryanalysis',
            index=models.Index(fields=['detected_project_type'], name='idx_github_repo_analysis_project_type'),
        ),
        migrations.AddIndex(
            model_name='githubrepositoryanalysis',
            index=models.Index(fields=['analysis_confidence'], name='idx_github_repo_analysis_confidence'),
        ),
    ]
```

---

## Test & Eval Plan

### Unit Tests

**File:** `llm_services/tests/unit/services/core/test_github_repository_agent.py`

```python
class TestGitHubRepositoryAgent:
    """Unit tests for each phase independently"""

    async def test_phase1_reconnaissance_detects_web_app(self):
        """Phase 1 correctly identifies web app project type"""
        agent = GitHubRepositoryAgent()
        structure = await agent._phase1_reconnaissance(
            "https://github.com/vercel/next.js",
            repo_stats=mock_nextjs_stats
        )
        assert structure.project_type == "web_app"
        assert structure.primary_language == "JavaScript"
        assert "TypeScript" in structure.languages_breakdown

    async def test_phase1_reconnaissance_detects_library(self):
        """Phase 1 correctly identifies library project type"""
        agent = GitHubRepositoryAgent()
        structure = await agent._phase1_reconnaissance(
            "https://github.com/django/django",
            repo_stats=mock_django_stats
        )
        assert structure.project_type == "library"
        assert structure.primary_language == "Python"

    async def test_phase2_prioritizes_config_files_first(self):
        """Phase 2 gives 'critical' priority to package.json"""
        agent = GitHubRepositoryAgent()
        files = await agent._phase2_file_prioritization(
            structure=mock_nextjs_structure,
            token_budget=8000
        )
        package_json = [f for f in files if f.path == "package.json"][0]
        assert package_json.priority == "critical"
        assert package_json.reason.lower().contains("dependencies")

    async def test_phase2_respects_token_budget(self):
        """Phase 2 stays within token budget"""
        agent = GitHubRepositoryAgent()
        files = await agent._phase2_file_prioritization(
            structure=mock_large_repo_structure,
            token_budget=5000
        )
        total_tokens = sum(f.estimated_tokens for f in files)
        assert total_tokens <= 5000

    async def test_phase2_excludes_vendor_files(self):
        """Phase 2 automatically excludes node_modules, vendor, generated"""
        agent = GitHubRepositoryAgent()
        files = await agent._phase2_file_prioritization(
            structure=mock_repo_with_vendor,
            token_budget=8000
        )
        paths = [f.path for f in files]
        assert not any("node_modules" in p for p in paths)
        assert not any("vendor" in p for p in paths)

    async def test_phase3_extracts_dependencies_with_versions(self):
        """Phase 3 config parser extracts package versions"""
        analyzer = HybridFileAnalyzer()
        config_result = await analyzer.analyze_config_files([
            Document(
                page_content='{"dependencies": {"react": "^18.2.0", "next": "14.0.0"}}',
                metadata={"file": "package.json", "source": "github"}
            )
        ])
        assert config_result.dependencies["react"] == "^18.2.0"
        assert config_result.dependencies["next"] == "14.0.0"

    async def test_phase3_detects_microservices_pattern(self):
        """Phase 3 source analyzer detects microservices architecture"""
        analyzer = HybridFileAnalyzer()
        source_result = await analyzer.analyze_source_code([
            Document(page_content=mock_microservices_code, metadata={"file": "services/user/main.go"})
        ])
        assert source_result.architecture_pattern == "microservices"

    async def test_phase3_parses_dockerfile(self):
        """Phase 3 infra analyzer extracts Dockerfile info"""
        analyzer = HybridFileAnalyzer()
        infra_result = await analyzer.analyze_infrastructure([
            Document(page_content="FROM node:18-alpine\nRUN npm install", metadata={"file": "Dockerfile"})
        ])
        assert "node:18-alpine" in infra_result.containerization["base_image"]

    async def test_phase3_extracts_ci_cd_workflows(self):
        """Phase 3 infra analyzer parses GitHub Actions"""
        analyzer = HybridFileAnalyzer()
        infra_result = await analyzer.analyze_infrastructure([
            Document(
                page_content=mock_github_actions_yaml,
                metadata={"file": ".github/workflows/test.yml"}
            )
        ])
        assert "pytest" in infra_result.ci_cd_setup["test_command"]
        assert infra_result.ci_cd_setup["coverage_enabled"] is True

    async def test_phase4_requests_refinement_when_low_confidence(self):
        """Phase 4 requests more files when confidence <0.75"""
        agent = GitHubRepositoryAgent()
        additional_files = await agent._phase4_refinement_check(
            current_analysis=mock_low_confidence_analysis,  # confidence=0.65
            confidence_threshold=0.75
        )
        assert additional_files is not None
        assert len(additional_files) >= 3  # Should request 3-5 files

    async def test_phase4_skips_refinement_when_high_confidence(self):
        """Phase 4 skips refinement when confidence ≥0.75"""
        agent = GitHubRepositoryAgent()
        additional_files = await agent._phase4_refinement_check(
            current_analysis=mock_high_confidence_analysis,  # confidence=0.85
            confidence_threshold=0.75
        )
        assert additional_files is None  # No refinement needed
```

**File:** `llm_services/tests/unit/services/core/test_hybrid_file_analyzer.py`

```python
class TestHybridFileAnalyzer:
    """Unit tests for multi-format parsing"""

    async def test_analyze_config_handles_requirements_txt(self):
        """Config analyzer parses requirements.txt"""
        analyzer = HybridFileAnalyzer()
        result = await analyzer.analyze_config_files([
            Document(page_content="django==4.2.0\ncelery>=5.3.0", metadata={"file": "requirements.txt"})
        ])
        assert result.dependencies["django"] == "==4.2.0"
        assert result.dependencies["celery"] == ">=5.3.0"

    async def test_analyze_config_handles_cargo_toml(self):
        """Config analyzer parses Cargo.toml"""
        analyzer = HybridFileAnalyzer()
        result = await analyzer.analyze_config_files([
            Document(
                page_content='[dependencies]\ntokio = "1.35.0"',
                metadata={"file": "Cargo.toml"}
            )
        ])
        assert result.dependencies["tokio"] == "1.35.0"

    async def test_synthesize_validates_consistency(self):
        """Synthesis calculates consistency score from cross-references"""
        analyzer = HybridFileAnalyzer()

        # Config says "react": "^18.0.0"
        config = ConfigAnalysisResult(dependencies={"react": "^18.0.0"})

        # Source code imports react
        source = SourceAnalysisResult(imports=["react"])

        # Docs mention "Built with React 18"
        docs = DocumentationAnalysisResult(technologies_mentioned=["React 18"])

        hybrid = await analyzer.synthesize_insights(config, source, {}, docs)

        # High consistency: all 3 sources agree on React
        assert hybrid.consistency_score >= 0.8
```

### Integration Tests

**File:** `llm_services/tests/integration/test_github_agent_flow.py`

```python
@pytest.mark.integration
class TestGitHubAgentFlowIntegration:
    """End-to-end tests with real GitHub repos (mocked LLM)"""

    async def test_end_to_end_nextjs_repo(self):
        """Complete flow for Next.js repository"""
        agent = GitHubRepositoryAgent()

        result = await agent.analyze_repository(
            repo_url="https://github.com/vercel/next.js",
            user_id=1,
            token_budget=8000
        )

        # Validate extracted data
        assert result.success is True
        assert "Next.js" in result.data["technologies"]
        assert "React" in result.data["technologies"]
        assert "TypeScript" in result.data["technologies"]
        assert result.confidence >= 0.75

        # Validate agent stored analysis
        assert result.data["agent_analysis"]["project_type"] == "framework"
        assert "package.json" in [f["path"] for f in result.data["agent_analysis"]["files_loaded"]]

    async def test_end_to_end_django_repo(self):
        """Complete flow for Django repository"""
        agent = GitHubRepositoryAgent()

        result = await agent.analyze_repository(
            repo_url="https://github.com/django/django",
            user_id=1,
            token_budget=8000
        )

        assert result.success is True
        assert "Python" in result.data["technologies"]
        assert "Django" in result.data["technologies"]
        assert result.confidence >= 0.80  # High confidence for well-documented repo

    async def test_handles_private_repo_gracefully(self):
        """Agent fails gracefully for inaccessible repos"""
        agent = GitHubRepositoryAgent()

        result = await agent.analyze_repository(
            repo_url="https://github.com/private/repo-404",
            user_id=1,
            token_budget=8000
        )

        assert result.success is False
        assert "not accessible" in result.error_message.lower()

    async def test_agent_vs_legacy_comparison(self):
        """Compare agent results with legacy approach"""
        # This test validates improvement over legacy
        repo_url = "https://github.com/pallets/flask"

        # Agent extraction
        agent = GitHubRepositoryAgent()
        agent_result = await agent.analyze_repository(repo_url, user_id=1)

        # Should extract MORE technologies (from setup.py)
        assert len(agent_result.data["technologies"]) >= 8  # Flask, Jinja2, Click, etc.

        # Should have HIGHER confidence
        assert agent_result.confidence >= 0.75

        # Should include config dependencies
        assert any("click" in t.lower() for t in agent_result.data["technologies"])
```

### Golden Test Cases

**50-Repo Validation Suite** (run before production deploy):

```python
GOLDEN_REPOS = [
    # Python Projects
    {
        "url": "https://github.com/django/django",
        "expected_project_type": "framework",
        "expected_technologies": ["Python", "Django", "SQLite", "PostgreSQL"],
        "expected_architecture": "framework",
        "min_confidence": 0.85,
        "min_tech_accuracy": 0.90
    },
    {
        "url": "https://github.com/pallets/flask",
        "expected_project_type": "framework",
        "expected_technologies": ["Python", "Flask", "Jinja2", "Click", "Werkzeug"],
        "expected_ci_cd": True,
        "min_confidence": 0.80
    },

    # JavaScript Projects
    {
        "url": "https://github.com/vercel/next.js",
        "expected_project_type": "framework",
        "expected_technologies": ["JavaScript", "TypeScript", "React", "Node.js", "Webpack"],
        "expected_features": ["Server-Side Rendering", "Static Generation"],
        "min_confidence": 0.85
    },
    {
        "url": "https://github.com/facebook/react",
        "expected_project_type": "library",
        "expected_technologies": ["JavaScript", "React", "JSX"],
        "min_confidence": 0.90
    },

    # Go Projects
    {
        "url": "https://github.com/kubernetes/kubernetes",
        "expected_project_type": "cli_tool",
        "expected_technologies": ["Go", "Docker", "etcd"],
        "expected_architecture": "microservices",
        "min_confidence": 0.75  # Large monorepo, harder to analyze
    },

    # Rust Projects
    {
        "url": "https://github.com/tokio-rs/tokio",
        "expected_project_type": "library",
        "expected_technologies": ["Rust", "async", "tokio"],
        "min_confidence": 0.80
    },

    # Edge Cases
    {
        "url": "https://github.com/torvalds/linux",
        "expected_project_type": "cli_tool",
        "expected_technologies": ["C", "Makefile"],
        "min_confidence": 0.65,  # Very large, complex structure
        "note": "Low confidence acceptable for kernel-level projects"
    },
    {
        "url": "https://github.com/Netflix/chaosmonkey",
        "expected_project_type": "cli_tool",
        "expected_technologies": ["Go", "AWS"],
        "expected_features": ["Chaos Engineering"],
        "min_confidence": 0.70
    },

    # Small Libraries
    {
        "url": "https://github.com/lodash/lodash",
        "expected_project_type": "library",
        "expected_technologies": ["JavaScript"],
        "min_confidence": 0.85
    },

    # ... add 41 more repos for comprehensive coverage
]

@pytest.mark.golden
class TestGoldenRepos:
    """Validation against 50-repo golden set"""

    @pytest.mark.parametrize("repo", GOLDEN_REPOS)
    async def test_golden_repo(self, repo):
        """Each repo must meet quality thresholds"""
        agent = GitHubRepositoryAgent()
        result = await agent.analyze_repository(
            repo_url=repo["url"],
            user_id=1,
            token_budget=8000
        )

        # Confidence check
        assert result.confidence >= repo["min_confidence"], \
            f"Confidence {result.confidence} below {repo['min_confidence']}"

        # Technology extraction accuracy
        expected_tech = set(repo["expected_technologies"])
        extracted_tech = set(result.data["technologies"])

        # Calculate accuracy (Jaccard similarity)
        intersection = expected_tech & extracted_tech
        union = expected_tech | extracted_tech
        accuracy = len(intersection) / len(union) if union else 0

        min_accuracy = repo.get("min_tech_accuracy", 0.85)
        assert accuracy >= min_accuracy, \
            f"Tech accuracy {accuracy:.0%} below {min_accuracy:.0%}"

        # Project type check
        if "expected_project_type" in repo:
            assert result.data["agent_analysis"]["project_type"] == repo["expected_project_type"]

        # CI/CD check
        if repo.get("expected_ci_cd"):
            assert result.data["agent_analysis"]["ci_cd_setup"], \
                "CI/CD setup not detected"
```

### AI Evaluation Thresholds

**Quantitative Metrics (Measured on Golden Set):**

| Metric | Baseline (Legacy) | Target (Agent) | Measured After Deploy |
|--------|------------------|----------------|----------------------|
| Technology extraction accuracy | 60% | **≥85%** | ___% |
| Enrichment confidence (avg) | 0.65 | **≥0.80** | ___ |
| Agent success rate | N/A | **≥90%** | ___% |
| Config file dependency detection | 0% | **≥95%** | ___% |
| Architecture pattern detection | 0% | **≥80%** | ___% |
| CI/CD metrics extraction | 0% | **≥70%** (when present) | ___% |
| Cross-source consistency score | N/A | **≥0.75** | ___ |

**Qualitative Metrics (User Feedback):**
- User satisfaction rating: 7/10 → **≥8.5/10**
- Technology completeness: "Missing key tech" complaints -60%
- Achievement relevance: User validation approval +30%

### Performance Benchmarks

**Latency Targets:**
- Phase 1 (Reconnaissance): ≤2 seconds P95
- Phase 2 (File Selection): ≤5 seconds P95
- Phase 3 (Hybrid Analysis): ≤20 seconds P95
- Phase 4 (Refinement): ≤10 seconds P95 (if triggered)
- **Total end-to-end:** ≤45 seconds P95

**Cost Targets:**
- Per-repo LLM cost: ≤$0.03 (target: $0.025)
- Token usage: ≤10K tokens/repo
- GitHub API calls: ≤5 calls/repo (within rate limits)

---

## Telemetry & Metrics

### Dashboards

**Grafana Dashboard: GitHub Agent Health**

**Panels:**
1. **Agent Success Rate** (7-day moving average)
   - Metric: `github_agent_success_rate`
   - Target: ≥90%
   - Alert: <85% for 10 minutes → P2

2. **Processing Latency** (percentiles)
   - Metrics: `github_agent_duration_p50`, `p95`, `p99`
   - Target: P95 ≤45s
   - Alert: P95 >60s for 15 minutes → P2

3. **Cost per Repository**
   - Metric: `github_agent_llm_cost_per_repo`
   - Target: ≤$0.03
   - Alert: >$0.05 for 1 hour → P1

4. **Technology Extraction Accuracy**
   - Metric: `github_agent_tech_accuracy` (manual validation sample)
   - Target: ≥85%
   - Alert: <80% for 24 hours → P2

5. **Confidence Distribution** (histogram)
   - Metric: `github_agent_confidence_histogram`
   - Target: Mean ≥0.80
   - Alert: Mean <0.75 for 6 hours → P2

6. **File Selection Quality**
   - Metrics: `github_agent_avg_files_loaded`, `github_agent_config_files_loaded`
   - Target: 15-20 files avg, ≥1 config file
   - Alert: <1 config file loaded for 1 hour → P3

7. **Phase Breakdown**
   - Metrics: `github_agent_phase1_duration`, `phase2_duration`, etc.
   - Identify bottlenecks

**Grafana Dashboard: Enrichment Quality Comparison**

**Panels:**
1. **Agent vs Legacy Quality** (side-by-side)
   - Metrics: `enrichment_confidence_agent` vs `enrichment_confidence_legacy`
   - Show improvement delta

2. **Failure Rate Trend**
   - Metric: `enrichment_failure_rate`
   - Baseline (legacy): 15%
   - Target (agent): ≤10%

3. **User Satisfaction Trend**
   - Metric: `enrichment_satisfaction_rating` (post-enrichment survey)
   - Baseline: 7/10
   - Target: ≥8.5/10

### Metrics to Track

**Agent Performance:**
```python
# Prometheus metrics
agent_success_rate = Gauge(
    'github_agent_success_rate',
    'Percentage of successful agent analyses',
    ['project_type']
)

agent_processing_duration = Histogram(
    'github_agent_processing_duration_seconds',
    'Total agent processing time',
    ['phase', 'project_type'],
    buckets=[5, 10, 20, 30, 45, 60, 90, 120]
)

agent_llm_cost = Histogram(
    'github_agent_llm_cost_usd',
    'LLM cost per repository analysis',
    ['project_type'],
    buckets=[0.01, 0.02, 0.03, 0.05, 0.10]
)

agent_files_loaded = Histogram(
    'github_agent_files_loaded_count',
    'Number of files loaded by agent',
    ['project_type'],
    buckets=[5, 10, 15, 20, 25, 30]
)

agent_confidence = Histogram(
    'github_agent_confidence_score',
    'Agent analysis confidence score',
    ['project_type'],
    buckets=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

agent_tech_extraction_count = Histogram(
    'github_agent_technologies_extracted_count',
    'Number of technologies extracted',
    ['project_type'],
    buckets=[0, 3, 5, 8, 10, 15, 20]
)

agent_phase_failure = Counter(
    'github_agent_phase_failure_total',
    'Total phase failures',
    ['phase', 'error_type']
)
```

**Quality Metrics:**
```python
tech_extraction_accuracy = Gauge(
    'github_agent_tech_extraction_accuracy',
    'Technology extraction accuracy (manual validation)',
    ['project_type']
)

config_file_detection_rate = Gauge(
    'github_agent_config_file_detection_rate',
    'Percentage of repos where config files were loaded',
    []
)

ci_cd_detection_rate = Gauge(
    'github_agent_ci_cd_detection_rate',
    'Percentage of repos with CI/CD detected',
    []
)

consistency_score = Histogram(
    'github_agent_consistency_score',
    'Cross-source consistency score',
    ['project_type'],
    buckets=[0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)
```

### Alert Thresholds

**P1 Alerts (Immediate Response):**
- Agent success rate <80% for 30 minutes
- LLM cost >$0.10/repo for 1 hour
- Any 5xx errors from agent code
- GitHub API error rate >10% for 10 minutes

**P2 Alerts (Next Business Day):**
- Agent success rate <85% for 2 hours
- Processing latency P95 >60s for 30 minutes
- Confidence avg <0.75 for 6 hours
- Technology extraction accuracy <80% for 24 hours

**P3 Alerts (Monitor):**
- Config file detection rate <80% for 24 hours
- Refinement iteration count avg >1.5 for 12 hours
- Token usage avg >12K/repo for 6 hours

---

## Edge Cases & Risks

### Edge Cases

**1. Very Large Monorepos (>10,000 files)**
- **Issue:** File listing timeout, token budget insufficient
- **Mitigation:**
  - Phase 1 limits directory depth to 3 levels
  - Phase 2 prioritizes key directories only (`/src`, `/app`, `/pkg`)
  - Timeout guard: 60 seconds max for Phase 1

**2. Private/Inaccessible Repositories**
- **Issue:** GitHub API returns 404/403
- **Mitigation:**
  - Immediate fail with clear error message: "Repository not accessible"
  - No retries (won't help with auth issues)
  - User-facing message: "Please make repository public or provide access token"

**3. Repositories with No Config Files**
- **Issue:** Pure C/Assembly projects with only Makefiles
- **Mitigation:**
  - Phase 3 handles missing config gracefully (empty `dependencies` dict)
  - Confidence score adjusted down (e.g., 0.65 instead of 0.80)
  - Still extracts useful info from README and source files

**4. Non-English Documentation**
- **Issue:** LLM struggles with Chinese/Japanese/Russian docs
- **Mitigation:**
  - GPT-5 handles multilingual content
  - If extraction fails, fall back to code analysis only
  - Confidence score reflects documentation quality

**5. Generated/Minified Code**
- **Issue:** `dist/bundle.min.js` is unintelligible
- **Mitigation:**
  - Phase 2 file filter excludes: `*.min.js`, `dist/`, `build/`, `__pycache__/`
  - Prioritizes source files over generated artifacts

**6. GitHub API Rate Limit Hit**
- **Issue:** 5,000 requests/hour exceeded
- **Mitigation:**
  - Exponential backoff: 2s, 4s, 8s delays
  - Max 3 retries
  - If still fails: Circuit breaker opens, all GitHub enrichments paused 5 minutes
  - Alert: P1 (immediate engineer response)

**7. LLM Returns Malformed JSON**
- **Issue:** GPT-5 doesn't follow JSON schema exactly
- **Mitigation:**
  - JSON schema validation with retry (up to 2 retries with corrected prompt)
  - If all retries fail: Log error, return partial data with low confidence (0.4)
  - Alert: P3 (monitor pattern)

**8. Conflicting Information Across Sources**
- **Issue:** package.json says "react": "^17.0.0" but docs say "React 18"
- **Mitigation:**
  - Phase 3 synthesis calculates consistency score (0-1)
  - If inconsistency detected (<0.6 score): Flag in metadata
  - Prefer config file data over docs (more authoritative)

**9. Extremely Long Files (>50K tokens)**
- **Issue:** Single file exceeds token budget
- **Mitigation:**
  - Truncate to first 5K tokens with warning
  - Agent notes: "File truncated due to length"
  - Still counts toward loaded file count

**10. Repository Deleted During Analysis**
- **Issue:** Repo exists at Phase 1, deleted by Phase 3
- **Mitigation:**
  - GitHub API returns 404 on file fetch
  - Agent marks as "Repository no longer accessible"
  - Fail gracefully with clear error message

### Risks

**Risk 1: Agent Complexity Leads to Maintenance Burden**
- **Likelihood:** Medium
- **Impact:** Medium
- **Mitigation:**
  - Comprehensive documentation + inline comments
  - Unit tests for each phase (>85% coverage)
  - Monitoring dashboards show phase-level bottlenecks

**Risk 2: LLM File Selection Misses Critical Files**
- **Likelihood:** Medium
- **Impact:** High
- **Mitigation:**
  - File type whitelist (always load package.json if present)
  - Post-deploy validation: Manual review of 20 random repo analyses
  - Iterate on file selection prompt based on failures

**Risk 3: Cost Explosion from Large Repos**
- **Likelihood:** Low
- **Impact:** High
- **Mitigation:**
  - Hard token budget limit: 8K tokens/repo
  - Per-repo timeout: 45 seconds max
  - Alert if cost >$0.05/repo (P1)

**Risk 4: GitHub API Changes Break Integration**
- **Likelihood:** Low
- **Impact:** High
- **Mitigation:**
  - Use stable GitHub API v3 (well-documented, backward-compatible)
  - Integration tests catch API contract changes
  - Monitor GitHub API deprecation notices

**Risk 5: Users Complain About Processing Time**
- **Likelihood:** Medium
- **Impact:** Low
- **Mitigation:**
  - Still within 5-minute P95 target (45s vs 30s)
  - Async processing (user doesn't wait)
  - Status polling shows "Analyzing repository..." message

**Risk 6: Quality Doesn't Improve as Expected**
- **Likelihood:** Low
- **Impact:** Critical
- **Mitigation:**
  - Pre-production validation on 50+ repos (must pass before deploy)
  - Canary deployment catches issues early (1 pod → 25% → 100%)
  - Rollback plan documented and tested

**Risk 7: Agent Fails Silently (No Error Reporting)**
- **Likelihood:** Medium
- **Impact:** High
- **Mitigation:**
  - Comprehensive error logging at each phase
  - Circuit breaker tracks failure patterns
  - Alert on error spike (>10% failure rate)

**Risk 8: Database Migration Fails in Production**
- **Likelihood:** Low
- **Impact:** Critical
- **Mitigation:**
  - Test migration in staging environment
  - Backup database before migration
  - Reversible migration (can roll back schema)

**Risk 9: Feature Creep (Phase 4, 5, 6...)**
- **Likelihood:** Medium
- **Impact:** Medium
- **Mitigation:**
  - Start with Phase 1-3 only (Phase 4 optional)
  - Mark Phase 4 as "experimental" initially
  - Only add Phase 5+ if Phase 1-4 proves successful

**Risk 10: No Fallback if Agent Fails**
- **Likelihood:** Low
- **Impact:** Critical
- **Mitigation:**
  - Pre-production testing reduces failure likelihood
  - Emergency rollback procedure (5-10 min code revert)
  - On-call engineer alerted on agent failure spike

---

## Deployment Plan

### Pre-Production Validation (Week 1-2)

**Local Development Testing:**
1. Run agent locally on 50+ diverse repos from golden set
2. Validate quality metrics meet thresholds:
   - Tech extraction accuracy ≥85%
   - Confidence avg ≥0.80
   - Success rate ≥90%
3. Fix critical bugs before staging deploy

**Golden Repo Checklist:**
```bash
# Run golden test suite
docker-compose exec backend uv run python manage.py test \
  llm_services.tests.integration.test_github_agent_flow::TestGoldenRepos \
  --keepdb --verbosity=2

# Validate results
# - All 50 repos must pass quality thresholds
# - No P1/P2 failures allowed
# - P3 failures reviewed case-by-case
```

### Staging Deployment (Week 3)

**Steps:**
1. Deploy to staging environment (isolated from production)
2. Run full enrichment test suite
3. Load test: 100 concurrent GitHub enrichments
4. Validate:
   - No database migration issues
   - Performance within targets (P95 ≤45s)
   - Cost within budget (≤$0.03/repo)
5. Fix any issues before production

**Staging Validation Checklist:**
- [ ] Database migration succeeds without errors
- [ ] Agent enriches 100 repos successfully (≥90% success rate)
- [ ] Load test: 100 concurrent enrichments complete within 5 minutes
- [ ] No memory leaks (monitor backend pod memory)
- [ ] No connection pool exhaustion
- [ ] Metrics dashboard shows accurate data

### Canary Production Deployment (Week 4)

**Day 1-2: Single Pod Canary**
```bash
# Deploy agent to 1 backend pod only
kubectl set image deployment/backend-canary backend=cv-tailor-backend:v1.3.0
kubectl scale deployment/backend-canary --replicas=1

# Monitor metrics 24/7
watch -n 60 'kubectl logs -l app=backend-canary --tail=100 | grep -i "github.*agent"'
```

**Canary Success Criteria (48 hours):**
- Agent success rate ≥85%
- No P1 alerts triggered
- User complaints = 0
- Cost per repo ≤$0.04 (allow 60% buffer)

**Day 3-5: 25% Rollout**
```bash
# Scale to 25% of backend pods (e.g., 3 out of 12 pods)
kubectl scale deployment/backend-canary --replicas=3
```

**25% Success Criteria (72 hours):**
- Agent success rate ≥90%
- Processing latency P95 ≤50s (allow 10% buffer)
- User satisfaction ≥8/10 (post-enrichment survey)

**Day 6-7: 100% Rollout**
```bash
# Update main backend deployment
kubectl set image deployment/backend backend=cv-tailor-backend:v1.3.0
kubectl rollout status deployment/backend
```

**Full Rollout Success Criteria (7 days):**
- All acceptance criteria met (see AC section above)
- No rollback needed
- Mark as stable

### Rollback Procedure

**Immediate Rollback (If P1 Alert):**
```bash
# 1. Identify failing commit
git log --oneline backend/llm_services/services/core/ | head -5

# 2. Create revert branch
git checkout main
git checkout -b emergency/revert-github-agent-$(date +%Y%m%d)
git revert <agent-commit-sha>

# 3. Emergency PR
gh pr create \
  --title "[EMERGENCY] Revert GitHub agent - $(date)" \
  --body "Reverting due to: <P1 alert reason>\n\nAlert: <link>" \
  --base main \
  --label emergency

# 4. Merge immediately (bypass review if critical)
gh pr merge --auto --squash --delete-branch

# 5. Deploy rollback
kubectl set image deployment/backend backend=cv-tailor-backend:v1.2.2-pre-agent
kubectl rollout status deployment/backend

# 6. Monitor for 30 minutes
watch -n 60 'kubectl logs -l app=backend --tail=100 | grep -i enrichment'
```

**Estimated Rollback Time:** 5-10 minutes

---

## Success Metrics

**Must-Pass Criteria (30 days after 100% rollout):**

| Metric | Baseline | Target | Actual |
|--------|----------|--------|--------|
| Technology extraction accuracy | 60% | ≥85% | ___% |
| Enrichment confidence (avg) | 0.65 | ≥0.80 | ___ |
| Enrichment failure rate | 15% | ≤10% | ___% |
| Agent success rate | N/A | ≥90% | ___% |
| Processing latency P95 | 30s | ≤50s | ___s |
| LLM cost per repo | $0.015 | ≤$0.03 | $____ |
| User satisfaction | 7/10 | ≥8.5/10 | ___/10 |
| Upload abandonment rate | 12% | ≤8% | ___% |

**If targets not met after 60 days:** Initiate rollback + retrospective

---

## Links

**Upstream Artifacts:**
- **PRD:** `docs/prds/prd.md` (v1.3.0)
- **TECH-SPECs:**
  - `docs/specs/spec-artifact-upload-enrichment-flow.md` (v1.3.0)
  - `docs/specs/spec-llm.md` (v3.1.0)
- **ADR:** `docs/adrs/adr-023-agent-style-github-traversal.md`
- **Discovery:** `docs/discovery/ft-013-github-agent-codebase-discovery.md`

**Related Features:**
- `ft-005-multi-source-artifact-preprocessing.md` (multi-source enrichment)
- `ft-012-gpt5-model-migration.md` (LLM model upgrade)

**Code References:**
- Current implementation: `llm_services/services/core/evidence_content_extractor.py:107`
- Reusable base: `llm_services/services/base/base_service.py`
- Document loading: `llm_services/services/core/document_loader_service.py:288-338`

---

**Last Updated:** 2025-10-06
**Next Review:** After CHECKPOINT #2 (Design Complete)
**Status:** Ready for implementation approval
