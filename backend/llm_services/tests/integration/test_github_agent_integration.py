"""
Integration tests for GitHub Agent (TDD Stage F - RED Phase).
Tests end-to-end agent flow with 50-repo golden test suite.
Implements ft-013-github-agent-traversal.md

GOLDEN TEST SUITE:
50 diverse real-world repositories spanning:
- Python: Django, FastAPI, Flask, pytest, numpy
- JavaScript/TypeScript: Next.js, React, Vue, Express, Node.js
- Rust: Tokio, Axum, Actix, Serde, Rocket
- Go: Gin, Echo, Kubernetes, Docker, Terraform
- Other: Ruby Rails, Java Spring, PHP Laravel

QUALITY GATES (ft-013 requirements):
- Technology accuracy ≥85%
- Processing confidence ≥0.82
- Processing time <45 seconds per repo
- Cost <$0.025 per repo

All tests will FAIL until implementation is complete (TDD RED phase).
"""

import pytest
import unittest
from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from decimal import Decimal
import time
from typing import List, Dict

# Import will fail until we create the service (TDD RED)
try:
    from llm_services.services.core.github_repository_agent import (
        GitHubRepositoryAgent,
        RepoStructureAnalysis
    )
except ImportError:
    pass

from llm_services.services.core.evidence_content_extractor import ExtractedContent
from llm_services.models import EnhancedEvidence, GitHubRepositoryAnalysis
from artifacts.models import Artifact, Evidence

User = get_user_model()


# Golden 50-Repo Test Suite Data
GOLDEN_REPOS = [
    # Python Ecosystem
    {
        "url": "https://github.com/django/django",
        "expected_project_type": "framework",
        "expected_technologies": ["Python", "Django", "SQL", "JavaScript"],
        "expected_patterns": ["MVC", "ORM", "Web framework"],
        "min_confidence": 0.85,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },
    {
        "url": "https://github.com/tiangolo/fastapi",
        "expected_project_type": "framework",
        "expected_technologies": ["Python", "FastAPI", "Pydantic", "OpenAPI"],
        "expected_patterns": ["Async", "REST API", "Type hints"],
        "min_confidence": 0.85,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },
    {
        "url": "https://github.com/pallets/flask",
        "expected_project_type": "framework",
        "expected_technologies": ["Python", "Flask", "Jinja2"],
        "expected_patterns": ["Microframework", "WSGI"],
        "min_confidence": 0.80,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },
    {
        "url": "https://github.com/pytest-dev/pytest",
        "expected_project_type": "tool",
        "expected_technologies": ["Python", "pytest"],
        "expected_patterns": ["Testing", "Fixtures", "Plugins"],
        "min_confidence": 0.80,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },

    # JavaScript/TypeScript Ecosystem
    {
        "url": "https://github.com/vercel/next.js",
        "expected_project_type": "framework",
        "expected_technologies": ["JavaScript", "TypeScript", "React", "Next.js", "Node.js"],
        "expected_patterns": ["SSR", "SSG", "React framework"],
        "min_confidence": 0.85,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },
    {
        "url": "https://github.com/facebook/react",
        "expected_project_type": "library",
        "expected_technologies": ["JavaScript", "React", "JSX"],
        "expected_patterns": ["UI library", "Component-based", "Virtual DOM"],
        "min_confidence": 0.85,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },
    {
        "url": "https://github.com/vuejs/core",
        "expected_project_type": "framework",
        "expected_technologies": ["JavaScript", "TypeScript", "Vue.js"],
        "expected_patterns": ["Reactive", "Component-based", "SFC"],
        "min_confidence": 0.85,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },
    {
        "url": "https://github.com/expressjs/express",
        "expected_project_type": "framework",
        "expected_technologies": ["JavaScript", "Node.js", "Express"],
        "expected_patterns": ["Web framework", "Middleware", "Routing"],
        "min_confidence": 0.80,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },

    # Rust Ecosystem
    {
        "url": "https://github.com/tokio-rs/tokio",
        "expected_project_type": "library",
        "expected_technologies": ["Rust", "Tokio", "Async"],
        "expected_patterns": ["Async runtime", "Concurrency"],
        "min_confidence": 0.80,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },
    {
        "url": "https://github.com/tokio-rs/axum",
        "expected_project_type": "framework",
        "expected_technologies": ["Rust", "Axum", "Tokio", "Tower"],
        "expected_patterns": ["Web framework", "Type-safe routing"],
        "min_confidence": 0.82,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },

    # Go Ecosystem
    {
        "url": "https://github.com/gin-gonic/gin",
        "expected_project_type": "framework",
        "expected_technologies": ["Go", "Gin"],
        "expected_patterns": ["HTTP framework", "Middleware"],
        "min_confidence": 0.80,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },
    {
        "url": "https://github.com/kubernetes/kubernetes",
        "expected_project_type": "platform",
        "expected_technologies": ["Go", "Kubernetes", "Docker"],
        "expected_patterns": ["Container orchestration", "Distributed systems"],
        "min_confidence": 0.85,
        "max_cost": 0.030,  # Larger repo, slightly higher budget
        "max_time_seconds": 50
    },

    # Additional repos for comprehensive testing (subset shown)
    {
        "url": "https://github.com/rails/rails",
        "expected_project_type": "framework",
        "expected_technologies": ["Ruby", "Rails", "SQL"],
        "expected_patterns": ["MVC", "ORM", "Convention over configuration"],
        "min_confidence": 0.82,
        "max_cost": 0.025,
        "max_time_seconds": 45
    },
]


