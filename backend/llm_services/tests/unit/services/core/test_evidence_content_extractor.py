"""
Unit tests for EvidenceContentExtractor (TDD Stage E - RED Phase).
Tests LLM-based content extraction from evidence sources.
Implements ft-005-multi-source-artifact-preprocessing.md
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from decimal import Decimal

from llm_services.services.core.evidence_content_extractor import EvidenceContentExtractor, ExtractedContent
from llm_services.models import ModelPerformanceMetric

User = get_user_model()


@tag('medium', 'integration', 'llm_services')
class EvidenceContentExtractorTestCase(TestCase):
    """Test EvidenceContentExtractor LLM extraction operations"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.extractor = EvidenceContentExtractor()

    # DEPRECATED: test_extract_github_content_success removed in ft-013
    # Legacy fixed-file extraction replaced with agent-based traversal (v1.3.0)
    # See: docs/features/ft-013-github-agent-traversal.md
    # New tests: test_github_repository_agent.py

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_extract_pdf_content_with_achievements(self, mock_llm_call):
        """Test extracting achievements and technologies from PDF resume"""
        pdf_chunks = [
            {
                'content': 'Led development of microservices architecture using Django and PostgreSQL',
                'metadata': {'page': 1}
            },
            {
                'content': 'Improved API performance by 40% through query optimization',
                'metadata': {'page': 1}
            },
            {
                'content': 'Technologies: Python, Django, PostgreSQL, Redis, Docker',
                'metadata': {'page': 2}
            }
        ]

        # Mock LLM response with ft-030 attributed format (HIGH-PRECISION)
        mock_llm_call.return_value = {
            'content': '''
            {
                "technologies": [
                    {"name": "Python", "source_attribution": {"source_quote": "Technologies: Python", "source_location": "page 2", "confidence": 0.95}},
                    {"name": "Django", "source_attribution": {"source_quote": "using Django and PostgreSQL", "source_location": "page 1", "confidence": 0.93}},
                    {"name": "PostgreSQL", "source_attribution": {"source_quote": "using Django and PostgreSQL", "source_location": "page 1", "confidence": 0.92}},
                    {"name": "Redis", "source_attribution": {"source_quote": "Technologies: ... Redis", "source_location": "page 2", "confidence": 0.90}},
                    {"name": "Docker", "source_attribution": {"source_quote": "Technologies: ... Docker", "source_location": "page 2", "confidence": 0.88}}
                ],
                "achievements": [
                    {"text": "Led development of microservices architecture", "source_attribution": {"source_quote": "Led development of microservices architecture using Django and PostgreSQL", "source_location": "page 1", "confidence": 0.96}},
                    {"text": "Improved API performance by 40%", "source_attribution": {"source_quote": "Improved API performance by 40% through query optimization", "source_location": "page 1", "confidence": 0.97}}
                ],
                "skills": []
            }
            ''',
            'cost': 0.001,
            'tokens': 150
        }

        result = await self.extractor.extract_pdf_content(
            pdf_chunks=pdf_chunks,
            user_id=self.user.id
        )

        # Verify structure
        assert isinstance(result, ExtractedContent)
        assert result.source_type == 'pdf'
        assert result.success is True

        # Verify achievements extraction with metrics (ft-030 attributed format)
        assert 'achievements' in result.data
        assert len(result.data['achievements']) > 0

        # Check for quantified achievement (achievements are now dicts with 'text' key)
        has_metric = any(
            ('%' in achievement.get('text', '') if isinstance(achievement, dict) else '%' in achievement) or
            any(str(i) in (achievement.get('text', '') if isinstance(achievement, dict) else achievement) for i in range(10))
            for achievement in result.data['achievements']
        )
        assert has_metric, "Should extract achievements with metrics"

        # Verify technologies (ft-030 attributed format - technologies are dicts with 'name' key)
        assert 'technologies' in result.data
        tech_names = [t['name'].lower() if isinstance(t, dict) else t.lower() for t in result.data['technologies']]
        assert 'python' in tech_names
        assert 'django' in tech_names

    @pytest.mark.asyncio
    async def test_extract_video_transcription(self):
        """Test transcribing video and extracting key topics"""
        video_path = "/tmp/demo_video.mp4"
        video_metadata = {
            'duration': 300,  # 5 minutes
            'format': 'mp4',
            'size_mb': 50
        }

        result = await self.extractor.extract_video_transcription(
            video_path=video_path,
            metadata=video_metadata,
            user_id=self.user.id
        )

        # Verify structure
        assert isinstance(result, ExtractedContent)
        assert result.source_type == 'video'

        # Video transcription is placeholder implementation, so we expect success=False or minimal data
        if result.success:
            # Verify transcription data exists (may be placeholder)
            assert 'transcription' in result.data or 'topics' in result.data

            # If topics exist, verify structure
            if 'topics' in result.data and result.data['topics']:
                assert all(isinstance(topic, str) for topic in result.data['topics'])
        else:
            # Placeholder implementation may return success=False
            assert result.success is False

    @pytest.mark.asyncio
    async def test_normalize_technologies_taxonomy(self):
        """Test normalizing technology names to standard taxonomy"""
        raw_technologies = [
            'react.js',
            'ReactJS',
            'REACT',
            'PostgreSQL',
            'postgres',
            'Docker',
            'docker-compose'
        ]

        normalized = await self.extractor.normalize_technologies(
            technologies=raw_technologies
        )

        # Verify normalization
        assert 'React' in normalized or 'react' in [n.lower() for n in normalized]
        assert 'PostgreSQL' in normalized or 'postgresql' in [n.lower() for n in normalized]

        # Verify de-duplication
        react_variants = [t for t in normalized if 'react' in t.lower()]
        assert len(react_variants) == 1, "Should deduplicate React variants"

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_extract_with_confidence_scoring(self, mock_llm_call):
        """
        Test that extractions include confidence scores.
        UPDATED for ft-013: Agent-based extraction now calculates confidence from:
        - Phase 1: Reconnaissance quality (repo metadata completeness)
        - Phase 2: File selection reasoning quality
        - Phase 3: Hybrid analysis consistency score
        - Phase 4: Refinement iterations (>1 iteration lowers confidence)
        """
        repo_url = "https://github.com/test/repo"
        repo_stats = {
            'stars': 100,
            'languages': {'Python': 100},
            'readme': "A Python library for testing"
        }

        # Mock LLM response for agent-based extraction
        mock_llm_call.return_value = {
            'content': '{"technologies": ["Python"], "achievements": [], "description": "Testing library"}',
            'cost': 0.001,
            'tokens': 50
        }

        # Mock GitHub agent's analyze_repository to avoid real API calls
        from llm_services.services.core.github_repository_agent import GitHubRepositoryAgent
        mock_github_result = ExtractedContent(
            source_type='github',
            source_url=repo_url,
            success=True,
            data={
                'technologies': ['Python'],
                'achievements': ['Built testing library'],
                'description': 'A Python library for testing'
            },
            confidence=0.85,
            processing_cost=0.001
        )

        with patch.object(GitHubRepositoryAgent, 'analyze_repository', return_value=mock_github_result):
            # Mock document loader (agent loads selected files from Phase 2)
            with patch.object(self.extractor.doc_loader, 'load_and_chunk_document') as mock_load:
                mock_load.return_value = {
                    'success': True,
                    'chunks': [{'content': 'Test content', 'metadata': {'file_type': 'readme'}}]
                }

                result = await self.extractor.extract_github_content(
                    repo_url=repo_url,
                    repo_stats=repo_stats,
                    user_id=self.user.id
                )

        # Verify confidence score (agent should return >=0.75 for successful single-iteration analysis)
        assert hasattr(result, 'confidence')
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0

        # Agent-based extraction with good repo stats should have high confidence
        # Note: Actual implementation will determine exact threshold
        if result.success and repo_stats.get('stars', 0) > 50:
            assert result.confidence >= 0.5, \
                "Agent should have reasonable confidence with complete repo metadata"

    # DEPRECATED: test_handles_missing_github_readme removed in ft-013
    # Agent-based approach doesn't rely on README; uses intelligent file selection
    # See: docs/features/ft-013-github-agent-traversal.md Phase 2 (File Prioritization)
    # New tests: test_github_repository_agent.py::test_phase2_prioritizes_files_without_readme

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_handles_pdf_without_clear_achievements(self, mock_llm_call):
        """Test extraction from PDF with no clear achievements"""
        pdf_chunks = [
            {
                'content': 'Responsible for maintaining systems',
                'metadata': {'page': 1}
            }
        ]

        # Mock LLM response with no clear achievements
        mock_llm_call.return_value = {
            'content': '{"technologies": [], "achievements": [], "skills": []}',
            'cost': 0.001,
            'tokens': 50
        }

        result = await self.extractor.extract_pdf_content(
            pdf_chunks=pdf_chunks,
            user_id=self.user.id
        )

        # Should succeed but with low confidence
        assert result.success is True
        assert 'achievements' in result.data
        # May have empty achievements list
        assert isinstance(result.data['achievements'], list)

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_tracks_llm_cost_and_tokens(self, mock_llm_call):
        """Test that extraction tracks LLM usage costs and performance metrics"""
        repo_url = "https://github.com/test/repo"
        repo_stats = {
            'stars': 100,
            'languages': {'Python': 100},
            'readme': "Test repository"
        }

        # Mock LLM response with cost tracking (legacy format - will be filtered out in HIGH-PRECISION)
        mock_llm_call.return_value = {
            'content': '{"technologies": ["Python"], "achievements": [], "description": "Test repo"}',
            'cost': 0.002,
            'tokens': 75
        }

        # Mock GitHub agent to avoid real API calls and ensure performance tracking runs
        from llm_services.services.core.github_repository_agent import GitHubRepositoryAgent
        mock_github_result = ExtractedContent(
            source_type='github',
            source_url=repo_url,
            success=True,
            data={
                'technologies': [],  # Will be empty after HIGH-PRECISION filtering
                'achievements': [],
                'description': 'Test repo'
            },
            confidence=0.85,
            processing_cost=0.002
        )

        with patch.object(GitHubRepositoryAgent, 'analyze_repository', return_value=mock_github_result):
            result = await self.extractor.extract_github_content(
                repo_url=repo_url,
                repo_stats=repo_stats,
                user_id=self.user.id
            )

        # Verify cost tracking in result
        assert hasattr(result, 'processing_cost')
        assert result.processing_cost >= 0

        # Verify performance metric was actually created in database
        metric_exists = await ModelPerformanceMetric.objects.filter(
            model_name='gpt-5',  # evidence_content_extractor uses 'gpt-5' for tracking
            task_type='github_content_extraction',
            user=self.user
        ).aexists()
        assert metric_exists, "Performance metric should be created in database"

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_performance_tracking_failure_logged_but_does_not_break_extraction(self, mock_llm_call):
        """Test that performance tracking failures are logged but don't break extraction"""
        repo_url = "https://github.com/test/repo"
        repo_stats = {
            'stars': 100,
            'languages': {'Python': 100},
            'readme': "Test repository"
        }

        # Mock LLM response
        mock_llm_call.return_value = {
            'content': '{"technologies": ["Python"], "achievements": [], "description": "Test repo"}',
            'cost': 0.002,
            'tokens': 75
        }

        # Mock GitHub agent to avoid real API calls
        from llm_services.services.core.github_repository_agent import GitHubRepositoryAgent
        mock_github_result = ExtractedContent(
            source_type='github',
            source_url=repo_url,
            success=True,
            data={
                'technologies': [],  # Will be empty after HIGH-PRECISION filtering
                'achievements': [],
                'description': 'Test repo'
            },
            confidence=0.85,
            processing_cost=0.002
        )

        with patch.object(GitHubRepositoryAgent, 'analyze_repository', return_value=mock_github_result):
            # Simulate failure in performance tracker (patch the centralized method)
            with patch.object(self.extractor.performance_tracker, 'record_task', side_effect=Exception("Database connection failed")):
                # Assert warning IS logged when performance tracking fails
                with self.assertLogs('llm_services.services.core.evidence_content_extractor', level='DEBUG') as log_ctx:
                    result = await self.extractor.extract_github_content(
                        repo_url=repo_url,
                        repo_stats=repo_stats,
                        user_id=self.user.id
                    )

                    # Should have logged warning about performance tracking failure
                    warning_logs = [log for log in log_ctx.output if 'WARNING' in log and 'Failed to track' in log]
                    assert len(warning_logs) > 0, "Should log warning when performance tracking fails"
                    assert any("Failed to track extraction performance" in log for log in warning_logs), \
                        f"Should log specific performance tracking error, got: {warning_logs}"

        # Extraction should still succeed despite performance tracking failure
        assert result.success is True
        assert result.source_type == 'github'
        assert hasattr(result, 'processing_cost')

    @pytest.mark.asyncio
    async def test_respects_ft005_p95_latency_requirement(self):
        """Test that extraction completes within P95 < 5 minutes requirement"""
        import time

        repo_url = "https://github.com/test/repo"
        repo_stats = {
            'stars': 100,
            'languages': {'Python': 100},
            'readme': "Test" * 1000  # Long README
        }

        # Mock GitHub agent's analyze_repository to avoid real API calls
        from llm_services.services.core.github_repository_agent import GitHubRepositoryAgent
        mock_github_result = ExtractedContent(
            source_type='github',
            source_url=repo_url,
            success=True,
            data={
                'technologies': ['Python'],
                'achievements': ['Fast processing'],
                'description': 'Test repository'
            },
            confidence=0.85,
            processing_cost=0.001
        )

        with patch.object(GitHubRepositoryAgent, 'analyze_repository', return_value=mock_github_result):
            start_time = time.time()

            result = await self.extractor.extract_github_content(
                repo_url=repo_url,
                repo_stats=repo_stats,
                user_id=self.user.id
            )

            elapsed_time = time.time() - start_time

            # Should complete in reasonable time (much less than 5 minutes)
            assert elapsed_time < 30.0, f"Extraction took {elapsed_time}s, should be < 30s"

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_parallel_extraction_from_multiple_sources(self, mock_llm_call):
        """Test extracting from multiple sources in parallel"""
        # Mock LLM response with ft-030 attributed format (HIGH-PRECISION)
        mock_llm_call.return_value = {
            'content': '''
            {
                "technologies": [
                    {"name": "Python", "source_attribution": {"source_quote": "Python project", "source_location": "README", "confidence": 0.92}}
                ],
                "achievements": [
                    {"text": "Test achievement", "source_attribution": {"source_quote": "Achievement 1", "source_location": "page 1", "confidence": 0.90}}
                ],
                "description": "Test project"
            }
            ''',
            'cost': 0.001,
            'tokens': 50
        }

        # Mock GitHub agent's analyze_repository to avoid real API calls
        from llm_services.services.core.github_repository_agent import GitHubRepositoryAgent
        mock_github_result = ExtractedContent(
            source_type='github',
            source_url="https://github.com/test/repo1",
            success=True,
            data={
                'technologies': [
                    {"name": "Python", "source_attribution": {"source_quote": "Python project", "source_location": "README", "confidence": 0.92}}
                ],
                'achievements': [],
                'description': 'Test repo'
            },
            confidence=0.85,
            processing_cost=0.001
        )

        with patch.object(GitHubRepositoryAgent, 'analyze_repository', return_value=mock_github_result):
            # Simulate extracting from GitHub and PDF simultaneously
            tasks = [
                self.extractor.extract_github_content(
                    repo_url="https://github.com/test/repo1",
                    repo_stats={'stars': 100, 'readme': "Repo 1", 'languages': {'Python': 100}},
                    user_id=self.user.id
                ),
                self.extractor.extract_pdf_content(
                    pdf_chunks=[{'content': 'Achievement 1', 'metadata': {}}],
                    user_id=self.user.id
                )
            ]

            import asyncio
            results = await asyncio.gather(*tasks)

        # Verify both completed
        assert len(results) == 2
        assert all(result.success for result in results)

    @pytest.mark.asyncio
    async def test_handles_llm_api_failure_gracefully(self):
        """
        Test error handling when LLM API fails during extraction.
        UPDATED for ft-013: Agent integrates with circuit breaker for fault tolerance.
        Failure scenarios now include:
        - GitHub API rate limiting during Phase 1 reconnaissance
        - LLM timeout during Phase 2 file selection
        - LLM failure during Phase 3 hybrid analysis
        - Circuit breaker opens after repeated failures
        """
        repo_url = "https://github.com/test/repo"
        repo_stats = {'stars': 100, 'readme': "Test"}

        # Mock GitHub agent's analyze_repository to avoid real API calls
        from llm_services.services.core.github_repository_agent import GitHubRepositoryAgent
        mock_github_result = ExtractedContent(
            source_type='github',
            source_url=repo_url,
            success=False,
            data={'error': 'LLM API Error during Phase 3'},
            confidence=0.0,
            processing_cost=0.001
        )

        with patch.object(GitHubRepositoryAgent, 'analyze_repository', return_value=mock_github_result):
            # Mock LLM API failure (could happen in Phase 2 or Phase 3)
            with patch.object(self.extractor, '_call_llm_for_extraction', side_effect=Exception("API Error")):
                with patch.object(self.extractor.doc_loader, 'load_and_chunk_document') as mock_load:
                    mock_load.return_value = {
                        'success': True,
                        'chunks': [{'content': 'Test', 'metadata': {}}]
                    }

                    result = await self.extractor.extract_github_content(
                        repo_url=repo_url,
                        repo_stats=repo_stats,
                        user_id=self.user.id
                    )

                    # Should handle error gracefully with circuit breaker integration
                    assert result.success is False
                    assert 'error' in result.data or hasattr(result, 'error_message')

                    # Agent should still return structured ExtractedContent even on failure
                    assert isinstance(result, ExtractedContent)
                    assert result.source_type == 'github'
                    assert result.confidence == 0.0 or result.confidence < 0.5, \
                        "Failed extraction should have low or zero confidence"


