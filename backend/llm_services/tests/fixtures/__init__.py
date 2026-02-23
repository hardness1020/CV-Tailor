"""
Test fixtures and sample data for LLM services tests.

This module provides reusable test data fixtures for job descriptions,
artifacts, and mock API responses.
"""

from .sample_job_descriptions import *
from .sample_artifacts import *
from .sample_responses import *

__all__ = [
    # Job descriptions
    'SAMPLE_JOB_DESCRIPTION',
    'SAMPLE_JOB_PARSED_DATA',
    'SAMPLE_JOB_WITH_REQUIREMENTS',

    # Artifacts
    'SAMPLE_ARTIFACTS_DATA',
    'SAMPLE_ENHANCED_ARTIFACT',
    'SAMPLE_ARTIFACT_CHUNKS',

    # API responses
    'MOCK_OPENAI_RESPONSES',
    'MOCK_ANTHROPIC_RESPONSES',
    'MOCK_EMBEDDING_RESPONSE',
]
