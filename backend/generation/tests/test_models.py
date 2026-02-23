"""
Unit tests for generation app models
"""

import uuid
from datetime import datetime, timedelta
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.utils import timezone

from generation.models import (
    JobDescription, GeneratedDocument, CVTemplate,
    GenerationFeedback, SkillsTaxonomy
)
# ft-006 models (will be created in Phase 3 - TDD Green)
try:
    from generation.models import BulletPoint, BulletGenerationJob
    BULLET_MODELS_AVAILABLE = True
except ImportError:
    BULLET_MODELS_AVAILABLE = False
    BulletPoint = None
    BulletGenerationJob = None

User = get_user_model()


@tag('medium', 'integration', 'generation')
class JobDescriptionModelTests(TestCase):
    """Test cases for JobDescription model"""

    def test_job_description_creation(self):
        """Test basic job description creation"""
        job_desc = JobDescription.objects.create(
            content_hash='abc123',
            raw_content='Software Engineer position at TechCorp',
            company_name='TechCorp',
            role_title='Software Engineer',
            parsing_confidence=0.9
        )

        self.assertEqual(job_desc.content_hash, 'abc123')
        self.assertEqual(job_desc.company_name, 'TechCorp')
        self.assertEqual(job_desc.parsing_confidence, 0.9)

    def test_get_or_create_from_content(self):
        """Test get_or_create_from_content method"""
        content = 'Looking for a Python developer'

        # First call should create
        job_desc1, created1 = JobDescription.get_or_create_from_content(
            content, 'TechCorp', 'Python Developer'
        )
        self.assertTrue(created1)
        self.assertEqual(job_desc1.company_name, 'TechCorp')

        # Second call should retrieve existing
        job_desc2, created2 = JobDescription.get_or_create_from_content(
            content, 'TechCorp', 'Python Developer'
        )
        self.assertFalse(created2)
        self.assertEqual(job_desc1.id, job_desc2.id)



@tag('medium', 'integration', 'generation')
class GeneratedDocumentModelTests(TestCase):
    """Test cases for GeneratedDocument model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.job_desc = JobDescription.objects.create(
            content_hash='abc123',
            raw_content='Test job description'
        )

    def test_generated_document_creation(self):
        """Test basic generated document creation"""
        expires_at = timezone.now() + timedelta(days=90)

        doc = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123',
            job_description=self.job_desc,
            expires_at=expires_at
        )

        self.assertEqual(doc.user, self.user)
        self.assertEqual(doc.document_type, 'cv')
        self.assertEqual(doc.status, 'processing')  # Default status
        self.assertIsInstance(doc.id, uuid.UUID)

    def test_generated_document_with_content(self):
        """Test generated document with CV content"""
        content = {
            'professional_summary': 'Experienced developer',
            'key_skills': ['Python', 'Django'],
            'experience': [
                {
                    'title': 'Software Engineer',
                    'organization': 'TechCorp',
                    'achievements': ['Built web apps']
                }
            ]
        }

        doc = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123',
            content=content,
            status='completed'
        )

        self.assertEqual(doc.content['professional_summary'], 'Experienced developer')
        self.assertEqual(len(doc.content['key_skills']), 2)
        self.assertEqual(doc.status, 'completed')



@tag('medium', 'integration', 'generation')
class CVTemplateModelTests(TestCase):
    """Test cases for CVTemplate model"""

    def test_cv_template_creation(self):
        """Test CV template creation"""
        template = CVTemplate.objects.create(
            name='Modern Professional',
            category='modern',
            description='A modern professional template',
            template_config={'font': 'Arial', 'color': '#000'},
            prompt_template='Generate CV with: {requirements}',
            is_premium=False,
            is_active=True
        )

        self.assertEqual(template.name, 'Modern Professional')
        self.assertEqual(template.category, 'modern')
        self.assertFalse(template.is_premium)
        self.assertTrue(template.is_active)



@tag('medium', 'integration', 'generation')
class GenerationFeedbackModelTests(TestCase):
    """Test cases for GenerationFeedback model"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123'
        )

    def test_feedback_creation(self):
        """Test feedback creation"""
        feedback = GenerationFeedback.objects.create(
            generation=self.generation,
            feedback_type='rating',
            feedback_data={'rating': 8, 'comment': 'Good quality'}
        )

        self.assertEqual(feedback.generation, self.generation)
        self.assertEqual(feedback.feedback_type, 'rating')
        self.assertEqual(feedback.feedback_data['rating'], 8)


