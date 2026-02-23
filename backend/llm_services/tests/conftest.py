"""
Pytest configuration and fixtures for LLM services tests.
"""

import os
import pytest
import django
from django.conf import settings
from django.test import override_settings
from unittest.mock import Mock, patch

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cv_tailor.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

# Import reusable test fixtures
from .fixtures import (
    SAMPLE_JOB_DESCRIPTION,
    SAMPLE_ARTIFACTS_DATA,
    MOCK_OPENAI_RESPONSES,
    MOCK_ANTHROPIC_RESPONSES,
    build_mock_chat_response
)


@pytest.fixture
def user():
    """Create a test user."""
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def staff_user():
    """Create a staff test user."""
    return User.objects.create_user(
        username='staffuser',
        email='staff@example.com',
        password='testpass123',
        is_staff=True
    )


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    with patch('llm_services.services.core.tailored_content_service.OpenAI') as mock_openai:
        mock_client = Mock()
        mock_openai.return_value = mock_client

        # Mock chat completion
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = '{"result": "test"}'
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 200
        mock_client.chat.completions.create.return_value = mock_response

        yield mock_client


@pytest.fixture
def mock_langchain():
    """Mock LangChain components."""
    with patch('llm_services.services.core.document_processor.PyPDFLoader') as mock_loader, \
         patch('llm_services.services.core.document_processor.RecursiveCharacterTextSplitter') as mock_splitter:

        # Mock loader
        mock_loader_instance = Mock()
        mock_loader.return_value = mock_loader_instance
        mock_loader_instance.load.return_value = [
            Mock(page_content="Test content", metadata={"page": 1})
        ]

        # Mock splitter
        mock_splitter_instance = Mock()
        mock_splitter.return_value = mock_splitter_instance
        mock_splitter_instance.split_documents.return_value = [
            Mock(page_content="Chunk 1", metadata={"chunk": 0})
        ]
        mock_splitter_instance.split_text.return_value = ["Text chunk 1"]

        yield {
            'loader': mock_loader,
            'splitter': mock_splitter
        }


@pytest.fixture
def mock_redis():
    """Mock Redis cache."""
    with patch('django.core.cache.cache') as mock_cache:
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        yield mock_cache


@pytest.fixture
def mock_celery_task():
    """Mock Celery task instance."""
    task = Mock()
    task.request = Mock()
    task.request.retries = 0
    task.max_retries = 3
    task.retry = Mock()
    return task


@pytest.fixture
@override_settings(
    # Test settings overrides
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    },
    # Mock API keys
    OPENAI_API_KEY='test-openai-key',
    ANTHROPIC_API_KEY='test-anthropic-key',
    # Test model configuration
    MODEL_SELECTION_STRATEGY='balanced',
    MODEL_BUDGETS={
        'free_tier': {'daily_limit_usd': 1.0},
        'paid_tier': {'daily_limit_usd': 10.0}
    }
)
def test_settings():
    """Test-specific Django settings."""
    yield


# Async test fixture for asyncio tests
@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Database fixtures
@pytest.fixture
def performance_metrics(user):
    """Create test performance metrics."""
    from llm_services.models import ModelPerformanceMetric
    from decimal import Decimal

    metrics = []
    for i in range(3):
        metric = ModelPerformanceMetric.objects.create(
            model_name='gpt-5',
            task_type='cv_generation',
            processing_time_ms=1000 + i * 100,
            tokens_used=500 + i * 50,
            cost_usd=Decimal(f'0.00{5 + i}'),
            success=True,
            user=user
        )
        metrics.append(metric)

    return metrics


@pytest.fixture
def circuit_breakers():
    """Create test circuit breakers."""
    from llm_services.models import CircuitBreakerState

    breakers = []
    for model_name in ['gpt-5', 'claude-sonnet-4', 'broken-model']:
        state = 'closed' if model_name != 'broken-model' else 'open'
        breaker = CircuitBreakerState.objects.create(
            model_name=model_name,
            state=state,
            failure_count=0 if state == 'closed' else 5
        )
        breakers.append(breaker)

    return breakers


# Mock external API responses
@pytest.fixture
def mock_openai_responses():
    """Mock OpenAI API responses."""
    return {
        'job_parsing': {
            'choices': [{
                'message': {
                    'content': '{"company_name": "Tech Corp", "role_title": "Engineer", "must_have_skills": ["Python"]}'
                }
            }],
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50}
        },
        'cv_generation': {
            'choices': [{
                'message': {
                    'content': '{"professional_summary": "Experienced developer", "key_skills": ["Python", "Django"]}'
                }
            }],
            'usage': {'prompt_tokens': 200, 'completion_tokens': 100}
        }
    }


@pytest.fixture
def sample_job_description():
    """Sample job description for testing."""
    return {
        'raw_content': '''
        Software Engineer position at Tech Corp.
        Requirements: Python, Django, React, 5+ years experience.
        Responsibilities: Build web applications, lead technical projects.
        ''',
        'company_name': 'Tech Corp',
        'role_title': 'Software Engineer'
    }


@pytest.fixture
def sample_artifacts_data():
    """Sample artifacts data for testing."""
    return [
        {
            'id': 1,
            'title': 'Backend API Development',
            'description': 'Built REST APIs using Python and Django',
            'artifact_type': 'project',
            'technologies': ['Python', 'Django', 'PostgreSQL'],
            'start_date': '2023-01-01',
            'end_date': '2023-12-31'
        },
        {
            'id': 2,
            'title': 'Frontend React App',
            'description': 'Developed responsive web application using React',
            'artifact_type': 'project',
            'technologies': ['React', 'JavaScript', 'CSS'],
            'start_date': '2022-06-01',
            'end_date': '2022-12-31'
        }
    ]


# Pytest markers for organizing tests
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "unit: Unit tests"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests"
    )
    config.addinivalue_line(
        "markers", "async_test: Async tests"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests"
    )