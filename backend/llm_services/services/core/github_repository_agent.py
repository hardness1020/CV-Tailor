"""
GitHubRepositoryAgent - Intelligent GitHub repository analysis using 4-phase agent architecture.
Implements ft-013-github-agent-traversal.md (v1.3.0)

Replaces legacy fixed-file extraction with adaptive, LLM-powered file selection.

4-Phase Architecture:
- Phase 1: Reconnaissance (GitHub API metadata, project type detection, language breakdown)
- Phase 2: File Prioritization (LLM selects 15-20 files, token-budget aware)
- Phase 3: Hybrid Analysis (Config/source/infra/docs parsing via HybridFileAnalyzer)
- Phase 4: Refinement (Optional iteration if confidence <0.75, max 2 iterations)

Performance targets:
- Processing time: <45 seconds/repo
- Cost: <$0.025/repo
- Token budget: 8K tokens/repo
- Quality: 85%+ technology accuracy, 0.82+ confidence
"""

import json
import re
import time
import logging
import asyncio
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict
from langchain.schema import Document
from decimal import Decimal

from ..base.base_service import BaseLLMService
from ..infrastructure.simple_llm_executor import SimpleLLMExecutor
from .hybrid_file_analyzer import HybridFileAnalyzer
from .document_loader_service import DocumentLoaderService

logger = logging.getLogger(__name__)


# GitHub Repository Agent Configuration
# Budget: $0.50/repo (20x increase from $0.025)
# Target: 13.5% code coverage (18x improvement from 0.75%)

# Phase 2: File Prioritization
PHASE2_MODEL = 'gpt-5-mini'  # Pattern matching task, cost-optimized
PHASE2_MAX_TOKENS = 10000     # Detailed file selection reasoning
PHASE2_MAX_FILES_CONSIDERED = 500  # Increased from 100

# Phase 3a: Source Code Analysis (handled by HybridFileAnalyzer)
# See hybrid_file_analyzer.py for source analysis config

# Phase 3b: Documentation Analysis (handled by HybridFileAnalyzer)
# See hybrid_file_analyzer.py for docs analysis config

# Expected costs per phase
PHASE2_COST_ESTIMATE = 0.0033   # GPT-5-mini
PHASE3A_COST_ESTIMATE = 0.088   # GPT-5, 20 files (in HybridFileAnalyzer)
PHASE3B_COST_ESTIMATE = 0.103   # GPT-5, 12 docs (in HybridFileAnalyzer)
TOTAL_COST_ESTIMATE = 0.202     # Well under $0.50 budget


# Data classes for agent state
@dataclass
class RepoStructureAnalysis:
    """Phase 1: Reconnaissance results"""
    repo_structure: Dict = field(default_factory=dict)
    detected_project_type: str = ""
    primary_language: str = ""
    languages_breakdown: Dict[str, int] = field(default_factory=dict)
    api_accessible: bool = True
    total_files: int = 0
    # Error tracking fields
    error_code: Optional[int] = None  # HTTP status code (401, 403, 404, 429)
    error_message: str = ""  # Detailed error message
    rate_limit_remaining: Optional[int] = None  # GitHub API rate limit remaining
    rate_limit_reset: Optional[int] = None  # Unix timestamp when rate limit resets


@dataclass
class FileToLoad:
    """Phase 2: File selection results"""
    path: str
    priority: str  # high, medium, low
    selection_reason: str
    estimated_tokens: int


