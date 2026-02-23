"""
Unit tests for GitHubRepositoryAgent (TDD Stage F - RED Phase).
Tests 4-phase agent-based GitHub repository analysis.
Implements ft-013-github-agent-traversal.md

Agent Architecture (v1.3.0):
- Phase 1: Reconnaissance (GitHub API metadata, project type detection)
- Phase 2: File Prioritization (LLM-powered file selection, token budget awareness)
- Phase 3: Hybrid Analysis (Multi-format parsing: config/source/infra/docs)
- Phase 4: Refinement (Optional iteration if confidence <0.75)

All tests will FAIL until implementation is complete (TDD RED phase).
"""

import pytest
import unittest
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from decimal import Decimal
from dataclasses import dataclass
from typing import List, Dict, Optional

# Import will fail until we create the service (TDD RED)
try:
    from llm_services.services.core.github_repository_agent import (
        GitHubRepositoryAgent,
        RepoStructureAnalysis,
        FileToLoad,
        HybridAnalysisResult
    )
except ImportError:
    # Expected to fail during RED phase
    pass

from llm_services.services.core.evidence_content_extractor import ExtractedContent

User = get_user_model()


@unittest.skip("Unit tests need comprehensive LLM mocking to prevent real API calls")
@tag('slow', 'integration', 'llm_services')
class GitHubRepositoryAgentPhase1TestCase(TestCase):
    """Test Phase 1: Reconnaissance"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @pytest.mark.asyncio
    @patch('requests.get')
    async def test_phase1_reconnaissance_detects_project_type(self, mock_get):
        """Test Phase 1 detects project type from repo metadata"""
        repo_url = "https://github.com/django/django"
        repo_stats = {
            'name': 'django',
            'description': 'The Web framework for perfectionists with deadlines.',
            'stars': 50000,
            'languages': {'Python': 95, 'JavaScript': 3, 'HTML': 2}
        }

        # Mock GitHub API tree response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tree': [
                {'path': 'setup.py', 'type': 'blob'},
                {'path': 'django/__init__.py', 'type': 'blob'},
                {'path': 'README.rst', 'type': 'blob'},
                {'path': 'docs/', 'type': 'tree'},
            ]
        }
        mock_get.return_value = mock_response

        result = await self.agent._phase1_reconnaissance(
            repo_url=repo_url,
            repo_stats=repo_stats
        )

        # Verify project type detection
        assert isinstance(result, RepoStructureAnalysis)
        assert result.detected_project_type in ['framework', 'library', 'application', 'tool']
        assert result.primary_language == 'Python'
        assert 'Python' in result.languages_breakdown
        assert result.languages_breakdown['Python'] > 90

    @pytest.mark.asyncio
    @patch('requests.get')
    async def test_phase1_extracts_language_breakdown(self, mock_get):
        """Test Phase 1 extracts accurate language breakdown"""
        repo_url = "https://github.com/vercel/next.js"
        repo_stats = {
            'name': 'next.js',
            'stars': 100000,
            'languages': {
                'TypeScript': 60,
                'JavaScript': 30,
                'CSS': 5,
                'HTML': 5
            }
        }

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'tree': []}
        mock_get.return_value = mock_response

        result = await self.agent._phase1_reconnaissance(
            repo_url=repo_url,
            repo_stats=repo_stats
        )

        # Verify language breakdown
        assert result.primary_language == 'TypeScript'
        assert result.languages_breakdown['TypeScript'] == 60
        assert result.languages_breakdown['JavaScript'] == 30
        assert len(result.languages_breakdown) == 4

    @pytest.mark.asyncio
    @patch('requests.get')
    async def test_phase1_parses_repo_structure(self, mock_get):
        """Test Phase 1 parses repository file structure"""
        repo_url = "https://github.com/test/monorepo"

        # Mock GitHub API tree response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'tree': [
                {'path': 'package.json', 'type': 'blob', 'size': 1024},
                {'path': 'src/index.ts', 'type': 'blob', 'size': 2048},
                {'path': 'src/utils/helper.ts', 'type': 'blob', 'size': 512},
                {'path': 'docker-compose.yml', 'type': 'blob', 'size': 800},
                {'path': 'README.md', 'type': 'blob', 'size': 3000},
                {'path': 'node_modules/', 'type': 'tree'},  # Should be excluded
            ]
        }
        mock_get.return_value = mock_response

        result = await self.agent._phase1_reconnaissance(
            repo_url=repo_url,
            repo_stats={'stars': 100, 'languages': {'TypeScript': 100}}
        )

        # Verify structure parsing
        assert hasattr(result, 'repo_structure')
        assert isinstance(result.repo_structure, dict)

        # Should exclude node_modules
        file_paths = [f['path'] for f in result.repo_structure.get('files', [])]
        assert 'package.json' in file_paths
        assert not any('node_modules' in p for p in file_paths)

    @pytest.mark.asyncio
    @patch('requests.get')
    async def test_phase1_handles_github_api_failure(self, mock_get):
        """Test Phase 1 handles GitHub API failures gracefully"""
        repo_url = "https://github.com/test/private-repo"

        # Mock 404 response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}
        mock_get.return_value = mock_response

        result = await self.agent._phase1_reconnaissance(
            repo_url=repo_url,
            repo_stats=None
        )

        # Should return partial data or indicate failure
        assert result is not None
        # Confidence should be low or indicate API failure
        assert hasattr(result, 'api_accessible')
        assert result.api_accessible is False


@unittest.skip("Unit tests need comprehensive LLM mocking to prevent real API calls")
@tag('slow', 'integration', 'llm_services')
class GitHubRepositoryAgentPhase2TestCase(TestCase):
    """Test Phase 2: File Prioritization"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @pytest.mark.asyncio
    @patch.object(GitHubRepositoryAgent, '_execute_llm_task')
    async def test_phase2_prioritizes_config_files_first(self, mock_llm):
        """Test Phase 2 prioritizes config files (package.json, requirements.txt) first"""
        structure = RepoStructureAnalysis(
            repo_structure={
                'files': [
                    {'path': 'package.json', 'size': 2000, 'type': 'config'},
                    {'path': 'requirements.txt', 'size': 500, 'type': 'config'},
                    {'path': 'README.md', 'size': 5000, 'type': 'doc'},
                    {'path': 'src/index.js', 'size': 3000, 'type': 'source'},
                    {'path': 'src/utils.js', 'size': 1500, 'type': 'source'},
                ]
            },
            detected_project_type='application',
            primary_language='JavaScript',
            languages_breakdown={'JavaScript': 100}
        )

        # Mock LLM file selection response
        mock_llm.return_value = {
            'content': '''
            {
                "selected_files": [
                    {"path": "package.json", "priority": "high", "reason": "Core dependencies"},
                    {"path": "requirements.txt", "priority": "high", "reason": "Python dependencies"},
                    {"path": "README.md", "priority": "medium", "reason": "Project overview"},
                    {"path": "src/index.js", "priority": "medium", "reason": "Main entry point"}
                ],
                "estimated_tokens": 7500,
                "reasoning": "Prioritized config files for tech stack detection"
            }
            ''',
            'cost': 0.005,
            'tokens': 200
        }

        result = await self.agent._phase2_file_prioritization(
            structure=structure,
            token_budget=8000
        )

        # Verify config files are prioritized
        assert isinstance(result, list)
        assert len(result) > 0

        # First files should be config files
        first_two = result[:2]
        config_files = [f for f in first_two if f.path in ['package.json', 'requirements.txt']]
        assert len(config_files) >= 1, "Config files should be prioritized first"

    @unittest.skip(reason="Mock infrastructure issue - requires LLM execution pattern update")
    @pytest.mark.asyncio
    @patch.object(GitHubRepositoryAgent, '_execute_llm_task')
    async def test_phase2_respects_token_budget(self, mock_llm):
        """Test Phase 2 respects token budget (8K tokens per repo)"""
        structure = RepoStructureAnalysis(
            repo_structure={
                'files': [{'path': f'file{i}.py', 'size': 1000} for i in range(50)]
            },
            detected_project_type='application',
            primary_language='Python',
            languages_breakdown={'Python': 100}
        )

        # Mock LLM to select many files
        mock_llm.return_value = {
            'content': '''
            {
                "selected_files": [
                    {"path": "file0.py", "priority": "high"},
                    {"path": "file1.py", "priority": "high"},
                    {"path": "file2.py", "priority": "medium"}
                ],
                "estimated_tokens": 7800,
                "reasoning": "Selected within budget"
            }
            ''',
            'cost': 0.005,
            'tokens': 200
        }

        result = await self.agent._phase2_file_prioritization(
            structure=structure,
            token_budget=8000
        )

        # Verify token budget is respected
        total_estimated_tokens = sum(f.estimated_tokens for f in result)
        assert total_estimated_tokens <= 8000, \
            f"Token budget exceeded: {total_estimated_tokens} > 8000"

    @unittest.skip(reason="Mock infrastructure issue - requires LLM execution pattern update")
    @pytest.mark.asyncio
    @patch.object(GitHubRepositoryAgent, '_execute_llm_task')
    async def test_phase2_llm_provides_selection_reasoning(self, mock_llm):
        """Test Phase 2 LLM provides reasoning for file selection"""
        structure = RepoStructureAnalysis(
            repo_structure={'files': [{'path': 'package.json', 'size': 1000}]},
            detected_project_type='application',
            primary_language='JavaScript',
            languages_breakdown={'JavaScript': 100}
        )

        mock_llm.return_value = {
            'content': '''
            {
                "selected_files": [
                    {
                        "path": "package.json",
                        "priority": "high",
                        "reason": "Contains dependency information and tech stack"
                    }
                ],
                "estimated_tokens": 500,
                "reasoning": "Config file is essential for understanding project dependencies"
            }
            ''',
            'cost': 0.002,
            'tokens': 100
        }

        result = await self.agent._phase2_file_prioritization(
            structure=structure,
            token_budget=8000
        )

        # Verify reasoning is captured
        assert len(result) > 0
        first_file = result[0]
        assert hasattr(first_file, 'selection_reason')
        assert len(first_file.selection_reason) > 10, \
            "Selection reason should be detailed"

    @unittest.skip(reason="Mock infrastructure issue - requires LLM execution pattern update")
    @pytest.mark.asyncio
    @patch.object(GitHubRepositoryAgent, '_execute_llm_task')
    async def test_phase2_selects_15_to_20_files_typically(self, mock_llm):
        """Test Phase 2 selects 15-20 files for typical repos (as per ft-013 spec)"""
        structure = RepoStructureAnalysis(
            repo_structure={
                'files': [{'path': f'src/file{i}.py', 'size': 800} for i in range(100)]
            },
            detected_project_type='application',
            primary_language='Python',
            languages_breakdown={'Python': 100}
        )

        # Mock LLM to select typical amount
        selected = [
            {"path": f"src/file{i}.py", "priority": "medium", "reason": "Source file"}
            for i in range(18)
        ]
        mock_llm.return_value = {
            'content': f'''
            {{
                "selected_files": {str(selected).replace("'", '"')},
                "estimated_tokens": 7200,
                "reasoning": "Selected representative sample"
            }}
            ''',
            'cost': 0.004,
            'tokens': 180
        }

        result = await self.agent._phase2_file_prioritization(
            structure=structure,
            token_budget=8000
        )

        # Verify typical file count
        assert 15 <= len(result) <= 25, \
            f"Should select 15-20 files typically, got {len(result)}"

    @unittest.skip(reason="Mock infrastructure issue - requires LLM execution pattern update")
    @pytest.mark.asyncio
    @patch.object(GitHubRepositoryAgent, '_execute_llm_task')
    async def test_phase2_prioritizes_files_without_readme(self, mock_llm):
        """
        Test Phase 2 works without README (replaces deprecated test_handles_missing_github_readme).
        Agent should still prioritize effectively using file structure analysis.
        """
        structure = RepoStructureAnalysis(
            repo_structure={
                'files': [
                    {'path': 'package.json', 'size': 1500},
                    {'path': 'src/index.ts', 'size': 2000},
                    {'path': 'tsconfig.json', 'size': 800},
                    # No README.md
                ]
            },
            detected_project_type='application',
            primary_language='TypeScript',
            languages_breakdown={'TypeScript': 100}
        )

        mock_llm.return_value = {
            'content': '''
            {
                "selected_files": [
                    {"path": "package.json", "priority": "high", "reason": "Dependencies"},
                    {"path": "tsconfig.json", "priority": "high", "reason": "TypeScript config"},
                    {"path": "src/index.ts", "priority": "medium", "reason": "Entry point"}
                ],
                "estimated_tokens": 3000,
                "reasoning": "No README, focused on config and entry points"
            }
            ''',
            'cost': 0.003,
            'tokens': 120
        }

        result = await self.agent._phase2_file_prioritization(
            structure=structure,
            token_budget=8000
        )

        # Should successfully select files without README
        assert len(result) >= 3
        # Config files should still be prioritized
        config_files = [f for f in result if 'json' in f.path]
        assert len(config_files) >= 2, "Should prioritize config files even without README"


