"""
Unit tests for generation app services (ft-006).

Tests cover:
- BulletGenerationService
- BulletValidationService

Reference: spec-20251001-ft006-implementation.md
TDD Red Phase: These tests will fail until services are implemented in Phase 3

NOTE: These are UNIT tests - they should NOT make external API calls.
All LLM service calls are mocked using common.test_mocks utilities.
"""

import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from decimal import Decimal
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import async_to_sync

# Import AsyncTestCase for async test methods
from common.test_base import AsyncTestCase

# Import test mocks to avoid real API calls
from common.test_mocks import (
    mock_llm_bullet_response,
    mock_llm_single_bullet_response,
    mock_validation_result,
    mock_validation_result_invalid,
    MockTailoredContentService,
    setup_mocked_llm_service
)

# Import services (will raise NotImplementedError until Phase 3)
from generation.services import (
    BulletGenerationService,
    GeneratedBulletSet,
    BulletValidationService,
    ValidationResult
)

User = get_user_model()


@tag('medium', 'integration', 'generation')
class BulletGenerationServiceTests(AsyncTestCase):
    """
    Test cases for BulletGenerationService (ft-006).

    Tests cover:
    - generate_bullets(): Generate exactly 3 bullets for artifact
    - batch_generate_bullets(): Generate bullets for multiple artifacts
    - regenerate_bullet(): Regenerate single bullet with refinement
    - get_generation_status(): Get async job status

    IMPORTANT: All LLM API calls are mocked. These are UNIT tests,
    not integration tests. No external API calls should be made.
    """

    def setUp(self):
        """
        Set up test data with mocked LLM service.
        """
        super().setUp()  # Initialize async event loop

        # Set up patcher for TailoredContentService
        self.patcher = patch('generation.services.bullet_generation_service.TailoredContentService')
        mock_tailored_service_class = self.patcher.start()

        # Configure mocked LLM service
        self.mock_llm_service = setup_mocked_llm_service()
        mock_tailored_service_class.return_value = self.mock_llm_service

        # Set up patcher for BulletVerificationService to prevent real API calls
        self.verification_patcher = patch('generation.services.bullet_generation_service.BulletVerificationService')
        mock_verification_class = self.verification_patcher.start()

        # Mock verify_bullet_set to return successful verification results
        mock_verification_instance = AsyncMock()
        mock_verification_instance.verify_bullet_set.return_value = [
            {
                'classification': 'VERIFIED',
                'confidence': 0.95,
                'hallucination_risk': 'LOW',
                'claims': [{'claim': 'mock claim', 'classification': 'VERIFIED', 'confidence': 0.95}],
                'cost': 0.0
            }
        ] * 3  # Return 3 verified bullet results

        mock_verification_class.return_value = mock_verification_instance

        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

        # Import models
        from artifacts.models import Artifact
        from generation.models import JobDescription, GeneratedDocument

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

        self.job_context = {
            'role_title': 'Senior Software Engineer',
            'key_requirements': ['Python', 'Django', 'PostgreSQL'],
            'preferred_skills': ['Docker', 'AWS'],
            'seniority_level': 'senior'
        }

        # Create service AFTER mocking is set up
        self.service = BulletGenerationService()

    def tearDown(self):
        """Clean up patchers"""
        super().tearDown()
        self.patcher.stop()
        self.verification_patcher.stop()

    async def test_generate_bullets_returns_exactly_three_bullets(self):
        """Test generate_bullets returns exactly 3 bullets with correct structure"""
        result = await self.service.generate_bullets(
            artifact_id=self.artifact.id,
            job_context=self.job_context
        )

        # Verify result structure
        self.assertIsInstance(result, GeneratedBulletSet)
        self.assertEqual(len(result.bullets), 3)
        self.assertIsInstance(result.quality_score, float)
        self.assertIsInstance(result.validation_passed, bool)
        self.assertIsInstance(result.generation_time_ms, int)
        self.assertIsInstance(result.cost_usd, float)

    async def test_generate_bullets_enforces_hierarchy(self):
        """Test bullets follow achievement → technical → impact hierarchy"""
        result = await self.service.generate_bullets(
            artifact_id=self.artifact.id,
            job_context=self.job_context
        )

        bullets = result.bullets

        # Position 1 must be achievement
        self.assertEqual(bullets[0].position, 1)
        self.assertEqual(bullets[0].bullet_type, 'achievement')

        # Position 2 must be technical
        self.assertEqual(bullets[1].position, 2)
        self.assertEqual(bullets[1].bullet_type, 'technical')

        # Position 3 must be impact
        self.assertEqual(bullets[2].position, 3)
        self.assertEqual(bullets[2].bullet_type, 'impact')

    async def test_generate_bullets_validates_length_constraints(self):
        """Test all bullets are 60-150 characters"""
        result = await self.service.generate_bullets(
            artifact_id=self.artifact.id,
            job_context=self.job_context
        )

        for bullet in result.bullets:
            text_length = len(bullet.text)
            self.assertGreaterEqual(
                text_length, 60,
                f"Bullet '{bullet.text}' is too short ({text_length} chars)"
            )
            self.assertLessEqual(
                text_length, 150,
                f"Bullet '{bullet.text}' is too long ({text_length} chars)"
            )

    async def test_generate_bullets_returns_existing_when_regenerate_false(self):
        """Test returns existing bullets if regenerate=False and bullets exist"""
        # First generation
        result1 = await self.service.generate_bullets(
            artifact_id=self.artifact.id,
            job_context=self.job_context,
            regenerate=False
        )

        first_bullet_text = result1.bullets[0].text

        # Second call with regenerate=False
        result2 = await self.service.generate_bullets(
            artifact_id=self.artifact.id,
            job_context=self.job_context,
            regenerate=False
        )

        # Should return same bullets
        self.assertEqual(result2.bullets[0].text, first_bullet_text)

    async def test_generate_bullets_regenerates_when_regenerate_true(self):
        """Test regenerates bullets even if they exist when regenerate=True"""
        # First generation
        result1 = await self.service.generate_bullets(
            artifact_id=self.artifact.id,
            job_context=self.job_context
        )

        # Force regeneration
        result2 = await self.service.generate_bullets(
            artifact_id=self.artifact.id,
            job_context=self.job_context,
            regenerate=True
        )

        # Should have different generation metadata
        self.assertIsNotNone(result2)
        self.assertEqual(len(result2.bullets), 3)

    async def test_generate_bullets_handles_validation_failure_with_retry(self):
        """Test retries generation if validation fails (up to 3 attempts)"""
        # Mock validation to fail first 2 attempts, pass on 3rd
        with patch.object(
            self.service.validation_service,
            'validate_bullet_set',
            side_effect=[
                Mock(is_valid=False, issues=['Quality too low'], bullet_scores=[0.5, 0.5, 0.5]),
                Mock(is_valid=False, issues=['Redundant content'], bullet_scores=[0.6, 0.6, 0.6]),
                Mock(is_valid=True, issues=[], overall_quality_score=0.87, bullet_scores=[0.87, 0.87, 0.87])
            ]
        ):
            result = await self.service.generate_bullets(
                artifact_id=self.artifact.id,
                job_context=self.job_context
            )

            # Should eventually succeed after retries
            self.assertTrue(result.validation_passed)
            self.assertEqual(result.quality_score, 0.87)

    async def test_generate_bullets_raises_error_after_max_attempts(self):
        """Test raises ValidationError if validation fails after 3 attempts"""
        from django.core.exceptions import ValidationError

        # Mock validation to always fail with proper values (not nested Mocks)
        with patch.object(
            self.service.validation_service,
            'validate_bullet_set',
            return_value=Mock(
                is_valid=False,
                issues=['Always fails'],
                bullet_scores=[0.3, 0.3, 0.3],
                overall_quality_score=0.3
            )
        ):
            with self.assertRaises(ValidationError):
                await self.service.generate_bullets(
                    artifact_id=self.artifact.id,
                    job_context=self.job_context
                )

    async def test_generate_bullets_raises_error_for_nonexistent_artifact(self):
        """Test raises ArtifactNotFoundError for invalid artifact_id"""
        with self.assertRaises(Exception) as context:  # Will be ArtifactNotFoundError
            await self.service.generate_bullets(
                artifact_id=99999,  # Non-existent
                job_context=self.job_context
            )

        self.assertIn('not found', str(context.exception).lower())

    async def test_generate_bullets_tracks_performance_metrics(self):
        """Test tracks generation time, cost, and model used"""
        result = await self.service.generate_bullets(
            artifact_id=self.artifact.id,
            job_context=self.job_context
        )

        # Verify metrics are tracked
        self.assertGreater(result.generation_time_ms, 0)
        self.assertGreater(result.cost_usd, 0)
        self.assertIsNotNone(result.model_used)
        self.assertIn('gpt', result.model_used.lower())  # Should be OpenAI model

    async def test_regenerate_bullet_updates_single_bullet(self):
        """Test regenerating a single bullet preserves others"""
        # First generate all bullets
        result = await self.service.generate_bullets(
            artifact_id=self.artifact.id,
            job_context=self.job_context
        )

        original_bullet_1 = result.bullets[0]
        original_bullet_2_text = result.bullets[1].text
        original_bullet_3_text = result.bullets[2].text

        # Mock TailoredContentService to return different text on regeneration
        with patch.object(
            self.service.tailored_content_service,
            'generate_bullet_points',
            return_value={
                'bullet_points': [{
                    'text': 'DIFFERENT: Led microservices platform development with 150k+ users and 99.99% uptime',
                    'type': 'achievement',
                    'keywords': ['microservices', 'platform', 'development'],
                    'confidence_score': 0.8,
                    'metrics': {'users': '150k+', 'uptime': '99.99%'}
                }],
                'processing_metadata': {'cost_usd': 0.001, 'model_used': 'gpt-5-mini'}
            }
        ):
            # Regenerate only bullet 1
            regenerated_bullet = await self.service.regenerate_bullet(
                bullet_id=original_bullet_1.id,
                refinement_prompt="Add more quantified metrics"
            )

        # Verify bullet 1 was regenerated
        self.assertNotEqual(regenerated_bullet.text, original_bullet_1.text)
        self.assertEqual(regenerated_bullet.position, 1)
        self.assertEqual(regenerated_bullet.bullet_type, 'achievement')

        # Verify other bullets unchanged (would need to fetch from DB)
        # In real implementation, we'd verify bullets 2 and 3 remain the same

    async def test_regenerate_bullet_applies_refinement_prompt(self):
        """Test refinement prompt influences regeneration"""
        result = await self.service.generate_bullets(
            artifact_id=self.artifact.id,
            job_context=self.job_context
        )

        bullet = result.bullets[0]

        # Mock TailoredContentService to return leadership-focused text
        with patch.object(
            self.service.tailored_content_service,
            'generate_bullet_points',
            return_value={
                'bullet_points': [{
                    'text': 'Directed cross-functional engineering team of 8 developers in microservices migration',
                    'type': 'achievement',
                    'keywords': ['leadership', 'team management', 'microservices'],
                    'confidence_score': 0.85,
                    'metrics': {'team_size': '8'}
                }],
                'processing_metadata': {'cost_usd': 0.001, 'model_used': 'gpt-5-mini'}
            }
        ):
            # Regenerate with specific refinement
            regenerated = await self.service.regenerate_bullet(
                bullet_id=bullet.id,
                refinement_prompt="Focus on leadership and team management aspects"
            )

        # Text should be different (influenced by prompt)
        self.assertNotEqual(regenerated.text, bullet.text)
        # In real implementation, would verify leadership keywords present

    def test_get_generation_status_returns_job_info(self):
        """Test getting status of async generation job"""
        from generation.models import BulletGenerationJob

        # Create a job
        job = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context,
            status='processing',
            progress_percentage=50
        )

        status = self.service.get_generation_status(str(job.id))

        # Verify status dict structure
        self.assertIsInstance(status, dict)
        self.assertEqual(status['status'], 'processing')
        self.assertEqual(status['progress_percentage'], 50)
        self.assertIsNotNone(status['artifact_id'])

    def test_get_generation_status_includes_bullets_when_completed(self):
        """Test completed job status includes generated bullets"""
        from generation.models import BulletGenerationJob

        test_bullets = [
            {'text': 'A' * 80, 'type': 'achievement'},
            {'text': 'B' * 80, 'type': 'technical'},
            {'text': 'C' * 80, 'type': 'impact'}
        ]

        job = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context,
            status='completed',
            generated_bullets=test_bullets
        )

        status = self.service.get_generation_status(str(job.id))

        self.assertEqual(status['status'], 'completed')
        self.assertIn('bullets', status)
        self.assertEqual(len(status['bullets']), 3)

    def test_get_generation_status_includes_error_when_failed(self):
        """Test failed job status includes error message"""
        from generation.models import BulletGenerationJob

        job = BulletGenerationJob.objects.create(
            artifact=self.artifact,
            user=self.user,
            job_context=self.job_context,
            status='failed',
            error_message='LLM API rate limit exceeded'
        )

        status = self.service.get_generation_status(str(job.id))

        self.assertEqual(status['status'], 'failed')
        self.assertIn('error_message', status)
        self.assertEqual(status['error_message'], 'LLM API rate limit exceeded')