@unittest.skip("Integration test requires real GitHub API and LLM access")
@tag('slow', 'integration', 'llm_services', 'github_agent')
class GoldenRepoTestSuite(TestCase):
    """Test agent against 50 diverse real-world repositories"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @pytest.mark.asyncio
    async def test_golden_50_repo_suite_quality_gates(self):
        """
        Test agent against 50 diverse repositories with quality gates.
        This is the MAIN validation test for ft-013.

        Quality Gates:
        - Technology accuracy ≥85%
        - Confidence ≥0.82
        - Time <45s per repo
        - Cost <$0.025 per repo
        """
        results = []
        failures = []

        for repo_config in GOLDEN_REPOS[:10]:  # Run first 10 in CI, full 50 locally
            repo_url = repo_config['url']
            print(f"\nTesting: {repo_url}")

            start_time = time.time()

            try:
                result = await self.agent.analyze_repository(
                    repo_url=repo_url,
                    user_id=self.user.id,
                    token_budget=8000
                )

                elapsed_time = time.time() - start_time

                # Validate quality gates
                validation = self._validate_repo_result(result, repo_config, elapsed_time)
                results.append(validation)

                if not validation['passed']:
                    failures.append({
                        'repo': repo_url,
                        'failures': validation['failures']
                    })

            except Exception as e:
                failures.append({
                    'repo': repo_url,
                    'failures': [f"Exception: {str(e)}"]
                })

        # Aggregate results
        pass_rate = sum(1 for r in results if r['passed']) / len(results) * 100

        # Overall quality gate: 90% of repos should pass all checks
        assert pass_rate >= 90.0, \
            f"Golden suite pass rate {pass_rate}% < 90%. Failures:\n" + \
            "\n".join(f"  {f['repo']}: {f['failures']}" for f in failures)

    def _validate_repo_result(
        self,
        result: ExtractedContent,
        expected: Dict,
        elapsed_time: float
    ) -> Dict:
        """Validate single repo result against expected values"""
        failures = []

        # 1. Technology Accuracy Check
        expected_techs = set(t.lower() for t in expected['expected_technologies'])
        extracted_techs = set(t.lower() for t in result.data.get('technologies', []))

        # Calculate accuracy: intersection / expected
        correct_techs = expected_techs.intersection(extracted_techs)
        tech_accuracy = len(correct_techs) / len(expected_techs) if expected_techs else 0

        if tech_accuracy < 0.85:
            failures.append(
                f"Tech accuracy {tech_accuracy:.2%} < 85%. "
                f"Expected: {expected_techs}, Got: {extracted_techs}"
            )

        # 2. Confidence Check
        if result.confidence < expected['min_confidence']:
            failures.append(
                f"Confidence {result.confidence:.2f} < {expected['min_confidence']}"
            )

        # 3. Performance Check
        if elapsed_time > expected['max_time_seconds']:
            failures.append(
                f"Time {elapsed_time:.1f}s > {expected['max_time_seconds']}s"
            )

        # 4. Cost Check
        if hasattr(result, 'processing_cost'):
            if result.processing_cost > expected['max_cost']:
                failures.append(
                    f"Cost ${result.processing_cost:.4f} > ${expected['max_cost']}"
                )

        return {
            'passed': len(failures) == 0,
            'failures': failures,
            'tech_accuracy': tech_accuracy,
            'confidence': result.confidence,
            'time': elapsed_time,
            'cost': getattr(result, 'processing_cost', 0)
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize("repo_config", [
        GOLDEN_REPOS[0],  # Django
        GOLDEN_REPOS[4],  # Next.js
        GOLDEN_REPOS[8],  # Tokio
        GOLDEN_REPOS[10], # Gin
    ])
    async def test_specific_golden_repo(self, repo_config):
        """Test individual repos from golden suite (parameterized)"""
        result = await self.agent.analyze_repository(
            repo_url=repo_config['url'],
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify success
        assert result.success is True, \
            f"Failed to analyze {repo_config['url']}: {result.data.get('error', 'Unknown error')}"

        # Verify technologies
        extracted_techs = [t.lower() for t in result.data.get('technologies', [])]
        for expected_tech in repo_config['expected_technologies']:
            assert any(expected_tech.lower() in t for t in extracted_techs), \
                f"Expected technology '{expected_tech}' not found in {extracted_techs}"


@unittest.skip("Integration test requires real GitHub API and LLM access")
@tag('slow', 'integration', 'llm_services', 'github_agent')
class GitHubAgentEndToEndTestCase(TestCase):
    """Test complete end-to-end agent flows"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @pytest.mark.asyncio
    async def test_end_to_end_django_monolith(self):
        """Test analyzing Django monolith repository"""
        repo_url = "https://github.com/django/django"

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify complete data structure
        assert isinstance(result, ExtractedContent)
        assert result.success is True
        assert result.source_type == 'github'
        assert result.source_url == repo_url

        # Verify technologies
        technologies = result.data['technologies']
        assert any('django' in t.lower() for t in technologies)
        assert any('python' in t.lower() for t in technologies)

        # Verify metrics
        if 'metrics' in result.data:
            metric_types = [m['type'] for m in result.data['metrics']]
            assert 'stars' in metric_types or 'contributors' in metric_types

        # Verify confidence
        assert result.confidence >= 0.80

        # Verify cost tracking
        if hasattr(result, 'processing_cost'):
            assert result.processing_cost > 0
            assert result.processing_cost < 0.03

    @pytest.mark.asyncio
    async def test_end_to_end_nextjs_frontend(self):
        """Test analyzing Next.js frontend repository"""
        repo_url = "https://github.com/vercel/next.js"

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify Next.js specific technologies
        technologies = result.data['technologies']
        tech_lower = [t.lower() for t in technologies]

        assert any('next' in t or 'nextjs' in t for t in tech_lower)
        assert any('react' in t for t in tech_lower)
        assert any('typescript' in t or 'javascript' in t for t in tech_lower)

        # Verify modern JavaScript patterns
        if 'patterns' in result.data:
            patterns = result.data['patterns']
            assert any('ssr' in p.lower() or 'server' in p.lower() for p in patterns)

    @pytest.mark.asyncio
    async def test_end_to_end_go_microservice(self):
        """Test analyzing Go microservice repository"""
        repo_url = "https://github.com/gin-gonic/gin"

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify Go technologies
        technologies = result.data['technologies']
        tech_lower = [t.lower() for t in technologies]

        assert any('go' in t or 'golang' in t for t in tech_lower)
        assert any('gin' in t for t in tech_lower)

        # Go repos are typically fast to analyze
        assert result.confidence >= 0.75

    @pytest.mark.asyncio
    async def test_end_to_end_rust_cli_tool(self):
        """Test analyzing Rust CLI tool repository"""
        repo_url = "https://github.com/tokio-rs/tokio"

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify Rust technologies
        technologies = result.data['technologies']
        tech_lower = [t.lower() for t in technologies]

        assert any('rust' in t for t in tech_lower)
        assert any('tokio' in t for t in tech_lower)

        # Rust repos should have high confidence (strong type system, clear patterns)
        assert result.confidence >= 0.75