@unittest.skip("Unit tests need comprehensive LLM mocking to prevent real API calls")
@tag('slow', 'integration', 'llm_services')
class GitHubRepositoryAgentPhase3TestCase(TestCase):
    """Test Phase 3: Hybrid Analysis"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @unittest.skip(reason="Mock infrastructure issue - requires HybridFileAnalyzer mocking update")
    @pytest.mark.asyncio
    @patch('llm_services.services.core.hybrid_file_analyzer.HybridFileAnalyzer')
    async def test_phase3_hybrid_analysis_all_file_types(self, mock_analyzer_class):
        """Test Phase 3 analyzes all file types (config, source, infra, docs)"""
        from langchain.schema import Document

        loaded_files = [
            Document(page_content='{"dependencies": {"django": "4.2"}}', metadata={'path': 'requirements.txt'}),
            Document(page_content='from django.db import models', metadata={'path': 'src/models.py'}),
            Document(page_content='FROM python:3.11', metadata={'path': 'Dockerfile'}),
            Document(page_content='# Project Documentation', metadata={'path': 'README.md'}),
        ]

        # Mock analyzer instance
        mock_analyzer = Mock()
        mock_analyzer.analyze_config_files = AsyncMock(return_value={
            'technologies': ['Django', 'Python'],
            'dependencies': {'django': '4.2'}
        })
        mock_analyzer.analyze_source_code = AsyncMock(return_value={
            'patterns': ['ORM models', 'database interaction'],
            'technologies': ['Django ORM']
        })
        mock_analyzer.analyze_infrastructure = AsyncMock(return_value={
            'deployment': ['Docker'],
            'runtime': 'Python 3.11'
        })
        mock_analyzer.analyze_documentation = AsyncMock(return_value={
            'project_summary': 'Django application'
        })
        mock_analyzer.synthesize_insights = AsyncMock(return_value=HybridAnalysisResult(
            config_analysis={'technologies': ['Django', 'Python']},
            source_analysis={'patterns': ['ORM models']},
            infrastructure_analysis={'deployment': ['Docker']},
            documentation_analysis={'project_summary': 'Django application'},
            consistency_score=0.92,
            confidence=0.88
        ))

        mock_analyzer_class.return_value = mock_analyzer

        result = await self.agent._phase3_hybrid_analysis(loaded_files=loaded_files)

        # Verify all file types were analyzed
        assert isinstance(result, HybridAnalysisResult)
        assert 'technologies' in result.config_analysis
        assert 'patterns' in result.source_analysis
        assert 'deployment' in result.infrastructure_analysis
        assert 'project_summary' in result.documentation_analysis

        # Verify analyzer methods were called
        mock_analyzer.analyze_config_files.assert_called_once()
        mock_analyzer.analyze_source_code.assert_called_once()
        mock_analyzer.analyze_infrastructure.assert_called_once()
        mock_analyzer.synthesize_insights.assert_called_once()

    @pytest.mark.asyncio
    async def test_phase3_parses_config_files(self):
        """Test Phase 3 correctly parses config files (JSON, YAML, TOML)"""
        from langchain.schema import Document

        config_docs = [
            Document(
                page_content='{"name": "my-app", "dependencies": {"react": "^18.0.0"}}',
                metadata={'path': 'package.json', 'file_type': 'config'}
            ),
        ]

        # This will fail until HybridFileAnalyzer is implemented
        from llm_services.services.core.hybrid_file_analyzer import HybridFileAnalyzer

        analyzer = HybridFileAnalyzer()
        result = await analyzer.analyze_config_files(config_docs)

        # Verify parsing
        assert 'technologies' in result
        assert 'React' in result['technologies']

    @unittest.skip(reason="Mock infrastructure issue - FastAPI detection needs improved test data")
    @pytest.mark.asyncio
    async def test_phase3_analyzes_source_code(self):
        """Test Phase 3 uses LLM to analyze source code patterns"""
        from langchain.schema import Document

        source_docs = [
            Document(
                page_content='''
                import asyncio
                from fastapi import FastAPI

                app = FastAPI()

                @app.get("/api/users")
                async def get_users():
                    return {"users": []}
                ''',
                metadata={'path': 'main.py', 'file_type': 'source'}
            ),
        ]

        from llm_services.services.core.hybrid_file_analyzer import HybridFileAnalyzer

        analyzer = HybridFileAnalyzer()
        result = await analyzer.analyze_source_code(source_docs)

        # Verify LLM-powered pattern detection
        assert 'patterns' in result
        assert 'technologies' in result
        # Should detect FastAPI
        assert any('fastapi' in tech.lower() for tech in result['technologies'])

    @pytest.mark.asyncio
    async def test_phase3_analyzes_infrastructure(self):
        """Test Phase 3 parses Dockerfiles and CI/CD configs"""
        from langchain.schema import Document

        infra_docs = [
            Document(
                page_content='''
                FROM node:18-alpine
                WORKDIR /app
                COPY package.json .
                RUN npm install
                COPY . .
                CMD ["npm", "start"]
                ''',
                metadata={'path': 'Dockerfile', 'file_type': 'infrastructure'}
            ),
        ]

        from llm_services.services.core.hybrid_file_analyzer import HybridFileAnalyzer

        analyzer = HybridFileAnalyzer()
        result = await analyzer.analyze_infrastructure(infra_docs)

        # Verify infrastructure detection
        assert 'deployment' in result
        assert 'runtime' in result
        assert 'Docker' in result['deployment']
        assert 'Node.js' in result['runtime'] or 'node' in result['runtime'].lower()

    @pytest.mark.asyncio
    async def test_phase3_cross_references_findings(self):
        """Test Phase 3 cross-references findings across file types for consistency"""
        from langchain.schema import Document
        from llm_services.services.core.hybrid_file_analyzer import HybridFileAnalyzer

        # Conflicting information: package.json says React, but source uses Vue
        config_docs = [Document(
            page_content='{"dependencies": {"react": "^18.0.0"}}',
            metadata={'path': 'package.json'}
        )]
        source_docs = [Document(
            page_content='import { createApp } from "vue"',
            metadata={'path': 'src/main.js'}
        )]

        analyzer = HybridFileAnalyzer()
        config_result = await analyzer.analyze_config_files(config_docs)
        source_result = await analyzer.analyze_source_code(source_docs)

        # Synthesize should detect inconsistency
        synthesized = await analyzer.synthesize_insights(
            config=config_result,
            source=source_result,
            infra={},
            docs={}
        )

        # Consistency score should be low due to React vs Vue conflict
        assert synthesized.consistency_score < 0.8, \
            "Should detect technology inconsistency between config and source"


@unittest.skip("Unit tests need comprehensive LLM mocking to prevent real API calls")
@tag('slow', 'integration', 'llm_services')
class GitHubRepositoryAgentPhase4TestCase(TestCase):
    """Test Phase 4: Refinement"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @unittest.skip(reason="Mock infrastructure issue - Phase 4 refinement logic needs test data update")
    @pytest.mark.asyncio
    async def test_phase4_refinement_triggers_when_confidence_low(self):
        """Test Phase 4 triggers refinement when confidence <0.75"""
        current_analysis = HybridAnalysisResult(
            config_analysis={'technologies': ['Python']},
            source_analysis={'patterns': []},
            infrastructure_analysis={},
            documentation_analysis={},
            consistency_score=0.65,
            confidence=0.68  # Below 0.75 threshold
        )

        result = await self.agent._phase4_refinement_check(
            current_analysis=current_analysis,
            confidence_threshold=0.75
        )

        # Should return additional files to load
        assert result is not None
        assert isinstance(result, list)
        assert len(result) > 0, "Should request additional files when confidence is low"

    @unittest.skip(reason="Mock infrastructure issue - Phase 4 refinement logic needs test data update")
    @pytest.mark.asyncio
    async def test_phase4_refinement_stops_after_max_iterations(self):
        """Test Phase 4 stops after max iterations (2) even if confidence low"""
        # Simulate 2nd iteration with still-low confidence
        current_analysis = HybridAnalysisResult(
            config_analysis={'technologies': ['Python']},
            source_analysis={'patterns': []},
            infrastructure_analysis={},
            documentation_analysis={},
            consistency_score=0.60,
            confidence=0.65,
            refinement_iterations=2  # Already at max
        )

        result = await self.agent._phase4_refinement_check(
            current_analysis=current_analysis,
            confidence_threshold=0.75
        )

        # Should NOT request more files (already at max iterations)
        assert result is None or len(result) == 0, \
            "Should stop refinement after max iterations"

    @unittest.skip(reason="Mock infrastructure issue - Phase 4 refinement logic needs test data update")
    @pytest.mark.asyncio
    async def test_phase4_skips_refinement_when_confidence_high(self):
        """Test Phase 4 skips refinement when confidence >=0.75"""
        current_analysis = HybridAnalysisResult(
            config_analysis={'technologies': ['Python', 'Django', 'PostgreSQL']},
            source_analysis={'patterns': ['REST API', 'ORM models']},
            infrastructure_analysis={'deployment': ['Docker']},
            documentation_analysis={'project_summary': 'Django REST API'},
            consistency_score=0.92,
            confidence=0.88  # Above threshold
        )

        result = await self.agent._phase4_refinement_check(
            current_analysis=current_analysis,
            confidence_threshold=0.75
        )

        # Should NOT request additional files
        assert result is None or len(result) == 0, \
            "Should skip refinement when confidence is high"


