"""
Unit tests for GitHub source attribution (ft-030).

Tests the enhanced GitHub extraction prompts that require source attribution
with file paths, line numbers, and confidence scores.

Related files:
- llm_services/services/core/hybrid_file_analyzer.py
- llm_services/services/core/github_repository_agent.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from django.test import TestCase, tag
from llm_services.services.core.hybrid_file_analyzer import HybridFileAnalyzer
from llm_services.services.core.github_repository_agent import GitHubRepositoryAgent
from langchain.schema import Document


@tag('fast', 'unit', 'llm_services', 'attribution')
class TestDocumentationAttribution(TestCase):
    """Test source attribution in documentation analysis."""

    def setUp(self):
        """Create HybridFileAnalyzer instance with mocked LLM."""
        self.analyzer = HybridFileAnalyzer()
        self.analyzer.llm_executor.execute = AsyncMock()

    @pytest.mark.asyncio
    async def test_documentation_analysis_includes_attribution(self):
        """Test that documentation analysis returns items with source attribution."""
        # Mock LLM response with attribution
        mock_response = {
            'content': '''{
                "project_summary": "A Django REST API for CV generation",
                "key_features": [
                    {
                        "text": "Real-time collaboration",
                        "source_attribution": {
                            "source_quote": "Support for real-time collaborative editing",
                            "source_file": "README.md",
                            "source_location": "README.md:## Features",
                            "confidence": 0.98,
                            "reasoning": "Direct mention in features section"
                        }
                    }
                ],
                "tech_stack_mentioned": [
                    {
                        "name": "Django",
                        "source_attribution": {
                            "source_quote": "Built with Django 4.2",
                            "source_file": "README.md",
                            "source_location": "README.md:## Tech Stack",
                            "confidence": 0.97,
                            "reasoning": "Direct framework mention with version"
                        }
                    }
                ],
                "achievements": [
                    {
                        "text": "Handles 100K+ concurrent users",
                        "source_attribution": {
                            "source_quote": "Scales to support over 100,000 concurrent users",
                            "source_file": "README.md",
                            "source_location": "README.md:## Performance",
                            "confidence": 0.98,
                            "reasoning": "Direct quote with scale metric"
                        }
                    }
                ],
                "project_type": "REST API"
            }'''
        }
        self.analyzer.llm_executor.execute.return_value = mock_response

        # Create mock documentation
        docs = [
            Document(
                page_content="README content here",
                metadata={'path': 'README.md'}
            )
        ]

        # Call documentation analysis
        result = await self.analyzer.analyze_documentation(docs)

        # Verify attribution structure
        assert 'key_features' in result
        assert len(result['key_features']) > 0
        feature = result['key_features'][0]
        assert isinstance(feature, dict)
        assert 'text' in feature
        assert 'source_attribution' in feature

        # Verify attribution metadata
        attribution = feature['source_attribution']
        assert 'source_quote' in attribution
        assert 'source_file' in attribution
        assert 'source_location' in attribution
        assert 'confidence' in attribution
        assert 'reasoning' in attribution
        assert attribution['confidence'] >= 0.5

    @pytest.mark.asyncio
    async def test_documentation_attribution_coverage_metrics(self):
        """Test that attribution coverage metrics are calculated correctly."""
        # Mock response with 2 attributed items and 1 inferred item
        mock_response = {
            'content': '''{
                "project_summary": "A test project",
                "key_features": [],
                "tech_stack_mentioned": [
                    {
                        "name": "Django",
                        "source_attribution": {
                            "source_quote": "Django 4.2",
                            "source_file": "README.md",
                            "source_location": "README.md:10",
                            "confidence": 0.97,
                            "reasoning": "Direct mention"
                        }
                    },
                    {
                        "name": "React",
                        "source_attribution": {
                            "source_quote": "React frontend",
                            "source_file": "README.md",
                            "source_location": "README.md:15",
                            "confidence": 0.45,
                            "reasoning": "Weak inference from context"
                        }
                    }
                ],
                "achievements": [],
                "project_type": "Web app"
            }'''
        }
        self.analyzer.llm_executor.execute.return_value = mock_response

        docs = [Document(page_content="content", metadata={'path': 'README.md'})]
        result = await self.analyzer.analyze_documentation(docs)

        # Verify coverage metrics
        assert 'attribution_coverage' in result
        assert 'inferred_item_ratio' in result
        assert 'total_items' in result
        assert 'attributed_items' in result

        # 2 technologies both have attribution
        assert result['total_items'] == 2
        assert result['attributed_items'] == 2
        assert result['attribution_coverage'] == 1.0  # 100% coverage

        # 1 out of 2 has confidence < 0.5
        assert result['inferred_item_ratio'] == 0.5  # 50% inferred


@tag('fast', 'unit', 'llm_services', 'attribution')
class TestSourceCodeAttribution(TestCase):
    """Test source attribution in source code analysis."""

    def setUp(self):
        """Create HybridFileAnalyzer instance with mocked LLM."""
        self.analyzer = HybridFileAnalyzer()
        self.analyzer.llm_executor.execute = AsyncMock()

    @pytest.mark.asyncio
    async def test_source_code_analysis_includes_file_line_attribution(self):
        """Test that source code analysis returns items with file:line attribution."""
        # Mock LLM response with code attribution (file:line format)
        mock_response = {
            'content': '''{
                "project_purpose": "Django REST API with service layer pattern",
                "patterns": [
                    {
                        "name": "REST API",
                        "source_attribution": {
                            "source_quote": "@app.route('/api/users', methods=['GET', 'POST'])",
                            "source_file": "app.py",
                            "source_location": "app.py:25",
                            "confidence": 0.98,
                            "reasoning": "Flask route decorator for HTTP API endpoint"
                        }
                    }
                ],
                "technologies": [
                    {
                        "name": "Django",
                        "source_attribution": {
                            "source_quote": "from django.db import models\\nclass User(models.Model):",
                            "source_file": "models.py",
                            "source_location": "models.py:1-5",
                            "confidence": 0.97,
                            "reasoning": "Django ORM model definition"
                        }
                    }
                ],
                "architecture_notes": "Monolithic Django app"
            }'''
        }
        self.analyzer.llm_executor.execute.return_value = mock_response

        # Create mock source code files
        docs = [
            Document(
                page_content="from django.db import models\\nclass User(models.Model):\\n    name = models.CharField()",
                metadata={'path': 'models.py'}
            )
        ]

        # Call source code analysis
        result = await self.analyzer.analyze_source_code(docs)

        # Verify attribution structure
        assert 'technologies' in result
        assert len(result['technologies']) > 0
        tech = result['technologies'][0]
        assert isinstance(tech, dict)
        assert 'name' in tech
        assert 'source_attribution' in tech

        # Verify file:line format
        attribution = tech['source_attribution']
        assert 'source_file' in attribution
        assert 'source_location' in attribution
        # Should be in format "file.py:line" or "file.py:line1-line2"
        assert ':' in attribution['source_location']
        assert attribution['source_file'] in attribution['source_location']

    @pytest.mark.asyncio
    async def test_code_attribution_coverage_metrics(self):
        """Test that code attribution coverage metrics are calculated correctly."""
        # Mock response with 3 patterns, all attributed, 1 low confidence
        mock_response = {
            'content': '''{
                "project_purpose": "Test project",
                "patterns": [
                    {
                        "name": "MVC",
                        "source_attribution": {
                            "source_quote": "class UserController:",
                            "source_file": "controllers.py",
                            "source_location": "controllers.py:15",
                            "confidence": 0.95,
                            "reasoning": "Clear MVC pattern"
                        }
                    },
                    {
                        "name": "Repository",
                        "source_attribution": {
                            "source_quote": "class UserRepository:",
                            "source_file": "repositories.py",
                            "source_location": "repositories.py:10",
                            "confidence": 0.92,
                            "reasoning": "Repository pattern implementation"
                        }
                    },
                    {
                        "name": "Observer",
                        "source_attribution": {
                            "source_quote": "def notify_listeners():",
                            "source_file": "events.py",
                            "source_location": "events.py:45",
                            "confidence": 0.48,
                            "reasoning": "Weak pattern, might be simple callback"
                        }
                    }
                ],
                "technologies": [],
                "architecture_notes": "Layered architecture"
            }'''
        }
        self.analyzer.llm_executor.execute.return_value = mock_response

        docs = [Document(page_content="code", metadata={'path': 'app.py'})]
        result = await self.analyzer.analyze_source_code(docs)

        # Verify coverage metrics
        assert 'attribution_coverage' in result
        assert 'inferred_item_ratio' in result
        assert result['total_items'] == 3  # 3 patterns
        assert result['attributed_items'] == 3  # all have attribution
        assert result['attribution_coverage'] == 1.0  # 100%
        # 1 out of 3 has confidence < 0.5
        assert result['inferred_item_ratio'] == pytest.approx(1/3, rel=0.01)


@tag('fast', 'unit', 'llm_services', 'attribution')
class TestGitHubAgentAggregation(TestCase):
    """Test attribution metric aggregation in GitHub agent."""

    def setUp(self):
        """Create GitHubRepositoryAgent instance."""
        self.agent = GitHubRepositoryAgent()

    def test_aggregate_attribution_metrics(self):
        """Test that GitHub agent correctly aggregates attribution metrics."""
        # Mock hybrid result with attribution metrics from both sources
        mock_hybrid_result = MagicMock()
        mock_hybrid_result.documentation_analysis = {
            'project_summary': 'Test project',
            'attribution_coverage': 0.95,
            'inferred_item_ratio': 0.10,
            'total_items': 10,
            'attributed_items': 10
        }
        mock_hybrid_result.source_analysis = {
            'project_purpose': 'Test purpose',
            'attribution_coverage': 0.90,
            'inferred_item_ratio': 0.20,
            'total_items': 5,
            'attributed_items': 5
        }

        # Call aggregation method
        result = self.agent._aggregate_attribution_metrics(mock_hybrid_result)

        # Verify structure
        assert 'overall_coverage' in result
        assert 'overall_inferred_ratio' in result
        assert 'documentation' in result
        assert 'code' in result

        # Verify weighted averages
        # Overall coverage: (10 + 5) / (10 + 5) = 15/15 = 1.0
        assert result['overall_coverage'] == 1.0

        # Overall inferred ratio: (0.10*10 + 0.20*5) / 15 = (1.0 + 1.0) / 15 = 2.0/15 ≈ 0.133
        assert result['overall_inferred_ratio'] == pytest.approx(0.133, rel=0.01)

        # Verify individual metrics preserved
        assert result['documentation']['coverage'] == 0.95
        assert result['documentation']['inferred_ratio'] == 0.10
        assert result['code']['coverage'] == 0.90
        assert result['code']['inferred_ratio'] == 0.20

    def test_aggregate_attribution_metrics_with_no_items(self):
        """Test aggregation handles zero items gracefully."""
        mock_hybrid_result = MagicMock()
        mock_hybrid_result.documentation_analysis = {
            'attribution_coverage': 0.0,
            'inferred_item_ratio': 0.0,
            'total_items': 0,
            'attributed_items': 0
        }
        mock_hybrid_result.source_analysis = {
            'attribution_coverage': 0.0,
            'inferred_item_ratio': 0.0,
            'total_items': 0,
            'attributed_items': 0
        }

        result = self.agent._aggregate_attribution_metrics(mock_hybrid_result)

        # Should not divide by zero
        assert result['overall_coverage'] == 0.0
        assert result['overall_inferred_ratio'] == 0.0


@tag('fast', 'unit', 'llm_services', 'attribution')
class TestAttributionCalculationMethods(TestCase):
    """Test the attribution metrics calculation methods."""

    def setUp(self):
        """Create HybridFileAnalyzer instance."""
        self.analyzer = HybridFileAnalyzer()

    def test_calculate_github_attribution_metrics_all_attributed(self):
        """Test calculation when all items have attribution."""
        extracted = {
            'key_features': [
                {
                    'text': 'Feature 1',
                    'source_attribution': {
                        'source_quote': 'quote',
                        'confidence': 0.95
                    }
                }
            ],
            'tech_stack_mentioned': [
                {
                    'name': 'Django',
                    'source_attribution': {
                        'source_quote': 'Django 4.2',
                        'confidence': 0.97
                    }
                }
            ],
            'achievements': []
        }

        result = self.analyzer._calculate_github_attribution_metrics(extracted)

        assert result['total_items'] == 2
        assert result['attributed_items'] == 2
        assert result['coverage'] == 1.0  # 100%
        assert result['inferred_ratio'] == 0.0  # No low-confidence items

    def test_calculate_github_attribution_metrics_mixed_confidence(self):
        """Test calculation with mixed confidence levels."""
        extracted = {
            'key_features': [],
            'tech_stack_mentioned': [
                {'name': 'Django', 'source_attribution': {'source_quote': 'quote', 'confidence': 0.95}},
                {'name': 'React', 'source_attribution': {'source_quote': 'quote', 'confidence': 0.45}},
                {'name': 'PostgreSQL', 'source_attribution': {'source_quote': 'quote', 'confidence': 0.92}}
            ],
            'achievements': []
        }

        result = self.analyzer._calculate_github_attribution_metrics(extracted)

        assert result['total_items'] == 3
        assert result['attributed_items'] == 3  # All have attribution
        assert result['coverage'] == 1.0
        # 1 out of 3 has confidence < 0.5
        assert result['inferred_ratio'] == pytest.approx(1/3, rel=0.01)

    def test_calculate_github_code_attribution_metrics(self):
        """Test code attribution metrics calculation."""
        extracted = {
            'patterns': [
                {'name': 'MVC', 'source_attribution': {'source_quote': 'code', 'confidence': 0.95}}
            ],
            'technologies': [
                {'name': 'Django', 'source_attribution': {'source_quote': 'code', 'confidence': 0.48}},
                {'name': 'React', 'source_attribution': {'source_quote': 'code', 'confidence': 0.92}}
            ]
        }

        result = self.analyzer._calculate_github_code_attribution_metrics(extracted)

        assert result['total_items'] == 3  # 1 pattern + 2 technologies
        assert result['attributed_items'] == 3
        assert result['coverage'] == 1.0
        # 1 out of 3 has confidence < 0.5
        assert result['inferred_ratio'] == pytest.approx(1/3, rel=0.01)