class GitHubRepositoryAgent(BaseLLMService):
    """
    Intelligent GitHub repository analyzer using adaptive 4-phase agent architecture.

    Replaces legacy fixed-file extraction with LLM-powered intelligent file selection.
    Implements ft-013-github-agent-traversal.md (v1.3.0).

    **4-Phase Architecture:**

    1. **Reconnaissance** (Phase 1):
       - Fetch repository metadata via GitHub API
       - Detect project type (Python/Django, Node/React, Rust, Go, etc.)
       - Analyze language breakdown and repository structure
       - Determine if repo is accessible (404/403 handling)

    2. **File Prioritization** (Phase 2):
       - Use LLM (GPT-5) to select 15-20 most informative files
       - Token-budget aware (default: 8K tokens/repo)
       - Prioritize config, main source files, docs
       - Avoid noise (tests, vendor, build artifacts)

    3. **Hybrid Analysis** (Phase 3):
       - Parse selected files using HybridFileAnalyzer
       - Extract technologies, patterns, infrastructure
       - Cross-reference findings for consistency

       - Phase 3a: Source code analysis (GPT-5, 20 files, 10K tokens)
       - Phase 3b: Documentation analysis (GPT-5, 12 docs, 10K tokens)

    4. **Refinement** (Phase 4):
       - Check if confidence < threshold (default: 0.75)
       - Optionally iterate once more with additional files
       - Max 2 iterations to prevent runaway costs

    **Performance Targets:**
    - Processing time: <45 seconds/repo
    - Cost: <$0.025/repo
    - Token budget: 8K tokens/repo
    - Quality: 85%+ technology accuracy, 0.82+ confidence

    Attributes:
        llm_executor (SimpleLLMExecutor): Lightweight LLM executor for file selection
        hybrid_analyzer (HybridFileAnalyzer): Multi-format file parser
        doc_loader (DocumentLoaderService): GitHub file loading service
        excluded_patterns (List[str]): Paths to exclude (node_modules, .git, etc.)

    Examples:
        >>> agent = GitHubRepositoryAgent()
        >>> result = await agent.analyze_repository(
        ...     repo_url="https://github.com/user/repo",
        ...     user_id=123,
        ...     token_budget=8000
        ... )
        >>> print(result.data['technologies'])
        ['Python', 'Django', 'PostgreSQL', 'Docker']
        >>> print(result.confidence)
        0.89
    """

    def __init__(self):
        """
        Initialize the GitHubRepositoryAgent with all required services.

        Sets up:
        - SimpleLLMExecutor for LLM-powered file selection (with client_manager)
        - HybridFileAnalyzer for multi-format parsing
        - DocumentLoaderService for GitHub file loading
        - Excluded path patterns (node_modules, build dirs, etc.)
        """
        super().__init__()
        self.llm_executor = SimpleLLMExecutor(client_manager=self.client_manager)
        self.hybrid_analyzer = HybridFileAnalyzer()
        self.doc_loader = DocumentLoaderService()

        # Excluded paths (never load these)
        self.excluded_patterns = [
            'node_modules/', '.git/', '__pycache__/', 'venv/', 'env/',
            'dist/', 'build/', '.next/', 'target/', 'vendor/'
        ]

    async def analyze_repository(
        self,
        repo_url: str,
        user_id: int,
        token_budget: int = 8000,
        repo_stats: Optional[Dict] = None
    ):
        """
        Execute complete 4-phase agent analysis on a GitHub repository.

        This is the main entry point that orchestrates all 4 phases:
        1. Reconnaissance → metadata, project type, language breakdown
        2. File Prioritization → LLM selects 15-20 files
        3. Hybrid Analysis → multi-format parsing
        4. Refinement → optional iteration if confidence < 0.75

        Args:
            repo_url (str): Full GitHub repository URL (e.g., "https://github.com/user/repo")
            user_id (int): User ID for tracking and cost attribution
            token_budget (int, optional): Maximum tokens to use. Defaults to 8000.
            repo_stats (Dict, optional): Pre-fetched GitHub API stats. If None, will fetch.

        Returns:
            ExtractedContent: Analysis results containing:
                - source_type (str): Always "github"
                - source_url (str): Repository URL
                - success (bool): True if analysis succeeded
                - data (Dict): Extracted information with keys:
                    - technologies (List[str]): All detected technologies
                    - metrics (List[Dict]): Repository metrics (stars, forks, commits)
                    - summary (str): Project description
                    - project_type (str): Detected project type
                    - patterns (List[str]): Design patterns detected
                    - infrastructure (Dict): Infrastructure analysis
                    - tokens_used (int): Total tokens consumed
                    - files_analyzed (int): Number of files analyzed
                    - refinement_iterations (int): 1 or 2
                - confidence (float): 0.0-1.0 confidence score
                - processing_cost (float): Estimated cost in USD

        Raises:
            TimeoutError: If analysis exceeds time limit
            GitHubAPIError: If GitHub API fails
            OpenAIError: If LLM API calls fail

        Examples:
            >>> agent = GitHubRepositoryAgent()
            >>> result = await agent.analyze_repository(
            ...     repo_url="https://github.com/django/django",
            ...     user_id=123,
            ...     token_budget=10000
            ... )
            >>> print(f"Confidence: {result.confidence:.2f}")
            Confidence: 0.92
            >>> print(f"Technologies: {result.data['technologies']}")
            Technologies: ['Python', 'Django', 'PostgreSQL', 'SQLite']
            >>> print(f"Cost: ${result.processing_cost:.4f}")
            Cost: $0.0180

        Note:
            Requires GITHUB_TOKEN and OPENAI_API_KEY environment variables.
        """
        from .evidence_content_extractor import ExtractedContent

        start_time = time.time()
        total_cost = 0.0
        total_tokens = 0

        try:
            # Phase 1: Reconnaissance
            logger.info(f"[Phase 1] Reconnaissance: {repo_url}")
            structure = await self._phase1_reconnaissance(repo_url, repo_stats)

            if not structure.api_accessible:
                # Log detailed error from Phase 1
                error_details = structure.error_message or 'GitHub API not accessible'
                logger.error(
                    f"[GitHub Agent] Extraction failed for {repo_url}: {error_details} "
                    f"(HTTP {structure.error_code})"
                )

                # Include rate limit info if available
                data = {'error': error_details}
                if structure.rate_limit_remaining is not None:
                    data['rate_limit_remaining'] = structure.rate_limit_remaining
                    data['rate_limit_reset'] = structure.rate_limit_reset

                return ExtractedContent(
                    source_type='github',
                    source_url=repo_url,
                    success=False,
                    data=data,
                    confidence=0.0,
                    error_message=error_details
                )

            # Phase 2: File Prioritization
            logger.info(f"[Phase 2] File Prioritization (budget: {token_budget} tokens)")
            files_to_load = await self._phase2_file_prioritization(structure, token_budget)
            total_tokens += 200  # Approximate LLM call for file selection

            # Load selected files
            loaded_docs = await self._load_files_from_github(repo_url, files_to_load)

            # Phase 3: Hybrid Analysis
            logger.info(f"[Phase 3] Hybrid Analysis ({len(loaded_docs)} files loaded)")

            # Warn if no documentation files loaded
            doc_files = [d for d in loaded_docs if d.metadata.get('file_type') == 'documentation']
            if not doc_files:
                logger.warning(
                    f"[Phase 3] No documentation files loaded for {repo_url}. "
                    f"This may result in empty project summary. "
                    f"Files loaded: {[d.metadata.get('path', 'unknown') for d in loaded_docs[:10]]}"
                )
            else:
                logger.info(f"[Phase 3] Found {len(doc_files)} documentation files")

            hybrid_result = await self._phase3_hybrid_analysis(loaded_docs)
            total_tokens += 500  # Approximate tokens for hybrid analysis

            # Phase 4: Refinement Check
            logger.info(f"[Phase 4] Refinement Check (confidence: {hybrid_result.confidence:.2f})")
            additional_files = await self._phase4_refinement_check(
                hybrid_result,
                confidence_threshold=0.75
            )

            # If refinement needed, iterate once more
            if additional_files and len(additional_files) > 0:
                logger.info(f"[Phase 4] Refinement: loading {len(additional_files)} more files")
                more_docs = await self._load_files_from_github(repo_url, additional_files)
                loaded_docs.extend(more_docs)

                # Re-run hybrid analysis with additional files
                hybrid_result = await self._phase3_hybrid_analysis(loaded_docs)
                hybrid_result.refinement_iterations = 2

            # Calculate final metrics
            elapsed_ms = int((time.time() - start_time) * 1000)
            total_cost = self._estimate_cost(total_tokens)

            # Extract technologies from all analysis phases
            technologies = self._extract_all_technologies(hybrid_result, structure)

            # Build final result - Multi-source summary with fallback
            summary = hybrid_result.documentation_analysis.get('project_summary', '')

            # Fallback to GitHub repository description if summary is empty
            if not summary and repo_stats:
                github_description = repo_stats.get('description', '').strip()
                if github_description:
                    summary = github_description
                    logger.info(f"[GitHub Agent] Using GitHub repo description as fallback: '{summary[:100]}...'")
                else:
                    summary = "No description available"
                    logger.warning(f"[GitHub Agent] No summary available from any source for {repo_url}")
            elif summary:
                # Log successful summary generation with source tracking
                summary_source = hybrid_result.documentation_analysis.get('summary_source', 'unknown')
                logger.info(f"[GitHub Agent] Summary generated from {summary_source}: {len(summary)} chars")
            else:
                summary = "No description available"
                logger.warning(f"[GitHub Agent] Empty summary for {repo_url}")

            # ft-030: Aggregate source attribution metrics
            attribution_metrics = self._aggregate_attribution_metrics(hybrid_result)

            data = {
                'technologies': technologies,
                'metrics': self._build_metrics(repo_stats or {}),
                'achievements': hybrid_result.documentation_analysis.get('achievements', []),
                'summary': summary,
                'project_type': structure.detected_project_type,
                'patterns': hybrid_result.source_analysis.get('patterns', []),
                'infrastructure': hybrid_result.infrastructure_analysis,
                'tokens_used': total_tokens,
                'files_analyzed': len(loaded_docs),
                'refinement_iterations': hybrid_result.refinement_iterations,
                # ft-030: Source attribution quality metrics
                'attribution_coverage': attribution_metrics['overall_coverage'],
                'inferred_item_ratio': attribution_metrics['overall_inferred_ratio'],
                'documentation_attribution': attribution_metrics['documentation'],
                'code_attribution': attribution_metrics['code']
            }

            return ExtractedContent(
                source_type='github',
                source_url=repo_url,
                success=True,
                data=data,
                confidence=hybrid_result.confidence,
                processing_cost=total_cost
            )

        except TimeoutError as e:
            logger.error(f"Agent timeout: {e}")
            return ExtractedContent(
                source_type='github',
                source_url=repo_url,
                success=False,
                data={'error': 'Analysis timed out'},
                confidence=0.0,
                error_message=str(e)
            )
        except Exception as e:
            logger.error(
                f"[GitHub Agent] Analysis failed for {repo_url}: {e}. "
                f"This may be due to API failures, timeout, or parsing errors.",
                exc_info=True
            )
            return ExtractedContent(
                source_type='github',
                source_url=repo_url,
                success=False,
                data={'error': str(e)},
                confidence=0.0,
                error_message=str(e)
            )

    def _parse_github_error_response(self, response: requests.Response, repo_url: str) -> Tuple[str, Optional[int], Optional[int]]:
        """
        Parse GitHub API error response and extract actionable error information.

        Args:
            response: HTTP response from GitHub API
            repo_url: Repository URL for error context

        Returns:
            Tuple of (error_message, rate_limit_remaining, rate_limit_reset)
        """
        status_code = response.status_code

        # Extract rate limit info from headers
        rate_limit_remaining = None
        rate_limit_reset = None
        if 'X-RateLimit-Remaining' in response.headers:
            try:
                rate_limit_remaining = int(response.headers['X-RateLimit-Remaining'])
                rate_limit_reset = int(response.headers.get('X-RateLimit-Reset', 0))
            except (ValueError, TypeError):
                pass

        # Build detailed error message
        if status_code == 401:
            error_msg = f"GitHub API authentication failed for {repo_url}. Check GITHUB_TOKEN environment variable."
        elif status_code == 403:
            if rate_limit_remaining == 0:
                # Rate limit exceeded
                import datetime
                reset_time = datetime.datetime.fromtimestamp(rate_limit_reset) if rate_limit_reset else "unknown"
                error_msg = f"GitHub API rate limit exceeded for {repo_url}. Resets at {reset_time}. Configure GITHUB_TOKEN for higher limits."
            else:
                error_msg = f"GitHub API access forbidden for {repo_url}. Repository may be private or inaccessible."
        elif status_code == 404:
            error_msg = f"GitHub repository not found: {repo_url}. Repository may be private, deleted, or URL is incorrect."
        elif status_code == 429:
            error_msg = f"GitHub API rate limit exceeded (429) for {repo_url}. Retry later."
        else:
            # Try to parse JSON error response
            try:
                error_data = response.json()
                api_message = error_data.get('message', 'Unknown error')
                error_msg = f"GitHub API error ({status_code}) for {repo_url}: {api_message}"
            except (ValueError, KeyError):
                error_msg = f"GitHub API error ({status_code}) for {repo_url}: {response.text[:200]}"

        return error_msg, rate_limit_remaining, rate_limit_reset

    async def _phase1_reconnaissance(
        self,
        repo_url: str,
        repo_stats: Optional[Dict]
    ) -> RepoStructureAnalysis:
        """
        Phase 1: Reconnaissance - Fetch metadata and detect project characteristics.

        Uses GitHub API to get:
        - Repository file structure (tree)
        - Language breakdown
        - Project type detection (framework/library/application/tool)

        Args:
            repo_url: GitHub repository URL
            repo_stats: Optional pre-fetched stats from DocumentLoaderService

        Returns:
            RepoStructureAnalysis with metadata
        """
        # Extract owner/repo from URL
        match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            error_msg = f"Invalid GitHub repository URL format: {repo_url}"
            logger.error(f"[Phase 1] {error_msg}")
            return RepoStructureAnalysis(
                api_accessible=False,
                error_code=400,
                error_message=error_msg
            )

        owner, repo = match.groups()
        repo = repo.replace('.git', '')

        # Fetch repo stats if not provided
        if not repo_stats:
            try:
                repo_stats = await self.doc_loader.get_github_repo_stats(repo_url)
            except Exception as e:
                error_msg = f"Failed to fetch GitHub repository metadata: {str(e)}"
                logger.error(f"[Phase 1] {error_msg} for {repo_url}")
                return RepoStructureAnalysis(
                    api_accessible=False,
                    error_code=500,
                    error_message=error_msg
                )

        # Fetch repository tree structure
        try:
            tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1"
            response = requests.get(tree_url, timeout=10)

            if response.status_code == 404:
                # Try 'master' branch
                tree_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1"
                response = requests.get(tree_url, timeout=10)

            if response.status_code != 200:
                # Parse error response and extract actionable information
                error_msg, rate_limit_remaining, rate_limit_reset = self._parse_github_error_response(response, repo_url)
                logger.error(f"[Phase 1] GitHub API request failed: {error_msg}")

                return RepoStructureAnalysis(
                    api_accessible=False,
                    error_code=response.status_code,
                    error_message=error_msg,
                    rate_limit_remaining=rate_limit_remaining,
                    rate_limit_reset=rate_limit_reset
                )

            tree_data = response.json()

            # Filter files (exclude directories and excluded patterns)
            files = []
            for item in tree_data.get('tree', []):
                if item['type'] == 'blob':
                    path = item['path']
                    # Skip excluded patterns
                    if not any(exc in path for exc in self.excluded_patterns):
                        files.append({
                            'path': path,
                            'size': item.get('size', 0),
                            'type': self._categorize_file(path)
                        })

            # Detect project type from file structure
            project_type = self._detect_project_type(files, repo_stats)

            # Extract primary language
            languages = repo_stats.get('languages', {})
            primary_language = max(languages.items(), key=lambda x: x[1])[0] if languages else "Unknown"

            return RepoStructureAnalysis(
                repo_structure={'files': files},
                detected_project_type=project_type,
                primary_language=primary_language,
                languages_breakdown=languages,
                api_accessible=True,
                total_files=len(files)
            )

        except Exception as e:
            error_msg = f"Phase 1 reconnaissance failed with unexpected error: {str(e)}"
            logger.error(f"[Phase 1] {error_msg} for {repo_url}", exc_info=True)
            return RepoStructureAnalysis(
                api_accessible=False,
                error_code=500,
                error_message=error_msg
            )

    def _categorize_file(self, path: str) -> str:
        """Categorize file by type (config, source, infra, doc)"""
        if any(path.endswith(ext) for ext in ['.json', '.toml', '.yml', '.yaml', '.txt', '.ini']):
            if any(name in path.lower() for name in ['package.json', 'cargo.toml', 'go.mod', 'requirements', 'pyproject']):
                return 'config'
            elif any(name in path for name in ['docker', 'kubernetes', '.github', '.circleci']):
                return 'infrastructure'
            else:
                return 'config'
        elif any(path.endswith(ext) for ext in ['.md', '.rst', '.adoc']):
            return 'documentation'
        elif any(path.endswith(ext) for ext in ['.py', '.js', '.ts', '.rs', '.go', '.java', '.rb', '.php']):
            return 'source'
        else:
            return 'other'

    def _detect_project_type(self, files: List[Dict], repo_stats: Dict) -> str:
        """Detect project type from file structure and description"""
        file_paths = [f['path'].lower() for f in files]
        description = (repo_stats.get('description') or '').lower()

        # Framework indicators
        if any('framework' in p or 'core' in p for p in file_paths[:20]):
            return 'framework'

        # Library indicators
        if any('lib' in p or 'library' in p for p in file_paths[:20]):
            return 'library'

        # CLI tool indicators
        if any('cli' in p or 'cmd' in p for p in file_paths):
            return 'tool'

        # Platform indicators
        if 'kubernetes' in description or 'k8s' in description:
            return 'platform'

        # Default: application
        return 'application'

    async def _phase2_file_prioritization(
        self,
        structure: RepoStructureAnalysis,
        token_budget: int
    ) -> List[FileToLoad]:
        """
        Phase 2: File Prioritization - LLM selects which files to load.

        Uses GPT-5 to intelligently select 15-20 files that maximize information gain
        while staying within token budget.

        Args:
            structure: RepoStructureAnalysis from Phase 1
            token_budget: Maximum tokens to use

        Returns:
            List of FileToLoad objects
        """
        files = structure.repo_structure.get('files', [])

        # Prioritize config files first (always load)
        config_files = [f for f in files if f['type'] == 'config'][:5]

        # Build LLM prompt for file selection
        file_summary = []
        for f in files[:PHASE2_MAX_FILES_CONSIDERED]:  # Consider first 500 files (increased from 100)
            file_summary.append({
                'path': f['path'],
                'type': f['type'],
                'size': f.get('size', 0)
            })

        prompt = f"""You are analyzing a {structure.detected_project_type} project written primarily in {structure.primary_language}.

Select 15-20 files to analyze to maximize understanding of:
1. Technology stack (dependencies, frameworks)
2. Architecture patterns
3. Infrastructure setup

Repository has {len(files)} total files. Here are the first {min(len(files), PHASE2_MAX_FILES_CONSIDERED)} files:
{json.dumps(file_summary, indent=2)}

Token budget: {token_budget} tokens
Priority: Config files > Entry points > Core modules > Tests

Return JSON with:
{{
    "selected_files": [
        {{"path": "file.ext", "priority": "high|medium|low", "reason": "why selected"}},
        ...
    ],
    "estimated_tokens": 7500,
    "reasoning": "Overall selection strategy"
}}

Select files that give maximum signal, minimize noise. Avoid duplicates and test files unless critical.
"""
        try:
            response = await self.llm_executor.execute(
                prompt=prompt,
                model_name=PHASE2_MODEL,  # GPT-5-mini for pattern matching (cost-optimized)
                max_tokens=PHASE2_MAX_TOKENS,  # 2000 for detailed reasoning
                temperature=0.3
            )

            data = json.loads(response['content'])
            selected = data.get('selected_files', [])

            # Convert to FileToLoad objects
            files_to_load = []
            for item in selected[:20]:  # Max 20 files
                files_to_load.append(FileToLoad(
                    path=item['path'],
                    priority=item.get('priority', 'medium'),
                    selection_reason=item.get('reason', ''),
                    estimated_tokens=400  # Rough estimate per file
                ))

            return files_to_load

        except Exception as e:
            logger.error(f"Phase 2 file prioritization failed: {e}")
            # Fallback: select first 5 config files + README
            fallback_files = []
            for f in config_files:
                fallback_files.append(FileToLoad(
                    path=f['path'],
                    priority='high',
                    selection_reason='Config file',
                    estimated_tokens=400
                ))

            # Add README if exists
            readme_files = [f for f in files if 'readme' in f['path'].lower()]
            if readme_files:
                fallback_files.append(FileToLoad(
                    path=readme_files[0]['path'],
                    priority='medium',
                    selection_reason='Documentation',
                    estimated_tokens=600
                ))

            return fallback_files[:10]

    async def _load_files_from_github(
        self,
        repo_url: str,
        files_to_load: List[FileToLoad]
    ) -> List[Document]:
        """
        Load file contents from GitHub repository.

        Args:
            repo_url: GitHub repository URL
            files_to_load: List of FileToLoad objects

        Returns:
            List of Document objects with file contents
        """
        # Extract owner/repo
        match = re.search(r'github\.com/([^/]+)/([^/]+)', repo_url)
        if not match:
            return []

        owner, repo = match.groups()
        repo = repo.replace('.git', '')

        documents = []

        for file_info in files_to_load:
            try:
                # Fetch file content from GitHub API
                file_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{file_info.path}"
                response = requests.get(file_url, timeout=10)

                if response.status_code == 404:
                    # Try master branch
                    file_url = f"https://raw.githubusercontent.com/{owner}/{repo}/master/{file_info.path}"
                    response = requests.get(file_url, timeout=10)

                if response.status_code == 200:
                    content = response.text
                    documents.append(Document(
                        page_content=content,
                        metadata={
                            'path': file_info.path,
                            'file_type': self._categorize_file(file_info.path),
                            'priority': file_info.priority,
                            'selection_reason': file_info.selection_reason
                        }
                    ))
                else:
                    logger.warning(f"Failed to load file {file_info.path}: HTTP {response.status_code}")

            except Exception as e:
                logger.warning(f"Error loading file {file_info.path}: {e}")

        return documents

    async def _phase3_hybrid_analysis(
        self,
        loaded_docs: List[Document]
    ):
        """
        Phase 3: Hybrid Analysis - Analyze all file types using HybridFileAnalyzer.

        Args:
            loaded_docs: List of Document objects

        Returns:
            HybridAnalysisResult
        """
        # Categorize documents by type
        config_docs = [d for d in loaded_docs if d.metadata.get('file_type') == 'config']
        source_docs = [d for d in loaded_docs if d.metadata.get('file_type') == 'source']
        infra_docs = [d for d in loaded_docs if d.metadata.get('file_type') == 'infrastructure']
        doc_docs = [d for d in loaded_docs if d.metadata.get('file_type') == 'documentation']

        # Analyze each type
        config_analysis = await self.hybrid_analyzer.analyze_config_files(config_docs)
        source_analysis = await self.hybrid_analyzer.analyze_source_code(source_docs)
        infra_analysis = await self.hybrid_analyzer.analyze_infrastructure(infra_docs)
        docs_analysis = await self.hybrid_analyzer.analyze_documentation(doc_docs)

        # Synthesize insights
        hybrid_result = await self.hybrid_analyzer.synthesize_insights(
            config=config_analysis,
            source=source_analysis,
            infra=infra_analysis,
            docs=docs_analysis
        )

        return hybrid_result

    async def _phase4_refinement_check(
        self,
        current_analysis,
        confidence_threshold: float = 0.75
    ) -> Optional[List[FileToLoad]]:
        """
        Phase 4: Refinement - Check if additional iteration needed.

        If confidence < threshold and iterations < 2, request more files.

        Args:
            current_analysis: HybridAnalysisResult
            confidence_threshold: Minimum confidence to skip refinement

        Returns:
            List of additional files to load, or None if refinement not needed
        """
        # Check if refinement already done
        if current_analysis.refinement_iterations >= 2:
            logger.info("[Phase 4] Max iterations reached, skipping refinement")
            return None

        # Check if confidence is sufficient
        if current_analysis.confidence >= confidence_threshold:
            logger.info(f"[Phase 4] Confidence {current_analysis.confidence:.2f} >= {confidence_threshold}, skipping refinement")
            return None

        # Refinement needed - request a few more files
        # (In production, this would use LLM to decide which files to add)
        logger.info(f"[Phase 4] Confidence {current_analysis.confidence:.2f} < {confidence_threshold}, refinement needed")

        # For now, return None (implement refinement logic if needed)
        return None

    def _extract_names_from_attributed_items(self, items: List) -> set:
        """
        Extract names from items that may be strings or attributed dicts (ft-030).

        Handles backward compatibility:
        - Old format: ["Django", "React"]
        - New format: [{"name": "Django", "source_attribution": {...}}, ...]

        Args:
            items: List of strings or attributed dictionaries

        Returns:
            Set of extracted names (strings)
        """
        names = set()
        for item in items:
            if isinstance(item, str):
                names.add(item)
            elif isinstance(item, dict) and 'name' in item:
                names.add(item['name'])
            else:
                logger.warning(f"Unexpected item format in attributed items: {type(item)}")
        return names

    def _extract_all_technologies(self, hybrid_result, structure: RepoStructureAnalysis) -> List[str]:
        """
        Extract and deduplicate all technologies from analysis phases.

        ft-030: Handles both old format (strings) and new format (attributed objects).
        """
        all_techs = set()

        # From config analysis (ft-030: handles attributed format)
        config_techs = self._extract_names_from_attributed_items(
            hybrid_result.config_analysis.get('technologies', [])
        )
        all_techs.update(config_techs)

        # From source analysis (ft-030: handles attributed format)
        source_techs = self._extract_names_from_attributed_items(
            hybrid_result.source_analysis.get('technologies', [])
        )
        all_techs.update(source_techs)

        # From infrastructure services (ft-030: handles attributed format)
        infra_names = self._extract_names_from_attributed_items(
            hybrid_result.infrastructure_analysis.get('services', [])
        )
        all_techs.update(infra_names)

        # From documentation (ft-030: handles attributed format)
        docs_techs = self._extract_names_from_attributed_items(
            hybrid_result.documentation_analysis.get('tech_stack_mentioned', [])
        )
        all_techs.update(docs_techs)

        # Add primary language (always a string)
        if structure.primary_language:
            all_techs.add(structure.primary_language)

        return sorted(list(all_techs))

    def _build_metrics(self, repo_stats: Dict) -> List[Dict]:
        """Build metrics list from repo stats"""
        metrics = []

        if 'stars' in repo_stats:
            metrics.append({
                'type': 'stars',
                'value': repo_stats['stars'],
                'context': 'github_stars'
            })

        if 'forks' in repo_stats:
            metrics.append({
                'type': 'forks',
                'value': repo_stats['forks'],
                'context': 'github_forks'
            })

        if 'contributors' in repo_stats:
            metrics.append({
                'type': 'contributors',
                'value': repo_stats['contributors'],
                'context': 'github_contributors'
            })

        return metrics

    def _aggregate_attribution_metrics(self, hybrid_result) -> Dict:
        """
        Aggregate source attribution metrics from documentation and code analysis (ft-030).

        Combines attribution coverage and inferred item ratios from both documentation
        and source code analysis to provide overall extraction quality metrics.

        Args:
            hybrid_result: HybridAnalysisResult with documentation_analysis and source_analysis

        Returns:
            Dict with:
                - overall_coverage: float (0.0-1.0) - weighted average attribution coverage
                - overall_inferred_ratio: float (0.0-1.0) - weighted average inferred ratio
                - documentation: Dict with coverage, inferred_ratio, total_items, attributed_items
                - code: Dict with coverage, inferred_ratio, total_items, attributed_items
        """
        # Extract documentation attribution metrics
        docs_analysis = hybrid_result.documentation_analysis
        docs_coverage = docs_analysis.get('attribution_coverage', 0.0)
        docs_inferred_ratio = docs_analysis.get('inferred_item_ratio', 0.0)
        docs_total_items = docs_analysis.get('total_items', 0)
        docs_attributed_items = docs_analysis.get('attributed_items', 0)

        # Extract code attribution metrics
        code_analysis = hybrid_result.source_analysis
        code_coverage = code_analysis.get('attribution_coverage', 0.0)
        code_inferred_ratio = code_analysis.get('inferred_item_ratio', 0.0)
        code_total_items = code_analysis.get('total_items', 0)
        code_attributed_items = code_analysis.get('attributed_items', 0)

        # Calculate overall metrics (weighted by number of items)
        total_items = docs_total_items + code_total_items
        if total_items > 0:
            overall_coverage = (
                (docs_attributed_items + code_attributed_items) / total_items
            )
            # Weight inferred ratio by total items
            overall_inferred_ratio = (
                (docs_inferred_ratio * docs_total_items + code_inferred_ratio * code_total_items)
                / total_items
            )
        else:
            overall_coverage = 0.0
            overall_inferred_ratio = 0.0

        logger.info(
            f"[GitHub Attribution] Overall coverage: {overall_coverage:.1%}, "
            f"inferred ratio: {overall_inferred_ratio:.1%} "
            f"(docs: {docs_coverage:.1%}/{docs_inferred_ratio:.1%}, "
            f"code: {code_coverage:.1%}/{code_inferred_ratio:.1%})"
        )

        return {
            'overall_coverage': overall_coverage,
            'overall_inferred_ratio': overall_inferred_ratio,
            'documentation': {
                'coverage': docs_coverage,
                'inferred_ratio': docs_inferred_ratio,
                'total_items': docs_total_items,
                'attributed_items': docs_attributed_items
            },
            'code': {
                'coverage': code_coverage,
                'inferred_ratio': code_inferred_ratio,
                'total_items': code_total_items,
                'attributed_items': code_attributed_items
            }
        }

    def _estimate_cost(self, total_tokens: int) -> float:
        """
        Estimate total LLM cost based on token usage.

        Updated cost model (2025-10-08):
        - Phase 2: GPT-5-mini ($0.0033/repo)
        - Phase 3a+3b: GPT-5 ($0.191/repo combined)
        - Total: ~$0.20/repo (well under $0.50 budget)

        Note: total_tokens parameter kept for backward compatibility but using
        phase-specific estimates for more accurate costing.
        """
        # Use phase-specific cost estimates (more accurate than token-based estimation)
        return PHASE2_COST_ESTIMATE + PHASE3A_COST_ESTIMATE + PHASE3B_COST_ESTIMATE
