"""
Unit tests for LLM services models.
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from unittest.mock import patch

from llm_services.models import (
    ModelPerformanceMetric,
    EnhancedEvidence,
    ModelCostTracking,
    CircuitBreakerState
    # NOTE (ft-007): ArtifactChunk, JobDescriptionEmbedding removed - embeddings infrastructure deleted
)

User = get_user_model()


@tag('fast', 'unit', 'llm_services')
class ModelPerformanceMetricTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_performance_metric(self):
        """Test creating a performance metric"""
        metric = ModelPerformanceMetric.objects.create(
            model_name='gpt-5',
            task_type='cv_generation',
            processing_time_ms=1500,
            tokens_used=800,
            cost_usd=Decimal('0.008'),
            quality_score=Decimal('0.85'),
            success=True,
            complexity_score=Decimal('0.6'),
            user=self.user
        )

        self.assertEqual(metric.model_name, 'gpt-5')
        self.assertEqual(metric.task_type, 'cv_generation')
        self.assertEqual(metric.processing_time_ms, 1500)
        self.assertEqual(metric.tokens_used, 800)
        self.assertEqual(metric.cost_usd, Decimal('0.008'))
        self.assertEqual(metric.quality_score, Decimal('0.85'))
        self.assertTrue(metric.success)
        self.assertEqual(metric.user, self.user)
        self.assertTrue(isinstance(metric.id, uuid.UUID))

    def test_performance_metric_validation(self):
        """Test validation constraints"""
        # Test invalid quality score
        with self.assertRaises(ValidationError):
            metric = ModelPerformanceMetric(
                model_name='gpt-5',
                task_type='cv_generation',
                processing_time_ms=1500,
                tokens_used=800,
                cost_usd=Decimal('0.008'),
                quality_score=Decimal('1.5'),  # Invalid: > 1.0
                user=self.user
            )
            metric.full_clean()

        # Test invalid complexity score
        with self.assertRaises(ValidationError):
            metric = ModelPerformanceMetric(
                model_name='gpt-5',
                task_type='cv_generation',
                processing_time_ms=1500,
                tokens_used=800,
                cost_usd=Decimal('0.008'),
                complexity_score=Decimal('-0.1'),  # Invalid: < 0.0
                user=self.user
            )
            metric.full_clean()

    def test_performance_metric_str_representation(self):
        """Test string representation"""
        metric = ModelPerformanceMetric.objects.create(
            model_name='gpt-5',
            task_type='cv_generation',
            processing_time_ms=1500,
            cost_usd=Decimal('0.008'),
            user=self.user
        )
        # The actual __str__ method returns the full created_at timestamp
        self.assertIn("gpt-5 - cv_generation", str(metric))
        self.assertIn(str(metric.created_at.date()), str(metric))


@tag('fast', 'unit', 'llm_services')
class EnhancedEvidenceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_enhanced_artifact(self):
        """Test creating an enhanced artifact (ft-007: enrichment-only, no embeddings)"""
        artifact = EnhancedEvidence.objects.create(
            user=self.user,
            title='Test Resume',
            content_type='pdf',
            raw_content='Raw resume content...',
            processed_content={'sections': ['education', 'experience']},
            processing_confidence=0.85
        )

        self.assertEqual(artifact.title, 'Test Resume')
        self.assertEqual(artifact.content_type, 'pdf')
        self.assertEqual(artifact.user, self.user)
        self.assertEqual(artifact.processing_confidence, 0.85)
        self.assertTrue(isinstance(artifact.id, uuid.UUID))

    def test_enhanced_artifact_str_representation(self):
        """Test string representation (ft-007: enrichment-only, no embeddings)"""
        artifact = EnhancedEvidence.objects.create(
            user=self.user,
            title='My Portfolio',
            content_type='github',
            raw_content='Portfolio content...',
            processing_confidence=0.90
        )
        # The actual __str__ includes Evidence ID - but this test creates without evidence so it's None
        expected = "My Portfolio (github) - Evidence #None"
        self.assertEqual(str(artifact), expected)


# NOTE (ft-007): ArtifactChunk tests removed - model deleted in embeddings removal
# @tag('fast', 'unit', 'llm_services')
# class ArtifactChunkTestCase(TestCase):
#     def setUp(self):
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com',
#             password='testpass123'
#         )
#         self.enhanced_evidence = EnhancedEvidence.objects.create(
#             user=self.user,
#             title='Test Artifact',
#             content_type='text',
#             raw_content='Test content...',
#             content_embedding=[0.0] * 1536,
#             summary_embedding=[0.0] * 1536
#         )
#
#     def test_create_artifact_chunk(self):
#         """Test creating an artifact chunk"""
#         chunk = ArtifactChunk.objects.create(
#             enhanced_evidence=self.enhanced_evidence,
#             chunk_index=0,
#             content='First chunk of content...',
#             content_hash='abc123def456',
#             tokens_used=50,
#             processing_cost_usd=Decimal('0.0001'),
#             embedding_vector=[0.0] * 1536
#         )
#
#         self.assertEqual(chunk.enhanced_evidence, self.enhanced_evidence)
#         self.assertEqual(chunk.chunk_index, 0)
#         self.assertEqual(chunk.content, 'First chunk of content...')
#         self.assertEqual(chunk.tokens_used, 50)
#
#     def test_chunk_unique_constraint(self):
#         """Test unique constraint on enhanced_evidence + chunk_index"""
#         ArtifactChunk.objects.create(
#             enhanced_evidence=self.enhanced_evidence,
#             chunk_index=0,
#             content='First chunk...',
#             content_hash='abc123',
#             embedding_vector=[0.0] * 1536
#         )
#
#         # Try to create another chunk with same enhanced_evidence and index
#         with self.assertRaises(IntegrityError):
#             ArtifactChunk.objects.create(
#                 enhanced_evidence=self.enhanced_evidence,
#                 chunk_index=0,  # Same index
#                 content='Duplicate chunk...',
#                 content_hash='def456',
#                 embedding_vector=[0.0] * 1536
#             )
#
#     def test_chunk_str_representation(self):
#         """Test string representation"""
#         chunk = ArtifactChunk.objects.create(
#             enhanced_evidence=self.enhanced_evidence,
#             chunk_index=2,
#             content='Chunk content...',
#             content_hash='abc123',
#             embedding_vector=[0.0] * 1536
#         )
#         # Update expected based on actual __str__ method: "{enhanced_evidence.title} - Chunk {chunk_index}"
#         expected = "Test Artifact - Chunk 2"
#         self.assertEqual(str(chunk), expected)


# NOTE (ft-007): JobDescriptionEmbedding tests removed - model deleted in embeddings removal
# @tag('fast', 'unit', 'llm_services')
# class JobDescriptionEmbeddingTestCase(TestCase):
#     def setUp(self):
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com',
#             password='testpass123'
#         )
#
#     def test_create_job_embedding(self):
#         """Test creating a job description embedding"""
#         embedding = JobDescriptionEmbedding.objects.create(
#             user=self.user,
#             job_description_hash='abc123def456',
#             company_name='Tech Corp',
#             role_title='Senior Developer',
#             tokens_used=200,
#             cost_usd=Decimal('0.0002'),
#             embedding_vector=[0.0] * 1536
#         )
#
#         self.assertEqual(embedding.company_name, 'Tech Corp')
#         self.assertEqual(embedding.role_title, 'Senior Developer')
#         self.assertEqual(embedding.tokens_used, 200)
#         self.assertEqual(embedding.access_count, 1)  # Default value
#
#     def test_job_embedding_unique_hash(self):
#         """Test unique constraint on job_description_hash"""
#         JobDescriptionEmbedding.objects.create(
#             user=self.user,
#             job_description_hash='unique_hash_123',
#             company_name='Tech Corp',
#             role_title='Developer',
#             embedding_vector=[0.0] * 1536
#         )
#
#         # Try to create another with same hash
#         with self.assertRaises(IntegrityError):
#             JobDescriptionEmbedding.objects.create(
#                 user=self.user,
#                 job_description_hash='unique_hash_123',  # Same hash
#                 company_name='Other Corp',
#                 role_title='Engineer',
#                 embedding_vector=[0.0] * 1536
#             )
#
#     def test_increment_access_count(self):
#         """Test incrementing access count"""
#         embedding = JobDescriptionEmbedding.objects.create(
#             user=self.user,
#             job_description_hash='test_hash',
#             company_name='Test Corp',
#             embedding_vector=[0.0] * 1536
#         )
#
#         # Simulate accessing the embedding
#         embedding.access_count += 1
#         embedding.last_accessed = timezone.now()
#         embedding.save()
#
#         embedding.refresh_from_db()
#         self.assertEqual(embedding.access_count, 2)
#
#     def test_job_embedding_str_representation(self):
#         """Test string representation"""
#         embedding = JobDescriptionEmbedding.objects.create(
#             user=self.user,
#             job_description_hash='test_hash',
#             company_name='Google',
#             role_title='Software Engineer',
#             embedding_vector=[0.0] * 1536
#         )
#         # The actual __str__ method shows: "Job Embedding: {role_title} at {company_name}"
#         expected = "Job Embedding: Software Engineer at Google"
#         self.assertEqual(str(embedding), expected)


@tag('fast', 'unit', 'llm_services')
class ModelCostTrackingTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_create_cost_tracking(self):
        """Test creating cost tracking entry"""
        cost_entry = ModelCostTracking.objects.create(
            user=self.user,
            date=timezone.now().date(),
            model_name='gpt-5',
            total_cost_usd=Decimal('0.150'),
            generation_count=15,
            avg_cost_per_generation=Decimal('0.010'),
            total_tokens_used=15000,
            avg_tokens_per_generation=1000
        )

        self.assertEqual(cost_entry.model_name, 'gpt-5')
        self.assertEqual(cost_entry.generation_count, 15)
        self.assertEqual(cost_entry.total_cost_usd, Decimal('0.150'))

    def test_cost_tracking_unique_constraint(self):
        """Test unique constraint on user + date + model_name"""
        today = timezone.now().date()

        ModelCostTracking.objects.create(
            user=self.user,
            date=today,
            model_name='gpt-5',
            total_cost_usd=Decimal('0.100'),
            generation_count=10,
            avg_cost_per_generation=Decimal('0.010')
        )

        # Try to create another entry for same user, date, model
        with self.assertRaises(IntegrityError):
            ModelCostTracking.objects.create(
                user=self.user,
                date=today,
                model_name='gpt-5',  # Same combination
                total_cost_usd=Decimal('0.200'),
                generation_count=20,
                avg_cost_per_generation=Decimal('0.010')
            )

    def test_cost_tracking_str_representation(self):
        """Test string representation"""
        cost_entry = ModelCostTracking.objects.create(
            user=self.user,
            date=timezone.now().date(),
            model_name='claude-sonnet-4',
            total_cost_usd=Decimal('0.250'),
            generation_count=8,
            avg_cost_per_generation=Decimal('0.03125')
        )
        # The actual __str__ method shows: "{user.email} - {model_name} - {date}"
        expected = f"{self.user.email} - claude-sonnet-4 - {cost_entry.date}"
        self.assertEqual(str(cost_entry), expected)


@tag('fast', 'unit', 'llm_services')
class CircuitBreakerStateTestCase(TestCase):
    def test_create_circuit_breaker(self):
        """Test creating circuit breaker state"""
        breaker = CircuitBreakerState.objects.create(
            model_name='test-create-breaker-model',
            failure_count=0,
            state='closed',
            failure_threshold=5,
            timeout_duration=30
        )

        self.assertEqual(breaker.model_name, 'test-create-breaker-model')
        self.assertEqual(breaker.failure_count, 0)
        self.assertEqual(breaker.state, 'closed')

    def test_circuit_breaker_state_choices(self):
        """Test valid state choices"""
        valid_states = ['closed', 'open', 'half_open']

        for state in valid_states:
            breaker = CircuitBreakerState.objects.create(
                model_name=f'test-model-{state}',
                state=state
            )
            self.assertEqual(breaker.state, state)

    def test_record_failure(self):
        """Test recording failure"""
        breaker = CircuitBreakerState.objects.create(
            model_name='test-model',
            failure_count=0,
            state='closed'
        )

        # Record failures
        breaker.record_failure()
        self.assertEqual(breaker.failure_count, 1)
        self.assertEqual(breaker.state, 'closed')  # Still closed
        self.assertIsNotNone(breaker.last_failure)

        # Record enough failures to open circuit
        for _ in range(4):  # Total will be 5 (default threshold)
            breaker.record_failure()

        self.assertEqual(breaker.failure_count, 5)
        self.assertEqual(breaker.state, 'open')

    def test_record_success(self):
        """Test recording success"""
        breaker = CircuitBreakerState.objects.create(
            model_name='test-model',
            failure_count=3,
            state='open'
        )

        breaker.record_success()

        self.assertEqual(breaker.failure_count, 0)
        self.assertEqual(breaker.state, 'closed')
        self.assertIsNone(breaker.last_failure)

    def test_can_attempt_request(self):
        """Test should_attempt_request logic"""
        breaker = CircuitBreakerState.objects.create(
            model_name='test-model',
            state='closed'
        )
        self.assertTrue(breaker.should_attempt_request())

        # Open circuit
        breaker.state = 'open'
        breaker.last_failure = timezone.now()
        breaker.save()
        self.assertFalse(breaker.should_attempt_request())

        # After timeout, should allow half-open
        breaker.last_failure = timezone.now() - timedelta(seconds=35)  # Past timeout
        breaker.save()
        self.assertTrue(breaker.should_attempt_request())

        # Should transition to half_open
        breaker.refresh_from_db()
        self.assertEqual(breaker.state, 'half_open')

    def test_circuit_breaker_str_representation(self):
        """Test string representation"""
        breaker = CircuitBreakerState.objects.create(
            model_name='test-string-repr-model',
            state='closed'
        )
        # The actual __str__ method shows: "{model_name} - {state} ({failure_count} failures)"
        expected = "test-string-repr-model - closed (0 failures)"
        self.assertEqual(str(breaker), expected)

    def test_circuit_breaker_unique_model_name(self):
        """Test unique constraint on model_name"""
        CircuitBreakerState.objects.create(
            model_name='unique-model',
            state='closed'
        )

        with self.assertRaises(IntegrityError):
            CircuitBreakerState.objects.create(
                model_name='unique-model',  # Duplicate
                state='open'
            )