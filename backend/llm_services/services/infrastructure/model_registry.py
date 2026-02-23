"""
Model Registry with latest AI models and configurations.
Implements ft-llm-003-flexible-model-selection.md
"""

from typing import Dict, Any, List, Optional
from django.conf import settings


class ModelRegistry:
    """Registry of available AI models with metadata and capabilities"""

    # Model configurations with latest 2025 models and pricing
    MODELS = {
        "chat_models": {
            "gpt-5": {
                "provider": "openai",
                "cost_input": 0.003,     # $3.00 per MTok (estimated)
                "cost_output": 0.012,    # $12.00 per MTok (estimated)
                "context_window": 128000,
                "max_tokens": 16384,
                "strengths": ["reasoning", "coding", "agentic_tasks"],
                "best_for": ["general", "complex_reasoning"],
                "quality_tier": "high",
                "speed_rank": 1
            },
            "gpt-5-mini": {
                "provider": "openai",
                "cost_input": 0.0002,    # $0.20 per MTok (estimated)
                "cost_output": 0.0008,   # $0.80 per MTok (estimated)
                "context_window": 128000,
                "max_tokens": 16384,
                "strengths": ["cost_efficiency", "speed"],
                "best_for": ["simple_tasks", "high_volume"],
                "quality_tier": "medium",
                "speed_rank": 1
            },
            "gpt-5-nano": {
                "provider": "openai",
                "cost_input": 0.0001,    # $0.10 per MTok (estimated)
                "cost_output": 0.0004,   # $0.40 per MTok (estimated)
                "context_window": 128000,
                "max_tokens": 8192,
                "strengths": ["ultra_cost_efficiency", "ultra_fast"],
                "best_for": ["ultra_simple_tasks", "extreme_volume"],
                "quality_tier": "basic",
                "speed_rank": 1
            }
        },

        "embedding_models": {
            "text-embedding-3-small": {
                "provider": "openai",
                "cost": 0.00002,        # $0.02 per MTok
                "dimensions": 1536,
                "max_input_tokens": 8191,
                "mteb_score": 62.3,
                "pages_per_dollar": 62500,
                "best_for": ["all_use_cases"],  # Single model for all strategies
                "quality_tier": "standard"
            }
        }
    }

    @classmethod
    def get_model_config(cls, model_name: str, model_type: str = "chat_models") -> Optional[Dict[str, Any]]:
        """Get configuration for a specific model"""
        return cls.MODELS.get(model_type, {}).get(model_name)

    @classmethod
    def get_models_by_provider(cls, provider: str, model_type: str = "chat_models") -> Dict[str, Dict[str, Any]]:
        """Get all models from a specific provider"""
        models = cls.MODELS.get(model_type, {})
        return {
            name: config for name, config in models.items()
            if config.get("provider") == provider and not config.get("deprecated", False)
        }

    @classmethod
    def get_models_by_criteria(cls,
                             model_type: str = "chat_models",
                             max_cost_per_1k_tokens: Optional[float] = None,
                             min_quality_tier: Optional[str] = None,
                             required_strengths: Optional[List[str]] = None,
                             exclude_deprecated: bool = True) -> Dict[str, Dict[str, Any]]:
        """Get models matching specific criteria"""
        models = cls.MODELS.get(model_type, {})
        filtered_models = {}

        quality_rankings = {"premium": 3, "high": 2, "medium": 1, "standard": 1}
        min_quality_rank = quality_rankings.get(min_quality_tier, 0)

        for name, config in models.items():
            # Skip deprecated models if requested
            if exclude_deprecated and config.get("deprecated", False):
                continue

            # Check cost constraint
            if max_cost_per_1k_tokens is not None:
                if model_type == "chat_models":
                    model_cost = max(config.get("cost_input", 0), config.get("cost_output", 0))
                else:  # embedding_models
                    model_cost = config.get("cost", 0)

                if model_cost > max_cost_per_1k_tokens:
                    continue

            # Check quality tier
            if min_quality_tier is not None:
                model_quality = quality_rankings.get(config.get("quality_tier", "standard"), 0)
                if model_quality < min_quality_rank:
                    continue

            # Check required strengths
            if required_strengths is not None:
                model_strengths = config.get("strengths", [])
                if not any(strength in model_strengths for strength in required_strengths):
                    continue

            filtered_models[name] = config

        return filtered_models

    @classmethod
    def calculate_cost(cls, model_name: str, input_tokens: int, output_tokens: int = 0,
                      model_type: str = "chat_models") -> float:
        """Calculate cost for using a specific model"""
        config = cls.get_model_config(model_name, model_type)
        if not config:
            return 0.0

        if model_type == "chat_models":
            input_cost = (input_tokens / 1000) * config.get("cost_input", 0)
            output_cost = (output_tokens / 1000) * config.get("cost_output", 0)
            return input_cost + output_cost
        elif model_type == "embedding_models":
            return (input_tokens / 1000) * config.get("cost", 0)

        return 0.0

    @classmethod
    def get_fallback_model(cls, model_name: str, model_type: str = "chat_models") -> Optional[str]:
        """Get appropriate fallback model for a given model"""
        config = cls.get_model_config(model_name, model_type)
        if not config:
            return None

        provider = config.get("provider")

        # Define fallback chains (OpenAI only)
        fallback_chains = {
            "chat_models": {
                "openai": ["gpt-5", "gpt-5-mini", "gpt-5-nano"]
            },
            "embedding_models": {
                "openai": ["text-embedding-3-small"]  # Single model, no fallback needed
            }
        }

        chain = fallback_chains.get(model_type, {}).get(provider, [])

        # Return next model in chain
        try:
            current_index = chain.index(model_name)
            if current_index + 1 < len(chain):
                return chain[current_index + 1]
        except ValueError:
            pass

        # Return first model in chain if current not found
        return chain[0] if chain else None

    @classmethod
    def get_recommended_model(cls, use_case: str, strategy: str = "balanced") -> Optional[str]:
        """Get recommended model for specific use case and strategy"""

        # Get strategy configuration
        strategy_config = settings.MODEL_STRATEGIES.get(strategy, {})

        recommendations = {
            "job_parsing": strategy_config.get("job_parsing_model", "gpt-5"),
            "cv_generation": strategy_config.get("cv_generation_model", "gpt-5"),
            "embedding": strategy_config.get("embedding_model", "text-embedding-3-small"),
            "simple_task": "gpt-5-mini",
            "complex_analysis": "gpt-5",
            "premium_quality": "gpt-5",
        }

        return recommendations.get(use_case)

    @classmethod
    def validate_api_keys(cls) -> Dict[str, bool]:
        """Validate that required API keys are configured (OpenAI only)"""
        return {
            "openai": bool(getattr(settings, 'OPENAI_API_KEY', ''))
        }

    @classmethod
    def get_model_stats(cls) -> Dict[str, Any]:
        """Get statistics about available models"""
        chat_models = cls.MODELS.get("chat_models", {})
        embedding_models = cls.MODELS.get("embedding_models", {})

        # Filter out deprecated models
        active_chat = {k: v for k, v in chat_models.items() if not v.get("deprecated", False)}
        active_embedding = {k: v for k, v in embedding_models.items() if not v.get("deprecated", False)}

        return {
            "total_chat_models": len(active_chat),
            "total_embedding_models": len(active_embedding),
            "providers": list(set([
                config["provider"] for config in
                list(active_chat.values()) + list(active_embedding.values())
            ])),
            "cheapest_chat_model": min(active_chat.items(),
                                     key=lambda x: x[1]["cost_input"])[0] if active_chat else None,
            "cheapest_embedding_model": min(active_embedding.items(),
                                          key=lambda x: x[1]["cost"])[0] if active_embedding else None,
            "highest_quality_chat": max(active_chat.items(),
                                      key=lambda x: {"premium": 3, "high": 2, "medium": 1}.get(
                                          x[1]["quality_tier"], 0))[0] if active_chat else None,
        }