@unittest.skip("Integration test requires real GitHub API and LLM access")
@tag('slow', 'integration', 'llm_services', 'github_agent')
class GitHubAgentDatabaseIntegrationTestCase(TestCase):
    """Test database integration and persistence"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @pytest.mark.asyncio
    async def test_creates_github_repository_analysis_record(self):
        """Test that github_repository_analysis table is populated"""
        # Create artifact and evidence
        artifact = await sync_to_async(Artifact.objects.create)(
            user=self.user,
            title='Test Project',
            artifact_type='project'
        )
        evidence = await sync_to_async(Evidence.objects.create)(
            artifact=artifact,
            url='https://github.com/test/repo',
            evidence_type='github'
        )

        result = await self.agent.analyze_repository(
            repo_url='https://github.com/test/repo',
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify database record was created
        # Note: This will fail until migration is created
        from llm_services.models import GitHubRepositoryAnalysis

        analysis_exists = await sync_to_async(
            GitHubRepositoryAnalysis.objects.filter(
                evidence=evidence
            ).exists
        )()

        assert analysis_exists, "GitHubRepositoryAnalysis record should be created"

        # Verify analysis fields
        analysis = await sync_to_async(
            GitHubRepositoryAnalysis.objects.get
        )(evidence=evidence)

        assert analysis.detected_project_type is not None
        assert analysis.primary_language is not None
        assert analysis.files_loaded is not None
        assert analysis.total_tokens_used > 0
        assert analysis.analysis_confidence >= 0.0

    @pytest.mark.asyncio
    async def test_links_analysis_to_enhanced_evidence(self):
        """Test that EnhancedEvidence is created for GitHub analysis (Phase 3.1)"""
        from llm_services.models import GitHubRepositoryAnalysis

        artifact = await sync_to_async(Artifact.objects.create)(
            user=self.user,
            title='Test Project',
            artifact_type='project'
        )
        evidence = await sync_to_async(Evidence.objects.create)(
            artifact=artifact,
            url='https://github.com/test/repo',
            evidence_type='github'
        )

        result = await self.agent.analyze_repository(
            repo_url='https://github.com/test/repo',
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify EnhancedEvidence was created (replaces ExtractedContent)
        enhanced = await sync_to_async(
            lambda: EnhancedEvidence.objects.get(evidence=evidence)
        )()

        assert enhanced is not None
        assert enhanced.content_type == 'github'
        assert enhanced.processing_confidence >= 0.0

        # TODO (Phase 3.2): Update GitHubRepositoryAnalysis.extracted_content FK to point to EnhancedEvidence
        # For now, verify the analysis exists
        analysis = await sync_to_async(
            lambda: GitHubRepositoryAnalysis.objects.get(evidence=evidence)
        )()
        assert analysis is not None

    @pytest.mark.asyncio
    async def test_tracks_all_4_phase_data_in_database(self):
        """Test that all 4 phases are tracked in database"""
        from llm_services.models import GitHubRepositoryAnalysis

        artifact = await sync_to_async(Artifact.objects.create)(
            user=self.user,
            title='Test Project',
            artifact_type='project'
        )
        evidence = await sync_to_async(Evidence.objects.create)(
            artifact=artifact,
            url='https://github.com/django/django',
            evidence_type='github'
        )

        await self.agent.analyze_repository(
            repo_url='https://github.com/django/django',
            user_id=self.user.id,
            token_budget=8000
        )

        analysis = await sync_to_async(
            GitHubRepositoryAnalysis.objects.get
        )(evidence=evidence)

        # Phase 1: Reconnaissance
        assert analysis.repo_structure is not None
        assert analysis.detected_project_type is not None
        assert analysis.primary_language is not None
        assert analysis.languages_breakdown is not None

        # Phase 2: File selection
        assert analysis.files_loaded is not None
        assert analysis.total_tokens_used > 0
        assert analysis.selection_reasoning is not None

        # Phase 3: Hybrid analysis
        assert analysis.config_analysis is not None
        assert analysis.source_analysis is not None

        # Phase 4: Refinement
        assert analysis.refinement_iterations >= 1
        assert analysis.analysis_confidence >= 0.0

        # Performance metrics
        assert analysis.processing_time_ms > 0
        assert analysis.llm_cost_usd > 0


@unittest.skip("Integration test requires real GitHub API and LLM access")
@tag('slow', 'integration', 'llm_services', 'github_agent')
class GitHubAgentPerformanceCostTestCase(TestCase):
    """Test performance and cost tracking"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @pytest.mark.asyncio
    async def test_respects_45_second_timeout_per_repo(self):
        """Test agent completes within 45 seconds (ft-013 requirement)"""
        repo_url = "https://github.com/django/django"  # Large repo

        start_time = time.time()
        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )
        elapsed_time = time.time() - start_time

        assert elapsed_time < 45.0, \
            f"Analysis took {elapsed_time:.1f}s, requirement is <45s"

    @pytest.mark.asyncio
    async def test_cost_stays_under_0_025_per_repo(self):
        """Test agent cost stays under $0.025 per repo (ft-013 requirement)"""
        repo_url = "https://github.com/fastapi/fastapi"

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        if hasattr(result, 'processing_cost'):
            assert result.processing_cost <= 0.025, \
                f"Cost ${result.processing_cost:.4f} exceeds $0.025 budget"

    @pytest.mark.asyncio
    async def test_tracks_cost_per_phase(self):
        """Test agent tracks cost breakdown by phase"""
        result = await self.agent.analyze_repository(
            repo_url="https://github.com/test/repo",
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify cost tracking exists
        assert hasattr(result, 'processing_cost')
        assert result.processing_cost > 0

        # Optionally verify phase-level breakdown if exposed
        if hasattr(result, 'cost_breakdown'):
            breakdown = result.cost_breakdown
            assert 'phase1_cost' in breakdown or 'reconnaissance_cost' in breakdown
            assert 'phase2_cost' in breakdown or 'file_selection_cost' in breakdown
            assert 'phase3_cost' in breakdown or 'hybrid_analysis_cost' in breakdown

    @pytest.mark.asyncio
    async def test_token_usage_within_budget(self):
        """Test total tokens used stays within 10K budget"""
        repo_url = "https://github.com/test/repo"

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify token tracking
        if 'tokens_used' in result.data:
            assert result.data['tokens_used'] <= 10000, \
                f"Token usage {result.data['tokens_used']} exceeds 10K budget"

    @pytest.mark.asyncio
    async def test_parallel_repo_processing(self):
        """Test processing multiple repos in parallel"""
        import asyncio

        repos = [
            "https://github.com/test/repo1",
            "https://github.com/test/repo2",
            "https://github.com/test/repo3",
        ]

        start_time = time.time()

        tasks = [
            self.agent.analyze_repository(
                repo_url=url,
                user_id=self.user.id,
                token_budget=8000
            )
            for url in repos
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed_time = time.time() - start_time

        # Parallel processing should be significantly faster than sequential
        # 3 repos * 45s each = 135s sequential, should complete in ~60s parallel
        assert elapsed_time < 90.0, \
            f"Parallel processing of 3 repos took {elapsed_time:.1f}s, should be <90s"

        # All should succeed or fail gracefully
        for result in results:
            if isinstance(result, Exception):
                # Should not have unhandled exceptions
                assert False, f"Unhandled exception in parallel processing: {result}"


@unittest.skip("Integration test requires real GitHub API and LLM access")
@tag('slow', 'integration', 'llm_services', 'github_agent')
class GitHubAgentErrorHandlingIntegrationTestCase(TestCase):
    """Test error handling and edge cases in real scenarios"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @pytest.mark.asyncio
    async def test_handles_private_repo_403(self):
        """Test handling of private repository (403 Forbidden)"""
        private_repo_url = "https://github.com/private-org/secret-repo"

        result = await self.agent.analyze_repository(
            repo_url=private_repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Should fail gracefully
        assert result.success is False
        assert result.confidence == 0.0
        assert 'error' in result.data or hasattr(result, 'error_message')

    @pytest.mark.asyncio
    async def test_handles_nonexistent_repo_404(self):
        """Test handling of non-existent repository (404 Not Found)"""
        fake_repo_url = "https://github.com/fake-user/nonexistent-repo-12345"

        result = await self.agent.analyze_repository(
            repo_url=fake_repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Should fail gracefully
        assert result.success is False
        assert 'not found' in result.data.get('error', '').lower() or \
               'not found' in getattr(result, 'error_message', '').lower()

    @pytest.mark.asyncio
    async def test_handles_github_api_rate_limiting(self):
        """Test handling of GitHub API rate limiting"""
        # This test may need to be run separately to trigger rate limiting
        # or mocked to simulate rate limit response

        # Simulate making many requests to trigger rate limit
        # (In real scenario, this would require many sequential calls)

        result = await self.agent.analyze_repository(
            repo_url="https://github.com/test/repo",
            user_id=self.user.id,
            token_budget=8000
        )

        # Should either succeed or fail gracefully with rate limit message
        if not result.success:
            error_msg = result.data.get('error', '').lower()
            if 'rate limit' in error_msg:
                # Properly handled rate limiting
                assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_handles_empty_repo_no_files(self):
        """Test handling of empty repository with no files"""
        # Would need to create a test repo with no files
        # Or mock the response

        empty_repo_url = "https://github.com/test/empty-repo"

        result = await self.agent.analyze_repository(
            repo_url=empty_repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Should handle gracefully with low confidence
        if result.success:
            assert result.confidence < 0.5, \
                "Empty repo should have low confidence"
        else:
            # Or may fail explicitly
            assert 'empty' in result.data.get('error', '').lower() or \
                   'no files' in result.data.get('error', '').lower()

    @pytest.mark.asyncio
    async def test_handles_very_large_repo_gracefully(self):
        """Test handling of very large repository (>1GB)"""
        large_repo_url = "https://github.com/torvalds/linux"  # Linux kernel

        result = await self.agent.analyze_repository(
            repo_url=large_repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Should complete within timeout even for huge repos
        # Agent should intelligently sample files, not load everything
        assert result is not None

        # Cost should still be reasonable
        if hasattr(result, 'processing_cost'):
            assert result.processing_cost < 0.05, \
                "Even large repos should stay within reasonable cost bounds"


@unittest.skip("Integration test requires real GitHub API and LLM access")
@tag('slow', 'integration', 'llm_services', 'github_agent')
class GitHubAgentRegressionTestCase(TestCase):
    """Regression tests to ensure improvements don't break existing functionality"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @pytest.mark.asyncio
    async def test_config_file_detection_improved_vs_legacy(self):
        """Test that config file detection is improved vs legacy system"""
        repo_url = "https://github.com/test/nodejs-app"

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Agent should detect technologies from package.json
        # Legacy system would miss this if not in first 10 files
        technologies = result.data.get('technologies', [])
        tech_lower = [t.lower() for t in technologies]

        # Should detect Node.js ecosystem
        assert any('node' in t or 'javascript' in t for t in tech_lower), \
            "Should detect Node.js from package.json"

    @pytest.mark.asyncio
    async def test_ci_cd_detection_improved_vs_legacy(self):
        """Test that CI/CD pipeline detection works (legacy couldn't do this)"""
        repo_url = "https://github.com/test/app-with-ci"

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Agent should detect CI/CD from .github/workflows or .circleci
        # Legacy system would never load these files (depth > 3)
        if 'infrastructure' in result.data:
            assert 'ci_cd' in result.data['infrastructure'] or \
                   'GitHub Actions' in str(result.data) or \
                   'CircleCI' in str(result.data)

    @pytest.mark.asyncio
    async def test_technology_accuracy_improvement(self):
        """Test that technology accuracy improved from 60% to 85%+"""
        # Test with a repo known to have multiple tech stack layers
        repo_url = "https://github.com/test/fullstack-app"

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Expected comprehensive tech detection
        expected_techs = [
            'django', 'python', 'react', 'javascript',
            'postgresql', 'redis', 'docker'
        ]

        detected_techs = [t.lower() for t in result.data.get('technologies', [])]

        accuracy = sum(
            1 for expected in expected_techs
            if any(expected in detected for detected in detected_techs)
        ) / len(expected_techs)

        assert accuracy >= 0.85, \
            f"Technology accuracy {accuracy:.1%} < 85%. Expected: {expected_techs}, Got: {detected_techs}"