@tag('medium', 'integration', 'generation')
class SkillsTaxonomyModelTests(TestCase):
    """Test cases for SkillsTaxonomy model"""

    def test_skills_taxonomy_creation(self):
        """Test skills taxonomy creation"""
        skill = SkillsTaxonomy.objects.create(
            skill_name='Python',
            category='programming',
            aliases=['Python3', 'py'],
            related_skills=['Django', 'Flask'],
            popularity_score=95
        )

        self.assertEqual(skill.skill_name, 'Python')
        self.assertEqual(skill.category, 'programming')
        self.assertEqual(len(skill.aliases), 2)
        self.assertEqual(skill.popularity_score, 95)


# ===== ft-006 Bullet Point Model Tests (TDD Red Phase) =====
# Reference: spec-20251001-ft006-implementation.md
# These tests will fail until models are implemented in Phase 3 (TDD Green)


@tag('medium', 'integration', 'generation')
class BulletPointModelTests(TestCase):
    """
    Test cases for BulletPoint model (ft-006).

    Tests cover:
    - Model creation and field validation
    - Three-bullet hierarchy enforcement
    - Length constraints (60-150 characters)
    - Position constraints (1-3)
    - Unique constraint (cv_generation + artifact + position)
    - User approval/editing tracking
    - Quality metrics
    """

    def setUp(self):
        """Set up test data"""
        if not BULLET_MODELS_AVAILABLE:
            self.skipTest("BulletPoint model not yet implemented (TDD Red phase)")

        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

        # Import Artifact model
        from artifacts.models import Artifact
        self.artifact = Artifact.objects.create(
            user=self.user,
            title='E-commerce Platform Development',
            description='Led development of microservices platform',
            artifact_type='project'
        )

        self.job_desc = JobDescription.objects.create(
            content_hash='abc123',
            raw_content='Senior Software Engineer at TechCorp'
        )

        self.cv_generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123',
            job_description=self.job_desc
        )

    def test_bullet_point_creation_with_achievement_type(self):
        """Test creating bullet point with achievement type (position 1)"""
        bullet = BulletPoint.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=1,
            bullet_type='achievement',
            text='Led development of microservices platform serving 100k+ daily users with 99.9% uptime',
            keywords=['microservices', 'platform', 'led', 'development'],
            metrics={'users': '100k+', 'uptime': '99.9%'},
            confidence_score=0.92,
            quality_score=0.87,
            has_action_verb=True,
            keyword_relevance_score=0.85
        )

        self.assertEqual(bullet.position, 1)
        self.assertEqual(bullet.bullet_type, 'achievement')
        self.assertEqual(len(bullet.text), 85)
        self.assertIn('microservices', bullet.keywords)
        self.assertEqual(bullet.metrics['users'], '100k+')
        self.assertEqual(bullet.confidence_score, 0.92)
        self.assertFalse(bullet.user_approved)
        self.assertFalse(bullet.user_edited)

    def test_bullet_point_creation_with_technical_type(self):
        """Test creating bullet point with technical type (position 2)"""
        bullet = BulletPoint.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=2,
            bullet_type='technical',
            text='Built scalable architecture using Python, Django, and PostgreSQL with Docker containerization',
            keywords=['Python', 'Django', 'PostgreSQL', 'Docker', 'architecture'],
            metrics={},
            confidence_score=0.89,
            quality_score=0.84
        )

        self.assertEqual(bullet.position, 2)
        self.assertEqual(bullet.bullet_type, 'technical')
        self.assertIn('Python', bullet.keywords)

    def test_bullet_point_creation_with_impact_type(self):
        """Test creating bullet point with impact type (position 3)"""
        bullet = BulletPoint.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=3,
            bullet_type='impact',
            text='Improved system performance by 40% while managing cross-functional team of 6 engineers',
            keywords=['performance', 'improvement', 'team management'],
            metrics={'performance_improvement': '40%', 'team_size': 6},
            confidence_score=0.88,
            quality_score=0.86
        )

        self.assertEqual(bullet.position, 3)
        self.assertEqual(bullet.bullet_type, 'impact')
        self.assertEqual(bullet.metrics['performance_improvement'], '40%')

    def test_bullet_point_length_validation_minimum(self):
        """Test bullet point text must be at least 60 characters"""
        from django.core.exceptions import ValidationError

        # Try to create bullet with text < 60 chars
        bullet = BulletPoint(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=1,
            bullet_type='achievement',
            text='Short text',  # Only 10 characters
            confidence_score=0.8,
            quality_score=0.7
        )

        with self.assertRaises(ValidationError):
            bullet.full_clean()  # Should raise ValidationError

    def test_bullet_point_length_validation_maximum(self):
        """Test bullet point text must not exceed 150 characters"""
        from django.core.exceptions import ValidationError

        # Try to create bullet with text > 150 chars
        long_text = 'A' * 151  # 151 characters
        bullet = BulletPoint(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=1,
            bullet_type='achievement',
            text=long_text,
            confidence_score=0.8,
            quality_score=0.7
        )

        with self.assertRaises(ValidationError):
            bullet.full_clean()

    def test_bullet_point_position_validation(self):
        """Test bullet position must be 1, 2, or 3"""
        from django.core.exceptions import ValidationError

        # Try position = 0
        bullet_zero = BulletPoint(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=0,  # Invalid
            bullet_type='achievement',
            text='A' * 80,
            confidence_score=0.8
        )

        with self.assertRaises(ValidationError):
            bullet_zero.full_clean()

        # Try position = 4
        bullet_four = BulletPoint(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=4,  # Invalid
            bullet_type='achievement',
            text='A' * 80,
            confidence_score=0.8
        )

        with self.assertRaises(ValidationError):
            bullet_four.full_clean()

    def test_bullet_point_hierarchy_validation_position_1_must_be_achievement(self):
        """Test position 1 must be 'achievement' type"""
        from django.core.exceptions import ValidationError

        bullet = BulletPoint(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=1,
            bullet_type='technical',  # Wrong type for position 1
            text='A' * 80,
            confidence_score=0.8
        )

        with self.assertRaises(ValidationError) as context:
            bullet.clean()

        self.assertIn('achievement', str(context.exception))

    def test_bullet_point_hierarchy_validation_position_2_must_be_technical(self):
        """Test position 2 must be 'technical' type"""
        from django.core.exceptions import ValidationError

        bullet = BulletPoint(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=2,
            bullet_type='achievement',  # Wrong type for position 2
            text='A' * 80,
            confidence_score=0.8
        )

        with self.assertRaises(ValidationError) as context:
            bullet.clean()

        self.assertIn('technical', str(context.exception))

    def test_bullet_point_hierarchy_validation_position_3_must_be_impact(self):
        """Test position 3 must be 'impact' type"""
        from django.core.exceptions import ValidationError

        bullet = BulletPoint(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=3,
            bullet_type='achievement',  # Wrong type for position 3
            text='A' * 80,
            confidence_score=0.8
        )

        with self.assertRaises(ValidationError) as context:
            bullet.clean()

        self.assertIn('impact', str(context.exception))

    def test_bullet_point_unique_constraint_per_artifact_and_position(self):
        """Test unique constraint: (cv_generation, artifact, position)"""
        from django.db import IntegrityError

        # Create first bullet
        BulletPoint.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=1,
            bullet_type='achievement',
            text='A' * 80,
            confidence_score=0.8
        )

        # Try to create duplicate (same cv_generation, artifact, position)
        with self.assertRaises(IntegrityError):
            BulletPoint.objects.create(
                artifact=self.artifact,
                cv_generation=self.cv_generation,
                position=1,  # Same position
                bullet_type='achievement',
                text='B' * 80,
                confidence_score=0.7
            )

    def test_bullet_point_user_approval_tracking(self):
        """Test user approval and editing tracking"""
        bullet = BulletPoint.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=1,
            bullet_type='achievement',
            text='A' * 80,
            confidence_score=0.8
        )

        # Initially not approved/edited
        self.assertFalse(bullet.user_approved)
        self.assertFalse(bullet.user_edited)
        self.assertEqual(bullet.original_text, '')

        # User approves bullet
        bullet.user_approved = True
        bullet.save()
        self.assertTrue(bullet.user_approved)

        # User edits bullet
        original_text = bullet.text
        bullet.original_text = original_text
        bullet.text = 'B' * 80
        bullet.user_edited = True
        bullet.save()

        self.assertTrue(bullet.user_edited)
        self.assertEqual(bullet.original_text, original_text)
        self.assertNotEqual(bullet.text, original_text)

    def test_bullet_point_string_representation(self):
        """Test __str__ method"""
        bullet = BulletPoint.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=1,
            bullet_type='achievement',
            text='A' * 80,
            confidence_score=0.8
        )

        expected = f"Bullet 1 for {self.artifact.title} (achievement)"
        self.assertEqual(str(bullet), expected)

    def test_bullet_point_quality_metrics(self):
        """Test quality metrics are stored correctly"""
        bullet = BulletPoint.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=1,
            bullet_type='achievement',
            text='A' * 80,
            confidence_score=0.92,
            quality_score=0.87,
            has_action_verb=True,
            keyword_relevance_score=0.85
        )

        self.assertEqual(bullet.confidence_score, 0.92)
        self.assertEqual(bullet.quality_score, 0.87)
        self.assertTrue(bullet.has_action_verb)
        self.assertEqual(bullet.keyword_relevance_score, 0.85)

    def test_bullet_point_ordering(self):
        """Test bullets are ordered by cv_generation, artifact, position"""
        # Create 3 bullets for same artifact
        bullet3 = BulletPoint.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=3,
            bullet_type='impact',
            text='C' * 80,
            confidence_score=0.8
        )
        bullet1 = BulletPoint.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=1,
            bullet_type='achievement',
            text='A' * 80,
            confidence_score=0.8
        )
        bullet2 = BulletPoint.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            position=2,
            bullet_type='technical',
            text='B' * 80,
            confidence_score=0.8
        )

        # Fetch all bullets
        bullets = BulletPoint.objects.filter(
            cv_generation=self.cv_generation,
            artifact=self.artifact
        )

        # Should be ordered by position (1, 2, 3)
        self.assertEqual(bullets[0], bullet1)
        self.assertEqual(bullets[1], bullet2)
        self.assertEqual(bullets[2], bullet3)


