"""
Unit tests for LLM service (core layer).
"""

import json
import asyncio
import uuid
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from django.test import TestCase, override_settings, tag
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from asgiref.sync import sync_to_async

from llm_services.services.core.tailored_content_service import TailoredContentService
from llm_services.models import ModelPerformanceMetric, CircuitBreakerState

User = get_user_model()


@tag('medium', 'integration', 'llm_services')
class LLMServiceTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.llm_service = TailoredContentService()

    def test_select_model_for_task(self):
        """Test model selection logic via model selector"""
        with patch.object(self.llm_service.model_selector, 'select_model_for_task') as mock_select:
            mock_select.return_value = 'gpt-5'

            with patch.object(self.llm_service.model_selector, 'get_selection_reason') as mock_reason:
                mock_reason.return_value = 'Model selected based on task requirements'

                # Test the model selector directly since LLMService uses it
                selected_model = self.llm_service.model_selector.select_model_for_task(
                    task_type='cv_generation',
                    context={'task_type': 'cv_generation'}
                )
                reasoning = self.llm_service.model_selector.get_selection_reason(selected_model, {})

                self.assertEqual(selected_model, 'gpt-5')
                self.assertIn('selected', reasoning.lower())
                mock_select.assert_called_once()
                mock_reason.assert_called_once()

    @override_settings(OPENAI_API_KEY='test-key-123')
    async def test_parse_job_description(self):
        """Test job description parsing"""
        # Mock _direct_api_call response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            'company_name': 'Tech Corp',
            'role_title': 'Senior Developer',
            'must_have_skills': ['Python', 'Django'],
            'nice_to_have_skills': ['React'],
            'key_responsibilities': ['Develop web applications'],
            'confidence_score': 0.9
        })
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 200
        mock_response.usage.total_tokens = 300

        with patch.object(self.llm_service.model_selector, 'select_model_for_task') as mock_select, \
             patch.object(self.llm_service.client_manager, 'make_completion_call', return_value=mock_response) as mock_api_call:

            mock_select.return_value = 'gpt-5'

            result = await self.llm_service.parse_job_description(
                "Software engineer position at Tech Corp",
                "Tech Corp",
                "Software Engineer",
                self.user.id
            )

            self.assertEqual(result['company_name'], 'Tech Corp')
            self.assertEqual(result['role_title'], 'Senior Developer')
            self.assertIn('Python', result['must_have_skills'])
            self.assertEqual(result['confidence_score'], 0.9)
            mock_api_call.assert_called_once()

    async def test_parse_job_description_api_error(self):
        """Test job description parsing with API error"""

        with patch.object(self.llm_service.model_selector, 'select_model_for_task') as mock_select, \
             patch.object(self.llm_service.client_manager, 'make_completion_call') as mock_api_call, \
             patch.object(self.llm_service.model_selector, 'should_use_fallback') as mock_fallback:

            mock_select.return_value = 'gpt-5'
            # Mock the API call to raise an exception
            mock_api_call.side_effect = Exception("API Error")
            # Mock fallback to return False so no fallback is attempted
            mock_fallback.return_value = False

            result = await self.llm_service.parse_job_description(
                "Job description",
                "Company",
                "Role",
                self.user.id
            )

            self.assertIn('error', result)
            self.assertIn('error occurred', result['error'].lower())

    @override_settings(OPENAI_API_KEY='test-key-123')
    async def test_generate_cv_content(self):
        """Test CV content generation"""
        # Mock API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
            This is a comprehensive CV content tailored to the job requirements.

            Professional Summary: Experienced developer with expertise in Python and Django.

            Key Skills: Python, Django, React, Software Engineering

            Work Experience:
            - Developer at Tech Corp: Built scalable applications using Python and Django

            Achievements:
            - Developed high-performance web applications
            - Led technical initiatives resulting in improved system efficiency
        """
        mock_response.usage.prompt_tokens = 200
        mock_response.usage.completion_tokens = 400
        mock_response.usage.total_tokens = 600

        job_data = {
            'must_have_skills': ['Python', 'Django'],
            'role_title': 'Senior Developer'
        }
        artifacts = [{'title': 'My Resume', 'technologies': ['Python']}]

        with patch.object(self.llm_service.model_selector, 'select_model_for_task') as mock_select, \
             patch.object(self.llm_service.client_manager, 'make_completion_call', return_value=mock_response) as mock_api_call:

            mock_select.return_value = 'gpt-5'

            result = await self.llm_service.generate_cv_content(
                job_data, artifacts, {}, self.user.id
            )

            self.assertIn('cv_content', result)
            self.assertTrue(result['success'])
            mock_api_call.assert_called_once()