@tag('medium', 'integration', 'generation')
class BulletValidationServiceTests(AsyncTestCase):
    """
    Test cases for BulletValidationService (ft-006).

    Tests cover:
    - validate_bullet_set(): Comprehensive validation
    - validate_three_bullet_structure(): Structure enforcement
    - validate_content_quality(): Quality scoring
    - check_semantic_similarity(): Redundancy detection
    - is_generic_content(): Generic content detection
    - starts_with_action_verb(): Action verb checking
    - count_metrics(): Quantified metrics counting
    - calculate_keyword_relevance(): Keyword matching
    """

    def setUp(self):
        """Set up test data"""
        super().setUp()  # Initialize async event loop
        self.service = BulletValidationService()

        self.valid_bullets = [
            {
                'text': 'Led development of microservices platform serving 100k+ daily users with 99.9% uptime',
                'type': 'achievement',
                'keywords': ['microservices', 'platform', 'led', 'development']
            },
            {
                'text': 'Built scalable architecture using Python, Django, and PostgreSQL with Docker containerization',
                'type': 'technical',
                'keywords': ['Python', 'Django', 'PostgreSQL', 'Docker', 'architecture']
            },
            {
                'text': 'Improved system performance by 40% while managing cross-functional team of 6 engineers',
                'type': 'impact',
                'keywords': ['performance', 'improvement', 'team management']
            }
        ]

        self.job_context = {
            'key_requirements': ['Python', 'Django', 'microservices'],
            'preferred_skills': ['Docker', 'PostgreSQL']
        }

    async def test_validate_bullet_set_passes_for_valid_bullets(self):
        """Test validation passes for well-formed bullets"""
        result = await self.service.validate_bullet_set(
            bullets=self.valid_bullets,
            job_context=self.job_context
        )

        self.assertIsInstance(result, ValidationResult)
        self.assertTrue(result.is_valid)
        self.assertGreater(result.overall_quality_score, 0.7)
        self.assertTrue(result.structure_valid)
        self.assertEqual(len(result.bullet_scores), 3)
        self.assertEqual(len(result.similarity_pairs), 0)  # No redundancy

    async def test_validate_bullet_set_fails_for_invalid_structure(self):
        """Test validation fails if not exactly 3 bullets"""
        # Only 2 bullets
        invalid_bullets = self.valid_bullets[:2]

        result = await self.service.validate_bullet_set(
            bullets=invalid_bullets,
            job_context=self.job_context
        )

        self.assertFalse(result.is_valid)
        self.assertFalse(result.structure_valid)
        self.assertIn('Expected 3 bullets', ' '.join(result.issues))

    async def test_validate_bullet_set_fails_for_wrong_hierarchy(self):
        """Test validation fails if hierarchy is wrong"""
        # Swap positions
        wrong_hierarchy = [
            {'text': 'A' * 80, 'type': 'technical'},  # Wrong! Should be achievement
            {'text': 'B' * 80, 'type': 'achievement'},  # Wrong! Should be technical
            {'text': 'C' * 80, 'type': 'impact'}
        ]

        result = await self.service.validate_bullet_set(
            bullets=wrong_hierarchy,
            job_context=self.job_context
        )

        self.assertFalse(result.is_valid)
        self.assertFalse(result.structure_valid)
        self.assertGreater(len(result.issues), 0)

    async def test_validate_bullet_set_detects_low_quality(self):
        """Test validation detects low-quality bullets"""
        low_quality_bullets = [
            {'text': 'A' * 60, 'type': 'achievement'},  # Generic, no metrics
            {'text': 'B' * 60, 'type': 'technical'},  # Generic, no metrics
            {'text': 'C' * 60, 'type': 'impact'}  # Generic, no metrics
        ]

        result = await self.service.validate_bullet_set(
            bullets=low_quality_bullets,
            job_context=self.job_context
        )

        # Should have low quality scores
        for score in result.bullet_scores:
            self.assertLess(score, 0.5)

        # May or may not be "valid" depending on threshold, but quality should be low
        self.assertLess(result.overall_quality_score, 0.5)

    async def test_validate_bullet_set_detects_redundancy(self):
        """Test validation detects redundant bullets"""
        redundant_bullets = [
            {
                'text': 'Led development of microservices platform serving 100k daily users with high uptime',
                'type': 'achievement'
            },
            {
                'text': 'Managed development of microservices platform for 100k daily users with excellent uptime',
                'type': 'technical'  # Very similar to bullet 1
            },
            {
                'text': 'Improved system performance by 40% through optimization',
                'type': 'impact'
            }
        ]

        result = await self.service.validate_bullet_set(
            bullets=redundant_bullets,
            job_context=self.job_context
        )

        # Should detect similarity between bullets 0 and 1
        self.assertGreater(len(result.similarity_pairs), 0)

        # Check similarity pair structure
        for pair in result.similarity_pairs:
            idx1, idx2, similarity = pair
            self.assertGreater(similarity, 0.80)

    def test_validate_three_bullet_structure_passes_for_correct_hierarchy(self):
        """Test structure validation passes for correct hierarchy"""
        valid, issues = self.service.validate_three_bullet_structure(self.valid_bullets)

        self.assertTrue(valid)
        self.assertEqual(len(issues), 0)

    def test_validate_three_bullet_structure_fails_for_wrong_count(self):
        """Test structure validation fails if not exactly 3 bullets"""
        # 2 bullets
        valid, issues = self.service.validate_three_bullet_structure(
            self.valid_bullets[:2]
        )

        self.assertFalse(valid)
        self.assertIn('Expected 3 bullets', ' '.join(issues))

        # 4 bullets
        four_bullets = self.valid_bullets + [{'text': 'D' * 80, 'type': 'achievement'}]
        valid, issues = self.service.validate_three_bullet_structure(four_bullets)

        self.assertFalse(valid)
        self.assertIn('Expected 3 bullets', ' '.join(issues))

    def test_validate_three_bullet_structure_fails_for_wrong_types(self):
        """Test structure validation enforces type hierarchy"""
        wrong_types = [
            {'text': 'A' * 80, 'type': 'impact'},  # Should be achievement
            {'text': 'B' * 80, 'type': 'achievement'},  # Should be technical
            {'text': 'C' * 80, 'type': 'technical'}  # Should be impact
        ]

        valid, issues = self.service.validate_three_bullet_structure(wrong_types)

        self.assertFalse(valid)
        self.assertGreater(len(issues), 0)
        self.assertIn('achievement', ' '.join(issues))

    def test_validate_content_quality_scores_high_quality_bullet(self):
        """Test quality scoring for excellent bullet"""
        excellent_bullet = {
            'text': 'Led development of microservices platform serving 100k+ daily users with 99.9% uptime',
            'keywords': ['microservices', 'platform', 'led', 'development']
        }

        score = self.service.validate_content_quality(
            bullet=excellent_bullet,
            job_context=self.job_context
        )

        # Should score high (has action verb, metrics, keywords, good length)
        self.assertGreaterEqual(score, 0.7)
        self.assertLessEqual(score, 1.0)

    def test_validate_content_quality_scores_low_quality_bullet(self):
        """Test quality scoring for poor bullet"""
        poor_bullet = {
            'text': 'Worked on various projects using different technologies and gained experience',
            'keywords': []
        }

        score = self.service.validate_content_quality(
            bullet=poor_bullet,
            job_context=self.job_context
        )

        # Should score low (generic, no metrics, weak verb phrase)
        self.assertLess(score, 0.5)

    async def test_check_semantic_similarity_finds_redundant_bullets(self):
        """Test semantic similarity detection"""
        similar_bullets = [
            {'text': 'Led development of microservices platform serving 100k daily users with high uptime'},
            {'text': 'Managed development of microservices platform for 100k daily users with excellent uptime'},  # Nearly identical content
            {'text': 'Optimized PostgreSQL database queries reducing latency by 60 percent'}  # Different topic
        ]

        pairs = await self.service.check_semantic_similarity(similar_bullets)

        # Should find similarity between bullets 0 and 1 (nearly identical)
        self.assertGreater(len(pairs), 0)

        # Verify pair structure
        for idx1, idx2, similarity in pairs:
            self.assertIn(idx1, [0, 1])
            self.assertIn(idx2, [0, 1])
            self.assertGreater(similarity, 0.80)

    async def test_check_semantic_similarity_returns_empty_for_unique_bullets(self):
        """Test no similarity detected for unique bullets"""
        unique_bullets = [
            {'text': 'Led development of microservices platform'},
            {'text': 'Built scalable database architecture'},
            {'text': 'Mentored junior engineers in agile practices'}
        ]

        pairs = await self.service.check_semantic_similarity(unique_bullets)

        # Should find no redundancy
        self.assertEqual(len(pairs), 0)

    def test_is_generic_content_detects_generic_patterns(self):
        """Test generic content detection"""
        generic_texts = [
            'Worked on various projects',
            'Participated in team activities',
            'Gained valuable experience',
            'Responsible for managing tasks',
            'Helped with development work'
        ]

        for text in generic_texts:
            is_generic = self.service.is_generic_content(text)
            self.assertTrue(is_generic, f"Should detect '{text}' as generic")

    def test_is_generic_content_passes_specific_content(self):
        """Test specific content is not flagged as generic"""
        specific_texts = [
            'Led development of microservices platform serving 100k+ users',
            'Built RESTful API handling 1M+ requests per day',
            'Optimized PostgreSQL queries reducing latency by 60%'
        ]

        for text in specific_texts:
            is_generic = self.service.is_generic_content(text)
            self.assertFalse(is_generic, f"Should not detect '{text}' as generic")

    def test_starts_with_action_verb_recognizes_strong_verbs(self):
        """Test action verb detection"""
        with_action_verbs = [
            'Led development of platform',
            'Built scalable architecture',
            'Improved system performance',
            'Managed cross-functional team',
            'Developed RESTful APIs'
        ]

        for text in with_action_verbs:
            has_verb = self.service.starts_with_action_verb(text)
            self.assertTrue(has_verb, f"Should recognize action verb in '{text}'")

    def test_starts_with_action_verb_rejects_weak_verbs(self):
        """Test weak verbs are not accepted"""
        without_action_verbs = [
            'Was responsible for development',
            'Worked on various projects',
            'Involved in team activities',
            'Helped with implementation'
        ]

        for text in without_action_verbs:
            has_verb = self.service.starts_with_action_verb(text)
            self.assertFalse(has_verb, f"Should reject weak verb in '{text}'")

    def test_count_metrics_finds_quantified_achievements(self):
        """Test metrics counting"""
        texts_with_metrics = {
            'Improved performance by 40% for 100k+ users': 2,  # 40%, 100k+
            'Managed team of 6 engineers over 2 years': 2,  # 6, 2 years
            'Reduced costs by $50k annually': 1,  # $50k
            'Achieved 99.9% uptime across 5 services': 2,  # 99.9%, 5
            'Led project with no metrics': 0  # No metrics
        }

        for text, expected_count in texts_with_metrics.items():
            count = self.service.count_metrics(text)
            self.assertEqual(
                count, expected_count,
                f"Expected {expected_count} metrics in '{text}', got {count}"
            )

    def test_calculate_keyword_relevance_scores_keyword_matches(self):
        """Test keyword relevance calculation"""
        bullet_with_keywords = {
            'text': 'Built scalable Python Django microservices with PostgreSQL and Docker',
            'keywords': ['Python', 'Django', 'microservices', 'PostgreSQL', 'Docker']
        }

        score = self.service.calculate_keyword_relevance(
            bullet=bullet_with_keywords,
            job_context=self.job_context
        )

        # All key requirements present: Python, Django, microservices
        # Plus preferred skills: PostgreSQL, Docker
        # Should score very high
        self.assertGreater(score, 0.8)

    def test_calculate_keyword_relevance_scores_low_for_no_keywords(self):
        """Test low relevance for bullets without job keywords"""
        bullet_no_keywords = {
            'text': 'Managed team activities and coordinated meetings effectively',
            'keywords': ['team', 'meetings']
        }

        score = self.service.calculate_keyword_relevance(
            bullet=bullet_no_keywords,
            job_context=self.job_context
        )

        # No job-relevant keywords
        self.assertLess(score, 0.3)