@tag('medium', 'integration', 'generation')
class BulletGenerationJobModelTests(TestCase):
    """
    Test cases for BulletGenerationJob model (ft-006).

    Tests cover:
    - Job creation and status tracking
    - Status transitions (pending → processing → completed/failed)
    - Attempt counting and max attempts
    - Performance metrics tracking
    - Error handling and messages
    - Helper methods (mark_started, mark_completed, mark_failed)
    """

    def setUp(self):
        """Set up test data"""
        if not BULLET_MODELS_AVAILABLE:
            self.skipTest("BulletGenerationJob model not yet implemented (TDD Red phase)")

        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

        from artifacts.models import Artifact
        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Test Artifact',
            description='Test description',
            artifact_type='project'
        )

        self.job_desc = JobDescription.objects.create(
            content_hash='abc123',
            raw_content='Software Engineer at TechCorp'
        )

        self.cv_generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123',
            job_description=self.job_desc
        )

        self.job_context = {
            'role_title': 'Senior Software Engineer',
            'key_requirements': ['Python', 'Django', 'PostgreSQL'],
            'preferred_skills': ['Docker', 'AWS'],
            'seniority_level': 'senior'
        }

    def test_bullet_generation_job_creation(self):
        """Test basic job creation"""
        job = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            cv_generation=self.cv_generation,
            user=self.user,
            job_context=self.job_context
        )

        self.assertIsInstance(job.id, uuid.UUID)
        self.assertEqual(job.artifact, self.artifact)
        self.assertEqual(job.user, self.user)
        self.assertEqual(job.status, 'pending')  # Default status
        self.assertEqual(job.progress_percentage, 0)
        self.assertEqual(job.generation_attempts, 0)
        self.assertEqual(job.max_attempts, 3)  # Default

    def test_bullet_generation_job_status_transitions(self):
        """Test status transitions through job lifecycle"""
        job = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context
        )

        # Initial state
        self.assertEqual(job.status, 'pending')

        # Mark as started
        job.mark_started()
        job.refresh_from_db()
        self.assertEqual(job.status, 'processing')
        self.assertIsNotNone(job.started_at)

        # Mark as completed
        test_bullets = [
            {'text': 'A' * 80, 'type': 'achievement'},
            {'text': 'B' * 80, 'type': 'technical'},
            {'text': 'C' * 80, 'type': 'impact'}
        ]
        test_validation = {
            'is_valid': True,
            'overall_quality_score': 0.87
        }
        job.mark_completed(test_bullets, test_validation)
        job.refresh_from_db()

        self.assertEqual(job.status, 'completed')
        self.assertEqual(job.progress_percentage, 100)
        self.assertIsNotNone(job.completed_at)
        self.assertEqual(len(job.generated_bullets), 3)
        self.assertEqual(job.validation_results['is_valid'], True)

    def test_bullet_generation_job_mark_failed(self):
        """Test marking job as failed"""
        job = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context
        )

        job.mark_started()

        # Mark as failed
        error_msg = "LLM API rate limit exceeded"
        error_trace = "Traceback: ..."
        job.mark_failed(error_msg, error_trace)
        job.refresh_from_db()

        self.assertEqual(job.status, 'failed')
        self.assertEqual(job.error_message, error_msg)
        self.assertEqual(job.error_traceback, error_trace)
        self.assertIsNotNone(job.completed_at)

    def test_bullet_generation_job_attempt_counting(self):
        """Test generation attempt counting"""
        job = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context
        )

        self.assertEqual(job.generation_attempts, 0)

        # Increment attempt
        job.increment_attempt()
        job.refresh_from_db()
        self.assertEqual(job.generation_attempts, 1)
        self.assertEqual(job.status, 'pending')  # Still pending after 1 attempt

        # Increment to 2
        job.increment_attempt()
        job.refresh_from_db()
        self.assertEqual(job.generation_attempts, 2)

        # Increment to 3 (max attempts)
        job.increment_attempt()
        job.refresh_from_db()
        self.assertEqual(job.generation_attempts, 3)
        self.assertEqual(job.status, 'needs_review')  # Status changes after max attempts

    def test_bullet_generation_job_performance_metrics(self):
        """Test performance metrics tracking"""
        job = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context
        )

        job.mark_started()

        # Complete with metrics
        from decimal import Decimal
        test_bullets = [{'text': 'A' * 80}] * 3
        test_validation = {'is_valid': True}

        job.mark_completed(test_bullets, test_validation)
        job.processing_duration_ms = 8500
        job.llm_cost_usd = Decimal('0.0234')
        job.tokens_used = 450
        job.save()

        job.refresh_from_db()

        self.assertEqual(job.processing_duration_ms, 8500)
        self.assertEqual(job.llm_cost_usd, Decimal('0.0234'))
        self.assertEqual(job.tokens_used, 450)

    def test_bullet_generation_job_string_representation(self):
        """Test __str__ method"""
        job = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context
        )

        expected = f"BulletGenJob {job.id} for {self.artifact.title} (pending)"
        self.assertEqual(str(job), expected)

    def test_bullet_generation_job_ordering(self):
        """Test jobs are ordered by created_at (most recent first)"""
        job1 = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context
        )
        job2 = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context
        )

        jobs = BulletGenerationJob.objects.all()
        self.assertEqual(jobs[0], job2)  # Most recent first
        self.assertEqual(jobs[1], job1)

    def test_bullet_generation_job_processing_duration_calculation(self):
        """Test processing duration is calculated from started_at to completed_at"""
        job = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context
        )

        job.mark_started()

        # Simulate some processing time
        import time
        time.sleep(0.1)  # 100ms

        test_bullets = [{'text': 'A' * 80}] * 3
        test_validation = {'is_valid': True}
        job.mark_completed(test_bullets, test_validation)

        job.refresh_from_db()

        # Duration should be calculated
        self.assertIsNotNone(job.processing_duration_ms)
        self.assertGreater(job.processing_duration_ms, 0)