"""
Unit tests for Evidence Re-unification Service (ft-045)
TDD Stage F - RED Phase: These tests will fail initially until implementation in Stage G

Tests the reunify_from_accepted_evidence() method that re-unifies artifact content
from user-edited and accepted EnhancedEvidence.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async

from llm_services.services.core.artifact_enrichment_service import ArtifactEnrichmentService
from llm_services.models import EnhancedEvidence
from artifacts.models import Artifact, Evidence

User = get_user_model()


@tag('medium', 'integration', 'llm_services', 'evidence_review')
class EvidenceReunificationServiceTestCase(TestCase):
    """Test ArtifactEnrichmentService.reunify_from_accepted_evidence() method"""

    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        # Create test artifact
        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Machine Learning Platform',
            description='AI-powered analytics platform',
            user_context='Led team of 5 engineers. Improved performance by 40%.',
            artifact_type='project',
            start_date='2023-01-01',
            end_date='2023-12-31'
        )

        # Create evidence sources
        self.github_evidence = Evidence.objects.create(
            artifact=self.artifact,
            url='https://github.com/test/ml-platform',
            evidence_type='github'
        )

        self.pdf_evidence = Evidence.objects.create(
            artifact=self.artifact,
            url='https://example.com/paper.pdf',
            evidence_type='document'
        )

        # Create ACCEPTED EnhancedEvidence (user-edited)
        self.accepted_github = EnhancedEvidence.objects.create(
            user=self.user,
            evidence=self.github_evidence,
            title='ml-platform',
            content_type='github',
            raw_content='Original GitHub content',
            processed_content={
                'summary': 'Built a machine learning platform with Python and TensorFlow',  # User-edited
                'technologies': ['Python', 'TensorFlow', 'Docker', 'Kubernetes'],  # User added Docker, Kubernetes
                'achievements': [
                    'Deployed ML models to production',
                    'Reduced inference latency by 50%'  # User-edited metric
                ]
            },
            processing_confidence=0.90,
            accepted=True  # ACCEPTED by user
        )

        # Create ACCEPTED PDF evidence
        self.accepted_pdf = EnhancedEvidence.objects.create(
            user=self.user,
            evidence=self.pdf_evidence,
            title='research-paper.pdf',
            content_type='pdf',
            raw_content='Original PDF content',
            processed_content={
                'summary': 'Published research on neural network optimization',
                'technologies': ['Python', 'PyTorch', 'CUDA'],  # Overlapping Python
                'achievements': [
                    'Achieved 92% accuracy on benchmark dataset',
                    'Published in top-tier conference'
                ]
            },
            processing_confidence=0.85,
            accepted=True  # ACCEPTED by user
        )

        # Create REJECTED evidence (should be excluded)
        self.rejected_evidence_source = Evidence.objects.create(
            artifact=self.artifact,
            url='https://example.com/incorrect.pdf',
            evidence_type='document'
        )

        self.rejected_evidence = EnhancedEvidence.objects.create(
            user=self.user,
            evidence=self.rejected_evidence_source,
            title='incorrect.pdf',
            content_type='pdf',
            raw_content='Incorrect content',
            processed_content={
                'summary': 'This content is wrong',
                'technologies': ['IncorrectTech'],
                'achievements': ['Wrong achievement']
            },
            processing_confidence=0.30,
            accepted=False  # REJECTED by user
        )

        self.service = ArtifactEnrichmentService()

    @pytest.mark.asyncio
    @patch.object(ArtifactEnrichmentService, '_execute_llm_task')
    async def test_reunify_from_accepted_evidence(self, mock_llm_task):
        """Test basic re-unification from accepted evidence"""
        # Mock LLM response
        mock_llm_task.return_value = {
            'content': 'Led a team of 5 engineers to build a machine learning platform using Python, TensorFlow, PyTorch, Docker, and Kubernetes. Improved performance by 40% through optimization. Deployed ML models to production with 50% reduced inference latency. Achieved 92% accuracy on benchmark dataset and published research in a top-tier conference.'
        }

        result = await self.service.reunify_from_accepted_evidence(
            artifact_id=self.artifact.id,
            user_id=self.user.id
        )

        # Verify return structure
        self.assertIn('artifact_id', result)
        self.assertIn('unified_description', result)
        self.assertIn('enriched_technologies', result)
        self.assertIn('enriched_achievements', result)
        self.assertIn('processing_confidence', result)

        # Verify artifact ID matches
        self.assertEqual(result['artifact_id'], self.artifact.id)

        # Verify unified description from LLM
        self.assertIn('team of 5', result['unified_description'])  # User context preserved
        self.assertIn('40%', result['unified_description'])  # User metric preserved

        # Verify LLM was called
        mock_llm_task.assert_called_once()
        call_context = mock_llm_task.call_args[1]['context']
        self.assertIn('messages', call_context)

    @pytest.mark.asyncio
    @patch.object(ArtifactEnrichmentService, '_execute_llm_task')
    async def test_reunify_with_user_context(self, mock_llm_task):
        """Test that user_context is treated as immutable ground truth in re-unification"""
        mock_llm_task.return_value = {
            'content': 'Led a team of 5 engineers (preserved from user context) to build ML platform. Improved performance by 40% (preserved from user context). Additional details from evidence...'
        }

        result = await self.service.reunify_from_accepted_evidence(
            artifact_id=self.artifact.id,
            user_id=self.user.id
        )

        # Verify LLM prompt includes user_context
        mock_llm_task.assert_called_once()
        call_context = mock_llm_task.call_args[1]['context']
        prompt = call_context['messages'][1]['content']

        # Verify prompt contains user_context as GROUND TRUTH
        self.assertIn('team of 5', prompt)
        self.assertIn('40%', prompt)
        self.assertIn('GROUND TRUTH', prompt.upper())  # Prompt should emphasize immutability

    @pytest.mark.asyncio
    @patch.object(ArtifactEnrichmentService, '_execute_llm_task')
    async def test_reunify_excluded_rejected(self, mock_llm_task):
        """Test that rejected evidence is excluded from re-unification"""
        mock_llm_task.return_value = {
            'content': 'Unified description from accepted evidence only'
        }

        result = await self.service.reunify_from_accepted_evidence(
            artifact_id=self.artifact.id,
            user_id=self.user.id
        )

        # Verify LLM prompt does NOT include rejected evidence
        call_context = mock_llm_task.call_args[1]['context']
        prompt = call_context['messages'][1]['content']

        # Should NOT contain rejected evidence content
        self.assertNotIn('This content is wrong', prompt)
        self.assertNotIn('IncorrectTech', prompt)
        self.assertNotIn('Wrong achievement', prompt)

        # Should contain accepted evidence content
        self.assertIn('TensorFlow', prompt)
        self.assertIn('PyTorch', prompt)

    @pytest.mark.asyncio
    @patch.object(ArtifactEnrichmentService, '_execute_llm_task')
    async def test_reunify_confidence_calculation(self, mock_llm_task):
        """Test processing confidence = average original confidence + 0.1 user acceptance bonus"""
        mock_llm_task.return_value = {
            'content': 'Unified description'
        }

        result = await self.service.reunify_from_accepted_evidence(
            artifact_id=self.artifact.id,
            user_id=self.user.id
        )

        # Expected confidence = (0.90 + 0.85) / 2 + 0.1 = 0.875 + 0.1 = 0.975
        # But capped at 1.0
        expected_confidence = min(1.0, (0.90 + 0.85) / 2 + 0.1)

        self.assertAlmostEqual(
            result['processing_confidence'],
            expected_confidence,
            places=2
        )

    @pytest.mark.asyncio
    @patch.object(ArtifactEnrichmentService, '_execute_llm_task')
    async def test_reunify_technologies_extraction(self, mock_llm_task):
        """Test technology deduplication from multiple accepted evidence sources"""
        mock_llm_task.return_value = {
            'content': 'Unified description'
        }

        result = await self.service.reunify_from_accepted_evidence(
            artifact_id=self.artifact.id,
            user_id=self.user.id
        )

        technologies = result['enriched_technologies']

        # Verify technologies from both accepted sources
        self.assertIn('Python', technologies)  # In both sources
        self.assertIn('TensorFlow', technologies)  # GitHub
        self.assertIn('PyTorch', technologies)  # PDF
        self.assertIn('Docker', technologies)  # GitHub
        self.assertIn('CUDA', technologies)  # PDF

        # Verify NO rejected evidence technologies
        self.assertNotIn('IncorrectTech', technologies)

        # Verify deduplication (Python appears only once)
        python_count = technologies.count('Python')
        self.assertEqual(python_count, 1, "Python should appear only once (deduplicated)")

    @pytest.mark.asyncio
    @patch.object(ArtifactEnrichmentService, '_execute_llm_task')
    async def test_reunify_achievements_extraction(self, mock_llm_task):
        """Test achievement aggregation from multiple accepted evidence sources"""
        mock_llm_task.return_value = {
            'content': 'Unified description'
        }

        result = await self.service.reunify_from_accepted_evidence(
            artifact_id=self.artifact.id,
            user_id=self.user.id
        )

        achievements = result['enriched_achievements']

        # Verify achievements from both accepted sources
        self.assertIn('Deployed ML models to production', achievements)
        self.assertIn('Reduced inference latency by 50%', achievements)
        self.assertIn('Achieved 92% accuracy on benchmark dataset', achievements)
        self.assertIn('Published in top-tier conference', achievements)

        # Verify NO rejected evidence achievements
        self.assertNotIn('Wrong achievement', achievements)

        # Verify limit (should not exceed 10 achievements as per spec)
        self.assertLessEqual(len(achievements), 10)

    @pytest.mark.asyncio
    @patch.object(ArtifactEnrichmentService, '_execute_llm_task')
    async def test_reunify_llm_failure_fallback(self, mock_llm_task):
        """Test graceful degradation when LLM re-unification fails"""
        # Mock LLM failure
        mock_llm_task.return_value = {
            'error': 'LLM API timeout',
            'error_details': {'original_error': 'Request timeout after 30s'}
        }

        # Assert that LLM failure is logged
        with self.assertLogs('llm_services.services.core.artifact_enrichment_service', level='ERROR') as cm:
            result = await self.service.reunify_from_accepted_evidence(
                artifact_id=self.artifact.id,
                user_id=self.user.id
            )

        # Should return fallback description (artifact title + description)
        self.assertIn('artifact_id', result)
        self.assertIn('unified_description', result)

        # Fallback should include artifact title
        self.assertIn('Machine Learning Platform', result['unified_description'])

        # Fallback should still extract technologies and achievements
        # (even without LLM narrative)
        self.assertGreater(len(result['enriched_technologies']), 0)
        self.assertGreater(len(result['enriched_achievements']), 0)

        # Verify expected error message was logged
        self.assertIn('[reunify] LLM failed for artifact', cm.output[0])
        self.assertIn('LLM API timeout', cm.output[0])
