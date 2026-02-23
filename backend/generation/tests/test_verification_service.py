"""
Unit tests for BulletVerificationService (ft-030 - Anti-Hallucination Improvements).
Tests LLM-based verification, claim extraction, classification, and aggregation.

Implements ADR-042: Verification Architecture
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from typing import Dict, List, Any

User = get_user_model()


@tag('medium', 'integration', 'generation', 'verification')
class BulletVerificationServiceTestCase(TestCase):
    """Test BulletVerificationService verification operations"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    @pytest.mark.asyncio
    async def test_verify_bullet_against_source_verified(self):
        """Test verification of a bullet with strong source support (VERIFIED)"""
        from generation.services.bullet_verification_service import BulletVerificationService

        service = BulletVerificationService()

        bullet = "Improved API response time by 40% through Redis caching"
        source_content = """
        Project: E-commerce Platform Optimization

        Implemented Redis caching layer for frequently accessed product data.
        This optimization reduced average API response time from 250ms to 150ms,
        representing a 40% improvement in response time.

        Technologies: Python, Redis, Django
        """

        # Mock LLM response for verification
        with patch.object(service.client_manager, 'make_completion_call') as mock_call:
            mock_call.return_value = AsyncMock(
                choices=[Mock(message=Mock(content="""{
                    "claims": [
                        {
                            "claim": "Improved API response time by 40%",
                            "classification": "VERIFIED",
                            "confidence": 0.95,
                            "evidence": "reduced average API response time from 250ms to 150ms, representing a 40% improvement",
                            "reasoning": "Source explicitly states 40% improvement with specific metrics"
                        },
                        {
                            "claim": "Used Redis caching",
                            "classification": "VERIFIED",
                            "confidence": 0.98,
                            "evidence": "Implemented Redis caching layer",
                            "reasoning": "Direct mention of Redis caching implementation"
                        }
                    ],
                    "overall_classification": "VERIFIED",
                    "overall_confidence": 0.96,
                    "hallucination_risk": "LOW"
                }"""))],
                usage=Mock(prompt_tokens=100, completion_tokens=150)
            )

            result = await service.verify_single_bullet(
                bullet=bullet,
                source_content=source_content,
                user_id=self.user.id
            )

        # Verify result structure
        assert 'classification' in result
        assert result['classification'] == 'VERIFIED'
        assert result['confidence'] >= 0.9
        assert result['hallucination_risk'] == 'LOW'
        assert 'claims' in result
        assert len(result['claims']) > 0

    @pytest.mark.asyncio
    async def test_verify_bullet_unsupported_claim(self):
        """Test detection of unsupported claims (UNSUPPORTED)"""
        from generation.services.bullet_verification_service import BulletVerificationService

        service = BulletVerificationService()

        bullet = "Led team of 10 engineers to deliver project 50% under budget"
        source_content = """
        Software Engineer at TechCorp
        - Developed microservices architecture
        - Implemented CI/CD pipeline
        - Worked with cross-functional teams
        """

        # Mock LLM response detecting unsupported claims
        with patch.object(service.client_manager, 'make_completion_call') as mock_call:
            mock_call.return_value = AsyncMock(
                choices=[Mock(message=Mock(content="""{
                    "claims": [
                        {
                            "claim": "Led team of 10 engineers",
                            "classification": "UNSUPPORTED",
                            "confidence": 0.85,
                            "evidence": null,
                            "reasoning": "No evidence of team leadership or team size in source"
                        },
                        {
                            "claim": "Delivered project 50% under budget",
                            "classification": "UNSUPPORTED",
                            "confidence": 0.90,
                            "evidence": null,
                            "reasoning": "No budget information or project delivery metrics mentioned"
                        }
                    ],
                    "overall_classification": "UNSUPPORTED",
                    "overall_confidence": 0.87,
                    "hallucination_risk": "HIGH"
                }"""))],
                usage=Mock(prompt_tokens=100, completion_tokens=150)
            )

            result = await service.verify_single_bullet(
                bullet=bullet,
                source_content=source_content,
                user_id=self.user.id
            )

        # Verify unsupported detection
        assert result['classification'] == 'UNSUPPORTED'
        assert result['hallucination_risk'] == 'HIGH'
        assert all(claim['classification'] == 'UNSUPPORTED' for claim in result['claims'])

    @pytest.mark.asyncio
    async def test_verify_bullet_inferred_claim(self):
        """Test classification of inferred claims (INFERRED)"""
        from generation.services.bullet_verification_service import BulletVerificationService

        service = BulletVerificationService()

        bullet = "Implemented OAuth authentication system"
        source_content = """
        Backend Developer at StartupXYZ
        - Built user login and registration system
        - Integrated third-party authentication
        - Enhanced security with token-based auth
        """

        # Mock LLM response with inferred classification
        with patch.object(service.client_manager, 'make_completion_call') as mock_call:
            mock_call.return_value = AsyncMock(
                choices=[Mock(message=Mock(content="""{
                    "claims": [
                        {
                            "claim": "Implemented OAuth authentication",
                            "classification": "INFERRED",
                            "confidence": 0.65,
                            "evidence": "Integrated third-party authentication",
                            "reasoning": "OAuth is implied by 'third-party authentication' but not explicitly stated"
                        }
                    ],
                    "overall_classification": "INFERRED",
                    "overall_confidence": 0.65,
                    "hallucination_risk": "MEDIUM"
                }"""))],
                usage=Mock(prompt_tokens=100, completion_tokens=150)
            )

            result = await service.verify_single_bullet(
                bullet=bullet,
                source_content=source_content,
                user_id=self.user.id
            )

        # Verify inferred classification
        assert result['classification'] == 'INFERRED'
        assert 0.5 <= result['confidence'] < 0.8
        assert result['hallucination_risk'] == 'MEDIUM'

    @pytest.mark.asyncio
    async def test_extract_claims_from_bullet(self):
        """Test claim extraction (step 1 of 4-step verification)"""
        from generation.services.bullet_verification_service import BulletVerificationService

        service = BulletVerificationService()

        bullet = "Led team of 5 engineers to build microservices platform, improving deployment time by 60%"

        # Mock LLM response for claim extraction
        with patch.object(service.client_manager, 'make_completion_call') as mock_call:
            mock_call.return_value = AsyncMock(
                choices=[Mock(message=Mock(content="""{
                    "claims": [
                        "Led team of 5 engineers",
                        "Built microservices platform",
                        "Improved deployment time by 60%"
                    ]
                }"""))],
                usage=Mock(prompt_tokens=50, completion_tokens=50)
            )

            claims = await service._extract_claims(bullet)

        # Verify claim extraction
        assert isinstance(claims, list)
        assert len(claims) >= 2  # Should extract multiple claims
        assert any('5 engineers' in claim or 'team' in claim for claim in claims)
        assert any('60%' in claim or 'deployment' in claim for claim in claims)

    @pytest.mark.asyncio
    async def test_build_verification_prompt(self):
        """Test verification prompt building with chain-of-thought instructions"""
        from generation.services.bullet_verification_service import BulletVerificationService

        service = BulletVerificationService()

        bullet = "Improved system performance by 40%"
        claims = ["Improved system performance by 40%"]
        source_content = "Optimized database queries"

        prompt = service._build_verification_prompt(bullet, claims, source_content)

        # Verify prompt includes key elements
        assert 'chain-of-thought' in prompt.lower() or 'reasoning' in prompt.lower()
        assert 'VERIFIED' in prompt
        assert 'INFERRED' in prompt
        assert 'UNSUPPORTED' in prompt
        assert bullet in prompt
        assert source_content in prompt
        assert 'evidence' in prompt.lower()

    @pytest.mark.asyncio
    async def test_verify_bullet_set_parallel(self):
        """Test parallel verification of multiple bullets (up to 3)"""
        from generation.services.bullet_verification_service import BulletVerificationService

        service = BulletVerificationService()

        bullets = [
            "Improved API performance by 40%",
            "Led team of 5 engineers",
            "Implemented CI/CD pipeline"
        ]
        source_content = "Backend engineer with expertise in optimization and DevOps"

        # Mock LLM responses
        with patch.object(service, 'verify_single_bullet') as mock_verify:
            mock_verify.return_value = AsyncMock(return_value={
                'classification': 'VERIFIED',
                'confidence': 0.85,
                'hallucination_risk': 'LOW',
                'claims': []
            })

            results = await service.verify_bullet_set(
                bullets=bullets,
                source_content=source_content,
                user_id=self.user.id
            )

        # Verify parallel execution
        assert len(results) == 3
        assert mock_verify.call_count == 3  # Called for each bullet

    @pytest.mark.asyncio
    async def test_circuit_breaker_on_llm_failure(self):
        """Test circuit breaker activates on LLM failures"""
        from generation.services.bullet_verification_service import BulletVerificationService

        service = BulletVerificationService()

        bullet = "Test bullet"
        source_content = "Test content"

        # Mock LLM failure
        with patch.object(service.client_manager, 'make_completion_call') as mock_call:
            mock_call.side_effect = Exception("LLM API Error")

            # Should gracefully degrade instead of crashing
            # Assert that LLM failure is logged
            with self.assertLogs('generation.services.bullet_verification_service', level='ERROR') as cm:
                result = await service.verify_single_bullet(
                    bullet=bullet,
                    source_content=source_content,
                    user_id=self.user.id
                )

            # Verify expected error message was logged
            self.assertIn('[ft-030] LLM verification error', cm.output[0])
            self.assertIn('LLM API Error', cm.output[0])

        # Verify graceful degradation
        assert 'error' in result or result['classification'] == 'UNVERIFIED'
        assert 'confidence' in result
        # Should have low confidence when verification fails
        assert result['confidence'] < 0.5

    @pytest.mark.asyncio
    async def test_confidence_based_on_evidence_strength(self):
        """Test that confidence reflects evidence strength"""
        from generation.services.bullet_verification_service import BulletVerificationService

        service = BulletVerificationService()

        # Strong evidence case
        bullet = "Reduced database query time by 50%"
        source_content = "Optimized SQL queries, reducing average query execution time from 200ms to 100ms (50% improvement)"

        with patch.object(service.client_manager, 'make_completion_call') as mock_call:
            mock_call.return_value = AsyncMock(
                choices=[Mock(message=Mock(content="""{
                    "claims": [{
                        "claim": "Reduced database query time by 50%",
                        "classification": "VERIFIED",
                        "confidence": 0.98,
                        "evidence": "reducing average query execution time from 200ms to 100ms (50% improvement)",
                        "reasoning": "Exact match with specific metrics"
                    }],
                    "overall_classification": "VERIFIED",
                    "overall_confidence": 0.98,
                    "hallucination_risk": "LOW"
                }"""))],
                usage=Mock(prompt_tokens=100, completion_tokens=100)
            )

            result = await service.verify_single_bullet(bullet, source_content, self.user.id)

        # High confidence for strong evidence
        assert result['confidence'] >= 0.95

    @pytest.mark.asyncio
    async def test_multiple_claims_aggregate_correctly(self):
        """Test aggregation of multiple claim results"""
        from generation.services.bullet_verification_service import BulletVerificationService

        service = BulletVerificationService()

        bullet = "Led Python team to build REST API with 99.9% uptime"
        source_content = "Senior Python developer on backend team. Built REST API services."

        # Mock response with mixed classifications
        with patch.object(service.client_manager, 'make_completion_call') as mock_call:
            mock_call.return_value = AsyncMock(
                choices=[Mock(message=Mock(content="""{
                    "claims": [
                        {
                            "claim": "Led Python team",
                            "classification": "INFERRED",
                            "confidence": 0.60,
                            "evidence": "Senior Python developer on backend team",
                            "reasoning": "Senior role implies leadership but not explicitly stated"
                        },
                        {
                            "claim": "Built REST API",
                            "classification": "VERIFIED",
                            "confidence": 0.95,
                            "evidence": "Built REST API services",
                            "reasoning": "Direct match"
                        },
                        {
                            "claim": "99.9% uptime",
                            "classification": "UNSUPPORTED",
                            "confidence": 0.85,
                            "evidence": null,
                            "reasoning": "No uptime metrics provided in source"
                        }
                    ],
                    "overall_classification": "INFERRED",
                    "overall_confidence": 0.70,
                    "hallucination_risk": "MEDIUM"
                }"""))],
                usage=Mock(prompt_tokens=100, completion_tokens=150)
            )

            result = await service.verify_single_bullet(bullet, source_content, self.user.id)

        # Verify aggregation logic
        assert len(result['claims']) == 3
        # Overall classification should reflect worst case or weighted average
        assert result['overall_classification'] in ['INFERRED', 'UNSUPPORTED']
        assert 'hallucination_risk' in result

    @pytest.mark.asyncio
    async def test_timeout_protection(self):
        """Test timeout protection for slow LLM calls"""
        from generation.services.bullet_verification_service import BulletVerificationService
        import asyncio

        service = BulletVerificationService()

        bullet = "Test bullet"
        source_content = "Test content"

        # Mock slow LLM call
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate 10s delay
            return Mock()

        with patch.object(service.client_manager, 'make_completion_call', side_effect=slow_call):
            # Should timeout and gracefully degrade
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(
                    service.verify_single_bullet(bullet, source_content, self.user.id),
                    timeout=2.0  # 2 second timeout
                )

    @pytest.mark.asyncio
    async def test_cost_tracking(self):
        """Test that verification tracks LLM costs"""
        from generation.services.bullet_verification_service import BulletVerificationService

        service = BulletVerificationService()

        bullet = "Test bullet"
        source_content = "Test content"

        with patch.object(service.client_manager, 'make_completion_call') as mock_call:
            mock_call.return_value = AsyncMock(
                choices=[Mock(message=Mock(content="""{
                    "claims": [{"claim": "Test", "classification": "VERIFIED", "confidence": 0.9, "evidence": "test", "reasoning": "test"}],
                    "overall_classification": "VERIFIED",
                    "overall_confidence": 0.9,
                    "hallucination_risk": "LOW"
                }"""))],
                usage=Mock(prompt_tokens=100, completion_tokens=150)
            )

            result = await service.verify_single_bullet(bullet, source_content, self.user.id)

        # Verify cost tracking
        assert 'cost' in result or hasattr(service, 'total_cost')
        # Cost should be > 0 for GPT-5 calls
        if 'cost' in result:
            assert result['cost'] > 0

    @pytest.mark.asyncio
    async def test_uses_gpt5_with_high_reasoning(self):
        """Test that verification uses GPT-5 with high reasoning effort"""
        from generation.services.bullet_verification_service import BulletVerificationService
        from llm_services.services.base.config_registry import TaskType

        service = BulletVerificationService()

        # Verify service is configured for VERIFICATION task type
        assert hasattr(service, 'task_type')
        assert service.task_type == TaskType.VERIFICATION

        # Verify config uses GPT-5 with high reasoning
        config = service._build_llm_config()
        assert config['model'] == 'gpt-5'
        assert config['reasoning_effort'] == 'high'
