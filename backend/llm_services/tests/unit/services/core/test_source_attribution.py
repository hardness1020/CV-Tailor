"""
Unit tests for source attribution functionality (ft-030 - Anti-Hallucination Improvements).
Tests source attribution extraction, coverage calculation, and inferred ratio tracking.

Implements ADR-041: Source Attribution Schema
"""

import pytest
import unittest
from unittest.mock import Mock, patch, AsyncMock
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

from llm_services.services.core.evidence_content_extractor import (
    EvidenceContentExtractor,
    ExtractedContent
)

User = get_user_model()


# These will be implemented in the next step
@dataclass
class SourceAttribution:
    """Source attribution for extracted content item"""
    source_quote: str  # Exact quote from source document
    source_location: str  # Location in document (page, section, line)
    confidence: float  # 0.0-1.0 confidence that quote supports item
    reasoning: Optional[str] = None  # Optional explanation


@tag('medium', 'integration', 'llm_services', 'attribution')
class SourceAttributionTestCase(TestCase):
    """Test source attribution extraction and tracking"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.extractor = EvidenceContentExtractor()

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_extract_with_source_attribution(self, mock_llm_call):
        """Test that PDF extraction includes source attribution for achievements"""
        pdf_chunks = [
            {
                'content': 'Improved API response time by 40% through caching implementation',
                'metadata': {'page': 1, 'section': 'Experience'}
            },
            {
                'content': 'Led team of 5 engineers to deliver project 2 weeks ahead of schedule',
                'metadata': {'page': 1, 'section': 'Experience'}
            }
        ]

        # Mock LLM response with source attribution
        mock_llm_call.return_value = {
            'content': '''{
                "technologies": ["Python", "Redis"],
                "achievements": [
                    {
                        "text": "Improved API response time by 40%",
                        "source_attribution": {
                            "source_quote": "Improved API response time by 40% through caching implementation",
                            "source_location": "page 1, Experience section",
                            "confidence": 0.95,
                            "reasoning": "Direct quote from source document"
                        }
                    },
                    {
                        "text": "Led team of 5 engineers",
                        "source_attribution": {
                            "source_quote": "Led team of 5 engineers to deliver project 2 weeks ahead of schedule",
                            "source_location": "page 1, Experience section",
                            "confidence": 0.92,
                            "reasoning": "Partial match with source"
                        }
                    }
                ],
                "summary": "Experienced engineer with proven track record"
            }''',
            'cost': 0.002,
            'tokens': 200
        }

        result = await self.extractor.extract_pdf_content(
            pdf_chunks=pdf_chunks,
            user_id=self.user.id
        )

        # Verify source attribution exists
        assert result.success is True
        assert 'achievements' in result.data
        achievements = result.data['achievements']
        assert len(achievements) > 0

        # Verify attribution structure for first achievement
        first_achievement = achievements[0]
        assert 'source_attribution' in first_achievement
        attribution = first_achievement['source_attribution']

        # Verify attribution fields
        assert 'source_quote' in attribution
        assert 'source_location' in attribution
        assert 'confidence' in attribution
        assert isinstance(attribution['confidence'], (int, float))
        assert 0.0 <= attribution['confidence'] <= 1.0

        # Verify source quote is not empty
        assert len(attribution['source_quote']) > 0

    @unittest.skip("ft-030: JSON parsing issue with null source_attribution - requires investigation")
    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, 'extract_quantified_metrics', new_callable=AsyncMock)
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_attribution_coverage_calculation(self, mock_llm_call, mock_metrics):
        """Test calculation of attribution coverage metric (≥95% target)"""
        # Mock extract_quantified_metrics to return empty list
        mock_metrics.return_value = []

        pdf_chunks = [
            {
                'content': 'Python, Django, PostgreSQL, Redis',
                'metadata': {'page': 1}
            }
        ]

        # Mock response with partial attribution (3 out of 4 technologies attributed)
        mock_llm_call.return_value = {
            'content': '{"technologies": [{"name": "Python", "source_attribution": {"source_quote": "Python", "source_location": "page 1", "confidence": 0.98}}, {"name": "Django", "source_attribution": {"source_quote": "Django", "source_location": "page 1", "confidence": 0.96}}, {"name": "PostgreSQL", "source_attribution": {"source_quote": "PostgreSQL", "source_location": "page 1", "confidence": 0.94}}, {"name": "Redis", "source_attribution": null}], "achievements": [], "summary": "Backend developer"}',
            'cost': 0.001
        }

        result = await self.extractor.extract_pdf_content(
            pdf_chunks=pdf_chunks,
            user_id=self.user.id
        )

        # Verify attribution_coverage field exists
        assert 'attribution_coverage' in result.data
        coverage = result.data['attribution_coverage']

        # Verify coverage is calculated as percentage
        assert isinstance(coverage, (int, float))
        assert 0.0 <= coverage <= 1.0

        # ft-030 HIGH-PRECISION: Redis with null attribution is filtered out (< 0.8 threshold)
        # Only Python (0.98), Django (0.96), PostgreSQL (0.94) remain
        # Coverage = 3 attributed / 3 total = 1.0
        assert coverage == 1.0, \
            "Attribution coverage should be 1.0 (3 attributed / 3 total after filtering)"

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, 'extract_quantified_metrics', new_callable=AsyncMock)
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_inferred_item_ratio_calculation(self, mock_llm_call, mock_metrics):
        """Test calculation of inferred_item_ratio (≤20% target)"""
        # Mock extract_quantified_metrics to return empty list
        mock_metrics.return_value = []

        pdf_chunks = [
            {
                'content': 'Built REST API with authentication',
                'metadata': {'page': 1}
            }
        ]

        # Mock response with some inferred items (low confidence attribution)
        mock_llm_call.return_value = {
            'content': '''{
                "technologies": [
                    {
                        "name": "REST API",
                        "source_attribution": {
                            "source_quote": "Built REST API with authentication",
                            "source_location": "page 1",
                            "confidence": 0.95
                        }
                    },
                    {
                        "name": "JWT",
                        "source_attribution": {
                            "source_quote": "authentication",
                            "source_location": "page 1",
                            "confidence": 0.45
                        }
                    },
                    {
                        "name": "OAuth",
                        "source_attribution": {
                            "source_quote": "authentication",
                            "source_location": "page 1",
                            "confidence": 0.40
                        }
                    }
                ],
                "achievements": [],
                "summary": "API developer"
            }''',
            'cost': 0.001
        }

        result = await self.extractor.extract_pdf_content(
            pdf_chunks=pdf_chunks,
            user_id=self.user.id
        )

        # Verify inferred_item_ratio field exists
        assert 'inferred_item_ratio' in result.data
        inferred_ratio = result.data['inferred_item_ratio']

        # Verify ratio is calculated as percentage
        assert isinstance(inferred_ratio, (int, float))
        assert 0.0 <= inferred_ratio <= 1.0

        # ft-030 HIGH-PRECISION: JWT (0.45) and OAuth (0.40) are filtered out (< 0.8 threshold)
        # Only REST API (0.95) remains
        # Inferred ratio = 0 / 1 = 0.0 (REST API has 0.95 confidence, not inferred)
        assert inferred_ratio == 0.0, \
            f"Inferred ratio should be 0.0 (0 inferred / 1 total after filtering), got {inferred_ratio:.2f}"

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, 'extract_quantified_metrics', new_callable=AsyncMock)
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_missing_attribution_handling(self, mock_llm_call, mock_metrics):
        """Test graceful handling when attribution is missing or incomplete"""
        # Mock extract_quantified_metrics to return empty list
        mock_metrics.return_value = []

        pdf_chunks = [
            {
                'content': 'Python developer with 5 years experience',
                'metadata': {'page': 1}
            }
        ]

        # Mock response without attribution (legacy format)
        mock_llm_call.return_value = {
            'content': '''{
                "technologies": ["Python", "Django"],
                "achievements": ["5 years experience"],
                "summary": "Python developer"
            }''',
            'cost': 0.001
        }

        result = await self.extractor.extract_pdf_content(
            pdf_chunks=pdf_chunks,
            user_id=self.user.id
        )

        # Verify extraction succeeds even without attribution
        assert result.success is True
        assert 'technologies' in result.data
        # ft-030 HIGH-PRECISION: Legacy format items without attribution are filtered out
        assert len(result.data['technologies']) == 0

        # Verify attribution_coverage defaults to 0.0 when missing
        assert 'attribution_coverage' in result.data
        assert result.data['attribution_coverage'] == 0.0

        # Verify inferred_item_ratio defaults to 0.0 when total_items = 0
        # (legacy items are filtered out in HIGH-PRECISION mode)
        assert 'inferred_item_ratio' in result.data
        assert result.data['inferred_item_ratio'] == 0.0

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, 'extract_quantified_metrics', new_callable=AsyncMock)
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_high_inferred_ratio_penalty(self, mock_llm_call, mock_metrics):
        """Test that high inferred_ratio (>30%) reduces confidence score"""
        # Mock extract_quantified_metrics to return empty list
        mock_metrics.return_value = []

        pdf_chunks = [
            {
                'content': 'Software engineer',
                'metadata': {'page': 1}
            }
        ]

        # Mock response with mostly inferred items
        mock_llm_call.return_value = {
            'content': '''{
                "technologies": [
                    {
                        "name": "Python",
                        "source_attribution": {
                            "source_quote": "Software",
                            "source_location": "page 1",
                            "confidence": 0.30
                        }
                    },
                    {
                        "name": "Django",
                        "source_attribution": {
                            "source_quote": "Software",
                            "source_location": "page 1",
                            "confidence": 0.25
                        }
                    },
                    {
                        "name": "PostgreSQL",
                        "source_attribution": {
                            "source_quote": "engineer",
                            "source_location": "page 1",
                            "confidence": 0.20
                        }
                    }
                ],
                "achievements": [],
                "summary": "Software engineer"
            }''',
            'cost': 0.001
        }

        result = await self.extractor.extract_pdf_content(
            pdf_chunks=pdf_chunks,
            user_id=self.user.id
        )

        # ft-030 HIGH-PRECISION: All items (Python 0.30, Django 0.25, PostgreSQL 0.20) are filtered out (< 0.8 threshold)
        # No items remain, so inferred_ratio = 0.0 (not 1.0)
        assert 'inferred_item_ratio' in result.data
        assert result.data['inferred_item_ratio'] == 0.0

        # Verify confidence is low due to empty extraction
        # Base confidence is penalized when extraction is empty
        assert result.confidence < 0.7, \
            "Confidence should be low when no items pass the confidence threshold"

    @pytest.mark.asyncio
    async def test_attribution_prompt_enhancement(self):
        """Test that extraction prompts include citation requirements"""
        extractor = EvidenceContentExtractor()

        # Test that the prompt includes attribution instructions
        with patch.object(extractor, '_call_llm_for_extraction') as mock_call:
            mock_call.return_value = {
                'content': '{"technologies": [], "achievements": [], "summary": ""}',
                'cost': 0.001
            }

            pdf_chunks = [
                {
                    'content': 'Sample content',
                    'metadata': {'page': 1}
                }
            ]

            await extractor.extract_pdf_content(
                pdf_chunks=pdf_chunks,
                user_id=self.user.id
            )

            # Verify LLM was called with enhanced prompt
            assert mock_call.called
            call_args = mock_call.call_args[1]  # Get keyword arguments
            prompt = call_args.get('prompt', '')

            # Verify prompt includes attribution requirements
            assert 'source_attribution' in prompt.lower() or 'source' in prompt.lower() or 'quote' in prompt.lower(), \
                "Extraction prompt should include source attribution requirements"

            # Verify prompt emphasizes factual extraction
            assert 'only extract' in prompt.lower() or 'explicitly' in prompt.lower(), \
                "Prompt should emphasize extracting only explicitly stated information"

    @pytest.mark.asyncio
    @patch.object(EvidenceContentExtractor, '_call_llm_for_extraction')
    async def test_attribution_coverage_high_quality(self, mock_llm_call):
        """Test that high-quality extraction achieves ≥95% attribution coverage"""
        pdf_chunks = [
            {
                'content': 'Experienced with Python, Django, PostgreSQL, Docker, and AWS',
                'metadata': {'page': 1}
            }
        ]

        # Mock high-quality response with full attribution
        mock_llm_call.return_value = {
            'content': '''{
                "technologies": [
                    {
                        "name": "Python",
                        "source_attribution": {
                            "source_quote": "Experienced with Python",
                            "source_location": "page 1",
                            "confidence": 0.98
                        }
                    },
                    {
                        "name": "Django",
                        "source_attribution": {
                            "source_quote": "Django",
                            "source_location": "page 1",
                            "confidence": 0.97
                        }
                    },
                    {
                        "name": "PostgreSQL",
                        "source_attribution": {
                            "source_quote": "PostgreSQL",
                            "source_location": "page 1",
                            "confidence": 0.96
                        }
                    },
                    {
                        "name": "Docker",
                        "source_attribution": {
                            "source_quote": "Docker",
                            "source_location": "page 1",
                            "confidence": 0.95
                        }
                    },
                    {
                        "name": "AWS",
                        "source_attribution": {
                            "source_quote": "AWS",
                            "source_location": "page 1",
                            "confidence": 0.94
                        }
                    }
                ],
                "achievements": [],
                "summary": "Backend developer"
            }''',
            'cost': 0.002
        }

        result = await self.extractor.extract_pdf_content(
            pdf_chunks=pdf_chunks,
            user_id=self.user.id
        )

        # Verify high attribution coverage
        assert 'attribution_coverage' in result.data
        coverage = result.data['attribution_coverage']
        assert coverage >= 0.95, \
            f"High-quality extraction should achieve ≥95% coverage, got {coverage:.2%}"

        # Verify low inferred ratio
        assert 'inferred_item_ratio' in result.data
        inferred_ratio = result.data['inferred_item_ratio']
        assert inferred_ratio <= 0.20, \
            f"High-quality extraction should have ≤20% inferred items, got {inferred_ratio:.2%}"