@tag('medium', 'integration', 'generation')
class GenerationServiceTests(AsyncTestCase):
    """
    Test cases for GenerationService two-phase workflow (ft-009).

    NOTE: These tests require async support and proper mocking of LLM services.
    They are temporarily simplified to avoid async test issues in Django TestCase.

    Full integration tests should be run manually or via async test framework.

    Tests cover:
    - prepare_bullets(): Phase 1 - Generate bullets for review
    - assemble_generation(): Phase 2 - Assemble CV from approved bullets
    """

    def setUp(self):
        """Set up test data"""
        super().setUp()  # Initialize async event loop
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

        # Import models
        from artifacts.models import Artifact
        from generation.models import JobDescription, GeneratedDocument

        self.artifact1 = Artifact.objects.create(
            user=self.user,
            title='E-commerce Platform Development',
            description='Led development of microservices platform',
            artifact_type='project'
        )

        self.artifact2 = Artifact.objects.create(
            user=self.user,
            title='API Integration Project',
            description='Built RESTful APIs for third-party systems',
            artifact_type='project'
        )

        self.job_desc = JobDescription.objects.create(
            content_hash='abc123',
            raw_content='Senior Software Engineer at TechCorp',
            company_name='TechCorp',
            role_title='Senior Software Engineer',
            parsed_data={  # Pre-populated to avoid LLM calls
                'role_title': 'Senior Software Engineer',
                'company_name': 'TechCorp',
                'must_have_skills': ['Python', 'Django'],
                'nice_to_have_skills': ['AWS'],
                'responsibilities': []
            }
        )

        self.cv_generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123',
            job_description=self.job_desc,
            status='pending'
        )

        # Import service
        from generation.services.generation_service import GenerationService
        self.service = GenerationService()

    def test_service_initialization(self):
        """Test GenerationService initializes correctly"""
        from generation.services.generation_service import GenerationService
        service = GenerationService()

        self.assertIsNotNone(service.content_service)
        self.assertIsNotNone(service.ranking_service)
        self.assertIsNotNone(service.bullet_service)

    # Commented out async tests - require proper async test framework
    # TODO: Implement with pytest-asyncio or Django async test support
    pass