@unittest.skip("Unit tests need comprehensive LLM mocking to prevent real API calls")
@tag('slow', 'integration', 'llm_services')
class GitHubRepositoryAgentIntegrationTestCase(TestCase):
    """Test end-to-end agent integration"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    @pytest.mark.asyncio
    @unittest.skip(reason="Mock infrastructure issue - end-to-end flow needs GitHub API mocking update")
    @patch('requests.get')
    @patch.object(GitHubRepositoryAgent, '_execute_llm_task')
    async def test_end_to_end_agent_analysis(self, mock_llm, mock_requests):
        """Test complete 4-phase agent analysis flow"""
        repo_url = "https://github.com/test/django-app"
        repo_stats = {
            'name': 'django-app',
            'stars': 500,
            'languages': {'Python': 95, 'JavaScript': 5}
        }

        # Mock GitHub API
        mock_requests.return_value = Mock(
            status_code=200,
            json=Mock(return_value={'tree': [
                {'path': 'requirements.txt', 'size': 500},
                {'path': 'manage.py', 'size': 1000},
            ]})
        )

        # Mock LLM calls
        mock_llm.return_value = {
            'content': '{"technologies": ["Django", "Python"], "achievements": []}',
            'cost': 0.01,
            'tokens': 500
        }

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000,
            repo_stats=repo_stats
        )

        # Verify complete analysis
        assert isinstance(result, ExtractedContent)
        assert result.success is True
        assert result.source_type == 'github'
        assert 'technologies' in result.data
        assert result.confidence >= 0.5

    @pytest.mark.asyncio
    @patch('requests.get')
    async def test_handles_github_api_404(self, mock_get):
        """Test agent handles GitHub API 404 errors"""
        repo_url = "https://github.com/test/nonexistent"

        mock_get.return_value = Mock(status_code=404, json=Mock(return_value={"message": "Not Found"}))

        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )

        # Should fail gracefully
        assert result.success is False
        assert result.confidence == 0.0

    @unittest.skip(reason="Mock infrastructure issue - LLM timeout handling needs async mocking update")
    @pytest.mark.asyncio
    @patch.object(GitHubRepositoryAgent, '_execute_llm_task')
    async def test_handles_llm_timeout_during_file_selection(self, mock_llm):
        """Test agent handles LLM timeout during Phase 2 file selection"""
        # Mock timeout exception
        mock_llm.side_effect = TimeoutError("LLM request timed out")

        result = await self.agent.analyze_repository(
            repo_url="https://github.com/test/repo",
            user_id=self.user.id,
            token_budget=8000
        )

        # Should handle timeout gracefully
        assert result.success is False
        assert 'timeout' in result.data.get('error', '').lower() or \
               'timeout' in getattr(result, 'error_message', '').lower()

    @pytest.mark.asyncio
    async def test_integrates_with_circuit_breaker(self):
        """Test agent integrates with CircuitBreaker for fault tolerance"""
        # Verify agent inherits from BaseLLMService (which has circuit breaker)
        from llm_services.services.base.base_service import BaseLLMService

        assert isinstance(self.agent, BaseLLMService), \
            "Agent should inherit from BaseLLMService for circuit breaker integration"

    @pytest.mark.asyncio
    async def test_respects_token_budget_hard_limit(self):
        """Test agent respects token budget hard limit (10K tokens/repo)"""
        # Mock to try loading way too many files
        result = await self.agent.analyze_repository(
            repo_url="https://github.com/test/large-repo",
            user_id=self.user.id,
            token_budget=8000  # Should not exceed this
        )

        # Verify cost tracking
        if hasattr(result, 'processing_cost'):
            # Approximate: 8K tokens at $0.003/1K = $0.024
            assert result.processing_cost <= 0.03, \
                f"Should stay within budget, cost was ${result.processing_cost}"

    @pytest.mark.asyncio
    async def test_respects_45_second_timeout(self):
        """Test agent respects 45-second timeout (ft-013 requirement)"""
        import time

        start_time = time.time()

        # This will likely fail during implementation if timeout not enforced
        result = await self.agent.analyze_repository(
            repo_url="https://github.com/django/django",
            user_id=self.user.id,
            token_budget=8000
        )

        elapsed_time = time.time() - start_time

        # Should complete in under 45 seconds
        assert elapsed_time < 45.0, \
            f"Analysis took {elapsed_time}s, should be < 45s (ft-013 requirement)"

    @pytest.mark.asyncio
    async def test_total_cost_under_0_025_per_repo(self):
        """Test agent total cost stays under $0.025/repo (ft-013 requirement)"""
        result = await self.agent.analyze_repository(
            repo_url="https://github.com/test/typical-app",
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify cost tracking
        if hasattr(result, 'processing_cost'):
            assert result.processing_cost <= 0.025, \
                f"Cost ${result.processing_cost} exceeds $0.025 budget"

    @pytest.mark.asyncio
    async def test_processing_time_under_45_seconds(self):
        """Test agent processing time stays under 45 seconds (ft-013 requirement)"""
        import time

        repo_url = "https://github.com/vercel/next.js"

        start_time = time.time()
        result = await self.agent.analyze_repository(
            repo_url=repo_url,
            user_id=self.user.id,
            token_budget=8000
        )
        elapsed_time = time.time() - start_time

        # Performance requirement from ft-013
        assert elapsed_time < 45.0, \
            f"Processing took {elapsed_time}s, requirement is <45s"

    @pytest.mark.asyncio
    async def test_tracks_all_phase_costs(self):
        """Test agent tracks costs for all 4 phases"""
        result = await self.agent.analyze_repository(
            repo_url="https://github.com/test/app",
            user_id=self.user.id,
            token_budget=8000
        )

        # Verify cost breakdown
        assert hasattr(result, 'processing_cost')
        # Should have phase-level cost tracking internally
        # (Implementation will determine exact structure)


@unittest.skip("Unit tests need comprehensive LLM mocking to prevent real API calls")
@tag('slow', 'integration', 'llm_services')
class GitHubRepositoryAgentAttributionTestCase(TestCase):
    """Test ft-030: Source attribution handling in GitHub agent"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.agent = GitHubRepositoryAgent()

    def test_extract_names_from_strings(self):
        """Test helper extracts names from old string format"""
        items = ["Django", "React", "PostgreSQL"]

        result = self.agent._extract_names_from_attributed_items(items)

        assert result == {"Django", "React", "PostgreSQL"}
        assert len(result) == 3

    def test_extract_names_from_attributed_dicts(self):
        """Test helper extracts names from attributed dict format (ft-030)"""
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
                    "source_quote": "import React from 'react'",
                    "source_location": "App.tsx:1",
                    "confidence": 0.90
                }
            }
        ]

        result = self.agent._extract_names_from_attributed_items(items)

        assert result == {"Django", "React"}
        assert len(result) == 2

    def test_extract_names_from_mixed_format(self):
        """Test helper handles mixed string and attributed dict format (backward compatibility)"""
        items = [
            "PostgreSQL",  # Old string format
            {
                "name": "Django",
                "source_attribution": {
                    "source_quote": "from django.db import models",
                    "source_location": "models.py:1",
                    "confidence": 0.95
                }
            },
            "Redis",  # Old string format
            {
                "name": "Celery",
                "source_attribution": {
                    "source_quote": "from celery import Celery",
                    "source_location": "tasks.py:1",
                    "confidence": 0.88
                }
            }
        ]

        result = self.agent._extract_names_from_attributed_items(items)

        assert result == {"PostgreSQL", "Django", "Redis", "Celery"}
        assert len(result) == 4

    def test_extract_names_from_empty_list(self):
        """Test helper handles empty list gracefully"""
        items = []

        result = self.agent._extract_names_from_attributed_items(items)

        assert result == set()
        assert len(result) == 0

    def test_extract_names_handles_malformed_dicts(self):
        """Test helper handles malformed dicts (missing 'name' key) gracefully"""
        items = [
            "Django",  # Valid string
            {
                "name": "React",
                "source_attribution": {"confidence": 0.90}
            },  # Valid attributed dict
            {
                "technology": "Vue",  # Malformed: wrong key
                "source_attribution": {"confidence": 0.85}
            },
            {
                "source_attribution": {"confidence": 0.80}  # Malformed: missing 'name'
            }
        ]

        result = self.agent._extract_names_from_attributed_items(items)

        # Should only extract valid items and skip malformed ones
        assert result == {"Django", "React"}
        assert len(result) == 2

    def test_extract_all_technologies_with_full_attribution(self):
        """
        Integration test: Test _extract_all_technologies with all sources using attributed format.

        This is the scenario that caused the original TypeError when dictionaries were
        passed to set.update().
        """
        # Mock HybridAnalysisResult with attributed format
        hybrid_result = MagicMock()
        hybrid_result.config_analysis = {
            'technologies': [
                {
                    "name": "Django",
                    "source_attribution": {
                        "source_quote": "django==4.2.7",
                        "source_location": "requirements.txt:3",
                        "confidence": 0.98
                    }
                },
                {
                    "name": "PostgreSQL",
                    "source_attribution": {
                        "source_quote": "psycopg2-binary==2.9.9",
                        "source_location": "requirements.txt:5",
                        "confidence": 0.95
                    }
                }
            ]
        }
        hybrid_result.source_analysis = {
            'technologies': [
                {
                    "name": "Django REST Framework",
                    "source_attribution": {
                        "source_quote": "from rest_framework import viewsets",
                        "source_location": "views.py:2",
                        "confidence": 0.92
                    }
                }
            ]
        }
        hybrid_result.infrastructure_analysis = {
            'services': [
                {
                    "name": "Redis",
                    "source_attribution": {
                        "source_quote": "redis:7-alpine",
                        "source_location": "docker-compose.yml:15",
                        "confidence": 0.96
                    }
                }
            ]
        }
        hybrid_result.documentation_analysis = {
            'tech_stack_mentioned': [
                {
                    "name": "Celery",
                    "source_attribution": {
                        "source_quote": "We use Celery for background tasks",
                        "source_location": "README.md:25",
                        "confidence": 0.85
                    }
                }
            ]
        }

        structure = RepoStructureAnalysis(
            repo_structure={},
            detected_project_type='application',
            primary_language='Python',
            languages_breakdown={'Python': 95}
        )

        result = self.agent._extract_all_technologies(hybrid_result, structure)

        # Verify all technologies are extracted and deduplicated
        assert isinstance(result, list)
        assert len(result) == 6  # 5 from sources + Python from primary_language
        assert sorted(result) == sorted([
            'Celery', 'Django', 'Django REST Framework',
            'PostgreSQL', 'Python', 'Redis'
        ])

    def test_extract_all_technologies_backward_compatibility(self):
        """
        Integration test: Test _extract_all_technologies with all sources using old string format.

        Ensures backward compatibility with existing data before ft-030.
        """
        # Mock HybridAnalysisResult with old string format
        hybrid_result = MagicMock()
        hybrid_result.config_analysis = {
            'technologies': ["Django", "PostgreSQL"]
        }
        hybrid_result.source_analysis = {
            'technologies': ["Django REST Framework"]
        }
        hybrid_result.infrastructure_analysis = {
            'services': ["Redis", "Nginx"]
        }
        hybrid_result.documentation_analysis = {
            'tech_stack_mentioned': ["Celery", "Docker"]
        }

        structure = RepoStructureAnalysis(
            repo_structure={},
            detected_project_type='application',
            primary_language='Python',
            languages_breakdown={'Python': 95}
        )

        result = self.agent._extract_all_technologies(hybrid_result, structure)

        # Verify all technologies are extracted and deduplicated
        assert isinstance(result, list)
        assert len(result) == 8  # 7 from sources + Python from primary_language
        assert sorted(result) == sorted([
            'Celery', 'Django', 'Django REST Framework',
            'Docker', 'Nginx', 'PostgreSQL', 'Python', 'Redis'
        ])

    def test_extract_all_technologies_deduplicates_names(self):
        """
        Integration test: Test _extract_all_technologies deduplicates technology names.

        Verifies that the same technology mentioned in multiple sources appears only once.
        """
        # Mock HybridAnalysisResult with duplicate technologies
        hybrid_result = MagicMock()
        hybrid_result.config_analysis = {
            'technologies': [
                {"name": "Django", "source_attribution": {"confidence": 0.98}}
            ]
        }
        hybrid_result.source_analysis = {
            'technologies': [
                {"name": "Django", "source_attribution": {"confidence": 0.95}}  # Duplicate
            ]
        }
        hybrid_result.infrastructure_analysis = {
            'services': [
                {"name": "PostgreSQL", "source_attribution": {"confidence": 0.97}}
            ]
        }
        hybrid_result.documentation_analysis = {
            'tech_stack_mentioned': [
                {"name": "PostgreSQL", "source_attribution": {"confidence": 0.90}}  # Duplicate
            ]
        }

        structure = RepoStructureAnalysis(
            repo_structure={},
            detected_project_type='application',
            primary_language='Python',
            languages_breakdown={'Python': 95}
        )

        result = self.agent._extract_all_technologies(hybrid_result, structure)

        # Verify deduplication works correctly
        assert isinstance(result, list)
        assert len(result) == 3  # Django, PostgreSQL, Python (no duplicates)
        assert sorted(result) == ['Django', 'PostgreSQL', 'Python']