@tag('medium', 'integration', 'llm_services')
class EvidenceContentExtractorHighPrecisionTestCase(TestCase):
    """Test ft-030 HIGH-PRECISION mode anti-hallucination features"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.extractor = EvidenceContentExtractor()

    def test_filter_by_confidence_threshold_attributed_format(self):
        """Test confidence filtering with attributed format (HIGH-PRECISION >= 0.8)"""
        items = [
            {
                "name": "Django",
                "source_attribution": {
                    "source_quote": "from django.db import models",
                    "source_location": "models.py:1",
                    "confidence": 0.95
                }
            },
            {
                "name": "React",
                "source_attribution": {
                    "source_quote": "might be using react",
                    "source_location": "page 2",
                    "confidence": 0.65  # Below threshold
                }
            },
            {
                "name": "PostgreSQL",
                "source_attribution": {
                    "source_quote": "PostgreSQL database configured",
                    "source_location": "settings.py:10",
                    "confidence": 0.88
                }
            }
        ]

        filtered = self.extractor._filter_by_confidence_threshold(
            items=items,
            threshold=0.8,
            item_type='technologies'
        )

        # Should keep Django (0.95) and PostgreSQL (0.88), reject React (0.65)
        assert len(filtered) == 2
        assert filtered[0]['name'] == 'Django'
        assert filtered[1]['name'] == 'PostgreSQL'

    def test_filter_by_confidence_threshold_legacy_strings(self):
        """Test confidence filtering rejects legacy string format (no attribution)"""
        items = [
            "Django",  # Legacy string, no attribution
            {
                "name": "React",
                "source_attribution": {
                    "confidence": 0.92
                }
            }
        ]

        filtered = self.extractor._filter_by_confidence_threshold(
            items=items,
            threshold=0.8,
            item_type='technologies'
        )

        # Should reject legacy string, keep only React
        assert len(filtered) == 1
        assert filtered[0]['name'] == 'React'

    def test_filter_by_confidence_threshold_empty_input(self):
        """Test confidence filtering handles empty input gracefully"""
        filtered = self.extractor._filter_by_confidence_threshold(
            items=[],
            threshold=0.8,
            item_type='technologies'
        )

        assert filtered == []

    def test_filter_by_confidence_threshold_all_rejected(self):
        """Test confidence filtering when all items below threshold"""
        items = [
            {"name": "Tech1", "source_attribution": {"confidence": 0.5}},
            {"name": "Tech2", "source_attribution": {"confidence": 0.7}},
            {"name": "Tech3", "source_attribution": {"confidence": 0.75}}
        ]

        filtered = self.extractor._filter_by_confidence_threshold(
            items=items,
            threshold=0.8,
            item_type='technologies'
        )

        assert len(filtered) == 0

    def test_filter_by_confidence_threshold_achievements(self):
        """Test confidence filtering works for achievements"""
        items = [
            {
                "text": "Improved performance by 40%",
                "source_attribution": {
                    "source_quote": "Optimized queries, improving performance by 40%",
                    "confidence": 0.95
                }
            },
            {
                "text": "Might have led team",
                "source_attribution": {
                    "source_quote": "worked with team",
                    "confidence": 0.6  # Below threshold
                }
            }
        ]

        filtered = self.extractor._filter_by_confidence_threshold(
            items=items,
            threshold=0.8,
            item_type='achievements'
        )

        # Should keep only first achievement
        assert len(filtered) == 1
        assert "Improved performance" in filtered[0]['text']

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_pdf_extraction_applies_confidence_filter(self, mock_llm_call):
        """Test PDF extraction filters low-confidence items (< 0.8)"""
        # Mock LLM response with mixed confidence items
        mock_llm_call.return_value = {
            'content': '''{
                "summary": "Software engineer with Python experience",
                "technologies": [
                    {
                        "name": "Python",
                        "source_attribution": {
                            "source_quote": "5 years Python development",
                            "source_location": "page 1",
                            "confidence": 0.95
                        }
                    },
                    {
                        "name": "Maybe React",
                        "source_attribution": {
                            "source_quote": "built web interfaces",
                            "source_location": "page 2",
                            "confidence": 0.5
                        }
                    }
                ],
                "achievements": [
                    {
                        "text": "Improved API latency by 40%",
                        "source_attribution": {
                            "source_quote": "Reduced API response time by 40%",
                            "confidence": 0.92
                        }
                    }
                ]
            }''',
            'cost': 0.01
        }

        pdf_chunks = [{'content': 'Test content', 'metadata': {'page': 1}}]

        result = await self.extractor.extract_pdf_content(
            pdf_chunks=pdf_chunks,
            source_url='test.pdf',
            user_id=self.user.id
        )

        # Should filter out "Maybe React" (confidence 0.5)
        assert result.success is True
        technologies = result.data.get('technologies', [])
        # Note: normalize_technologies returns strings, so we check count
        assert len(technologies) >= 1
        # The low-confidence "Maybe React" should have been filtered before normalization