"""
Unified settings management for LLM services.
"""

from typing import Dict, Any, Optional
from django.conf import settings


class SettingsManager:
    """Centralized configuration management for LLM services"""

    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """Get LLM service configuration"""
        strategy = getattr(settings, 'MODEL_SELECTION_STRATEGY', 'balanced')
        return getattr(settings, 'LLM_SERVICE_SETTINGS', {
            'default_timeout': 30,
            'retry_attempts': 3,
            'fallback_enabled': True,
            'model_selection_strategy': strategy
        })

    @classmethod
    def get_circuit_breaker_config(cls) -> Dict[str, Any]:
        """Get circuit breaker configuration"""
        return getattr(settings, 'CIRCUIT_BREAKER_SETTINGS', {
            'failure_threshold': 5,
            'timeout': 30,
            'retry_attempts': 3
        })

    @classmethod
    def get_langchain_config(cls) -> Dict[str, Any]:
        """Get LangChain document processing configuration"""
        return getattr(settings, 'LANGCHAIN_SETTINGS', {
            'chunk_size': 1000,
            'chunk_overlap': 200,
            'max_chunks_per_document': 50
        })

    @classmethod
    def get_model_selection_config(cls) -> Dict[str, Any]:
        """Get model selection strategy configuration"""
        strategy = getattr(settings, 'MODEL_SELECTION_STRATEGY', 'balanced')
        strategies = getattr(settings, 'MODEL_STRATEGIES', {
            'balanced': {
                'job_parsing_model': 'gpt-5',
                'cv_generation_model': 'gpt-5',
                'embedding_model': 'text-embedding-3-small'
            },
            'cost_optimized': {
                'job_parsing_model': 'gpt-5-mini',
                'cv_generation_model': 'gpt-5-mini',
                'embedding_model': 'text-embedding-3-small'
            },
            'quality_optimized': {
                'job_parsing_model': 'gpt-5',
                'cv_generation_model': 'gpt-5',
                'embedding_model': 'text-embedding-3-small'
            }
        })

        return {
            'strategy': strategy,
            'config': strategies.get(strategy, strategies['balanced'])
        }

    @classmethod
    def get_api_keys(cls) -> Dict[str, str]:
        """Get API keys for different providers (OpenAI only)"""
        return {
            'openai': getattr(settings, 'OPENAI_API_KEY', '')
        }

    @classmethod
    def get_embedding_config(cls) -> Dict[str, Any]:
        """Get embedding service configuration"""
        return getattr(settings, 'EMBEDDING_SETTINGS', {
            'model': 'text-embedding-3-small',
            'batch_size': 100,
            'cache_embeddings': True,
            'dimensions': 1536
        })