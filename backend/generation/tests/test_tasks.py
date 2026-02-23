"""
Unit tests for generation app Celery tasks.

Tests cover:
- generate_document_task (using GenerationService)
- cleanup_expired_generations
- TailoredContentService helper methods
"""

from unittest.mock import patch, Mock, AsyncMock
from django.test import TransactionTestCase, TestCase, tag
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from asgiref.sync import sync_to_async

# Import async test classes
from common.test_base import AsyncTestCase, AsyncTransactionTestCase

from generation.models import (
    JobDescription, GeneratedDocument
)
from generation.tasks import (
    generate_document_task, cleanup_expired_generations
)
from llm_services.services.core.tailored_content_service import TailoredContentService
from artifacts.models import Artifact

User = get_user_model()


# ===== TailoredContentService Helper Method Tests =====

@tag('medium', 'integration', 'generation')
class TailoredContentServiceHelperTests(TestCase):
    """Test cases for TailoredContentService helper methods."""

    def setUp(self):
        self.service = TailoredContentService()

    def test_calculate_skill_match_score(self):
        """Test skill matching score calculation"""
        user_skills = ['Python', 'Django', 'JavaScript']
        job_requirements = ['Python', 'Django', 'React']

        score = self.service._calculate_skill_match_score(user_skills, job_requirements)

        # Should match 2 out of 3 requirements
        expected_score = int((2/3) * 10)
        self.assertEqual(score, expected_score)

    def test_calculate_skill_match_score_empty(self):
        """Test skill matching with empty inputs"""
        self.assertEqual(self.service._calculate_skill_match_score([], ['Python']), 0)
        self.assertEqual(self.service._calculate_skill_match_score(['Python'], []), 0)

    def test_find_missing_skills(self):
        """Test finding missing skills"""
        user_skills = ['Python', 'Django']
        required_skills = ['Python', 'Django', 'React', 'TypeScript']

        missing = self.service._find_missing_skills(user_skills, required_skills)

        self.assertEqual(len(missing), 2)
        self.assertIn('React', missing)
        self.assertIn('TypeScript', missing)

    def test_find_missing_skills_partial_match(self):
        """Test partial skill matching"""
        user_skills = ['JavaScript Programming', 'Python Development']
        required_skills = ['JavaScript', 'Python', 'React']

        missing = self.service._find_missing_skills(user_skills, required_skills)

        # JavaScript and Python should be matched, only React missing
        self.assertEqual(len(missing), 1)
        self.assertIn('React', missing)


# ===== Generation Task Tests =====

@tag('medium', 'integration', 'generation', 'tasks')
class GenerationTaskTests(AsyncTransactionTestCase):
    """Test cases for generation Celery tasks"""

    def setUp(self):
        super().setUp()  # Initialize async event loop
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.job_desc = JobDescription.objects.create(
            content_hash='abc123',
            raw_content='Python developer position',
            parsed_data={
                'must_have_skills': ['Python', 'Django'],
                'nice_to_have_skills': ['React']
            }
        )
        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Django Project',
            technologies=['Python', 'Django']
        )

    @patch('generation.tasks.GenerationService')
    async def test_generate_document_task_no_llm(self, mock_generation_service_class):
        """Test document generation task without LLM service"""
        generation = await sync_to_async(GeneratedDocument.objects.create)(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123',
            job_description=self.job_desc
        )

        # Mock GenerationService to raise exception (service now raises instead of returning error)
        from common.exceptions import GenerationError
        from generation.tasks import _generate_document_async

        mock_generation_service = Mock()
        mock_generation_service.generate_document_for_job = AsyncMock(
            side_effect=GenerationError('No LLM service available')
        )
        mock_generation_service.get_model_selection_strategy = Mock(return_value='balanced')
        mock_generation_service_class.return_value = mock_generation_service

        # Assert that generation failure is logged
        with self.assertLogs('generation.tasks', level='ERROR') as cm:
            # Call the async implementation directly (not the Celery wrapper)
            await _generate_document_async(generation.id)

        # Task should catch exception and mark generation as failed
        await sync_to_async(generation.refresh_from_db)()
        self.assertEqual(generation.status, 'failed')
        self.assertIn('No LLM service available', generation.error_message)

        # Verify expected error message was logged
        self.assertIn('CV generation failed', cm.output[0])
        self.assertIn('No LLM service available', cm.output[0])

    def test_cleanup_expired_generations(self):
        """Test cleanup of expired generations"""
        # Create expired generation
        expired_time = timezone.now() - timedelta(days=1)
        GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123',
            expires_at=expired_time
        )

        # Create valid generation
        future_time = timezone.now() + timedelta(days=1)
        GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='def456',
            expires_at=future_time
        )

        # Run cleanup
        deleted_count = cleanup_expired_generations()

        self.assertEqual(deleted_count, 1)
        self.assertEqual(GeneratedDocument.objects.count(), 1)
