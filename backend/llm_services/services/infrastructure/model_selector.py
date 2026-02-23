"""
Intelligent Model Selection Logic.
Implements ft-llm-003-flexible-model-selection.md
"""

import logging
from typing import Dict, Any, Optional, List
from django.conf import settings
from .model_registry import ModelRegistry
from ..base.settings_manager import SettingsManager

logger = logging.getLogger(__name__)


class IntelligentModelSelector:
    """Intelligently select optimal models based on task complexity and requirements"""

    def __init__(self):
        self.registry = ModelRegistry()
        self.settings_manager = SettingsManager()

        # Get model selection configuration from settings manager
        selection_config = self.settings_manager.get_model_selection_config()
        self.strategy = selection_config['strategy']
        self.strategy_config = selection_config['config']

    def select_model_for_task(self, task_type: str, context: Dict[str, Any]) -> str:
        """Select optimal model based on task type and context"""

        selection_methods = {
            "job_parsing": self._select_parsing_model,
            "cv_generation": self._select_generation_model,
            "content_unification": self._select_generation_model,  # Similar complexity to CV generation
            "embedding": self._select_embedding_model,
            "similarity_search": self._select_embedding_model,
            "job_embedding": self._select_embedding_model,
            "artifact_embedding": self._select_embedding_model,
        }

        selector_method = selection_methods.get(task_type, self._select_default_model)
        selected_model = selector_method(context)

        logger.info(f"Selected model '{selected_model}' for task '{task_type}' using strategy '{self.strategy}'")

        return selected_model

    def _select_parsing_model(self, context: Dict[str, Any]) -> str:
        """Select model for job description parsing"""
        job_description = context.get('job_description', '')
        company_name = context.get('company_name', '')
        role_title = context.get('role_title', '')

        # Calculate complexity score
        job_length = len(job_description.split())
        total_text_length = len(job_description) + len(company_name) + len(role_title)

        # For very long or complex job descriptions, use higher capability models
        if job_length > 1000 or total_text_length > 5000:
            return 'gpt-5'  # Best choice for long context handling

        # For short/simple job descriptions, use cost-effective models
        elif job_length < 200 and self.strategy == 'cost_optimized':
            return 'gpt-5-mini'  # Most cost efficient

        # Default to strategy-configured model
        return self.strategy_config.get('job_parsing_model', 'gpt-5')

    def _select_generation_model(self, context: Dict[str, Any]) -> str:
        """Select model for CV content generation"""
        artifacts = context.get('artifacts', [])
        job_data = context.get('job_data', {})
        preferences = context.get('preferences', {})

        # Calculate complexity score
        complexity_score = self._calculate_complexity_score(context)
        artifact_count = len(artifacts)

        # Determine if creative writing is required
        tone = preferences.get('tone', '')
        requires_creativity = tone in ['creative', 'engaging', 'storytelling']

        # High complexity or premium requirements
        if (complexity_score > 0.8 or
            artifact_count > 10 or
            requires_creativity or
            preferences.get('quality_preference') == 'premium'):

            return 'gpt-5'  # Best quality for complex tasks

        # Medium complexity
        elif complexity_score > 0.5 or artifact_count > 5:
            return 'gpt-5'  # Balanced performance

        # Low complexity and cost optimization
        elif complexity_score <= 0.5 and self.strategy == 'cost_optimized':
            return 'gpt-5-mini'  # Cost efficient

        # Default to strategy-configured model
        return self.strategy_config.get('cv_generation_model', 'gpt-5')

    def _select_embedding_model(self, context: Dict[str, Any]) -> str:
        """Select embedding model based on use case"""
        use_case = context.get('use_case', 'similarity')
        text_complexity = context.get('text_complexity', 'standard')
        user_preferences = context.get('user_preferences', {})

        # Premium use cases that benefit from higher dimensions
        premium_use_cases = [
            'semantic_analysis',
            'complex_matching',
            'detailed_similarity',
            'research_analysis'
        ]

        # Use single embedding model for all use cases (simplified per ADR-20251005)
        # text-embedding-3-small provides sufficient quality for all CV similarity matching
        return self.strategy_config.get('embedding_model', 'text-embedding-3-small')

    def _select_default_model(self, context: Dict[str, Any]) -> str:
        """Fallback model selection for unknown task types"""
        return 'gpt-5'

    def _calculate_complexity_score(self, context: Dict[str, Any]) -> float:
        """Calculate task complexity score (0.0 - 1.0)"""
        score = 0.0

        # Job description complexity
        job_description = context.get('job_description', '')
        job_data = context.get('job_data', {})

        if isinstance(job_data, dict):
            job_description = job_data.get('raw_content', job_description)

        job_word_count = len(job_description.split())
        if job_word_count > 1000:
            score += 0.3
        elif job_word_count > 500:
            score += 0.2
        elif job_word_count > 200:
            score += 0.1

        # Artifact complexity
        artifacts = context.get('artifacts', [])
        artifact_count = len(artifacts)

        # More artifacts = higher complexity
        score += min(0.3, artifact_count * 0.03)

        # Technical content complexity
        technical_indicators = ['API', 'framework', 'architecture', 'algorithm', 'database']
        job_text = job_description.lower()
        technical_matches = sum(1 for indicator in technical_indicators if indicator.lower() in job_text)
        score += min(0.2, technical_matches * 0.05)

        # Special requirements
        preferences = context.get('preferences', {})
        if isinstance(preferences, dict):
            if preferences.get('requires_creative_writing', False):
                score += 0.2
            if preferences.get('tone') == 'creative':
                score += 0.15
            if preferences.get('length') == 'detailed':
                score += 0.1

        # Multiple languages or international context
        if any(keyword in job_description.lower() for keyword in ['multilingual', 'international', 'global']):
            score += 0.1

        return min(1.0, score)

    def get_fallback_model(self, model_name: str, task_type: str) -> Optional[str]:
        """Get fallback model based on task type"""
        # Determine model type based on task type
        if task_type in ['embedding', 'similarity_search', 'job_embedding', 'artifact_embedding']:
            model_type = 'embedding_models'
        else:
            model_type = 'chat_models'

        return self.registry.get_fallback_model(model_name, model_type)

    def get_selection_reason(self, selected_model: str, context: Dict[str, Any]) -> str:
        """Generate human-readable reason for model selection"""
        complexity_score = self._calculate_complexity_score(context)
        artifact_count = len(context.get('artifacts', []))

        reasons = []

        # Strategy-based reason
        reasons.append(f"strategy_{self.strategy}")

        # Complexity-based reasons
        if complexity_score > 0.8:
            reasons.append("high_complexity")
        elif complexity_score > 0.5:
            reasons.append("medium_complexity")
        else:
            reasons.append("low_complexity")

        # Artifact count reasons
        if artifact_count > 10:
            reasons.append("many_artifacts")
        elif artifact_count > 5:
            reasons.append("multiple_artifacts")
        elif artifact_count <= 2:
            reasons.append("few_artifacts")

        # Model-specific reasons
        model_config = self.registry.get_model_config(selected_model)
        if model_config:
            if model_config.get('quality_tier') == 'premium':
                reasons.append("premium_quality")
            elif 'cost_efficiency' in model_config.get('strengths', []):
                reasons.append("cost_optimized")
            elif 'long_context' in model_config.get('strengths', []):
                reasons.append("long_context_handling")

        return "_".join(reasons[:4])  # Limit to 4 main reasons

    def get_fallback_model(self, failed_model: str, task_type: str) -> Optional[str]:
        """Get appropriate fallback model when primary model fails"""

        # Use registry's fallback logic
        registry_fallback = self.registry.get_fallback_model(failed_model)
        if registry_fallback:
            return registry_fallback

        # Strategy-based fallback
        strategy_fallback = self.strategy_config.get('fallback_model')
        if strategy_fallback and strategy_fallback != failed_model:
            return strategy_fallback

        # Task-specific fallbacks
        task_fallbacks = {
            'job_parsing': 'gpt-5-mini',  # Fast and cheap for parsing
            'cv_generation': 'gpt-5',     # Balanced for generation
            'embedding': 'text-embedding-3-small',  # Standard embedding
        }

        return task_fallbacks.get(task_type, 'gpt-5')

    def should_use_fallback(self, model_name: str, error_context: Dict[str, Any]) -> bool:
        """Determine if we should use fallback model based on error"""

        error_type = error_context.get('error_type', '')
        error_count = error_context.get('consecutive_errors', 0)

        # Immediate fallback conditions
        immediate_fallback_errors = [
            'rate_limit_exceeded',
            'model_not_available',
            'insufficient_quota',
            'authentication_failed'
        ]

        if error_type in immediate_fallback_errors:
            return True

        # Fallback after multiple errors
        if error_count >= 3:
            return True

        # Cost-based fallback
        if error_type == 'budget_exceeded':
            return True

        return False

    def optimize_for_budget(self, daily_spent: float, monthly_spent: float) -> Dict[str, str]:
        """Adjust model selection based on current budget usage"""

        budget_config = settings.MODEL_BUDGETS
        daily_budget = budget_config.get('daily_budget_usd', 50.0)
        monthly_budget = budget_config.get('monthly_budget_usd', 1000.0)

        daily_usage_ratio = daily_spent / daily_budget if daily_budget > 0 else 0
        monthly_usage_ratio = monthly_spent / monthly_budget if monthly_budget > 0 else 0

        # If budget is running high, suggest cost-optimized models
        if daily_usage_ratio > 0.8 or monthly_usage_ratio > 0.8:
            return {
                'job_parsing_model': 'gpt-5-mini',
                'cv_generation_model': 'gpt-5-mini',
                'embedding_model': 'text-embedding-3-small',
                'recommendation': 'budget_exceeded_cost_optimization'
            }
        elif daily_usage_ratio > 0.6 or monthly_usage_ratio > 0.6:
            return {
                'job_parsing_model': 'gpt-5-mini',
                'cv_generation_model': 'gpt-5',
                'embedding_model': 'text-embedding-3-small',
                'recommendation': 'budget_warning_partial_optimization'
            }

        # Budget is fine, return strategy defaults
        return {
            **self.strategy_config,
            'recommendation': 'budget_ok_normal_operation'
        }

    def get_performance_recommendations(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze performance data and recommend optimizations"""

        recommendations = {
            'model_changes': [],
            'strategy_changes': [],
            'cost_optimizations': [],
            'quality_improvements': []
        }

        # Analyze model performance
        for model_name, metrics in performance_data.items():
            avg_time = metrics.get('avg_processing_time_ms', 0)
            avg_cost = metrics.get('avg_cost_per_generation', 0)
            success_rate = metrics.get('success_rate', 1.0)
            quality_score = metrics.get('avg_quality_score', 0.8)

            # Performance issues
            if avg_time > 5000:  # > 5 seconds
                recommendations['model_changes'].append({
                    'model': model_name,
                    'issue': 'slow_performance',
                    'suggestion': 'Consider switching to faster model',
                    'alternative': self._find_faster_alternative(model_name)
                })

            # Cost issues
            if avg_cost > 0.20:  # > $0.20 per generation
                recommendations['cost_optimizations'].append({
                    'model': model_name,
                    'issue': 'high_cost',
                    'current_cost': avg_cost,
                    'suggestion': 'Consider cost-effective alternative',
                    'alternative': self._find_cheaper_alternative(model_name)
                })

            # Quality issues
            if quality_score < 0.75:
                recommendations['quality_improvements'].append({
                    'model': model_name,
                    'issue': 'low_quality',
                    'current_score': quality_score,
                    'suggestion': 'Consider higher-quality model',
                    'alternative': self._find_higher_quality_alternative(model_name)
                })

            # Reliability issues
            if success_rate < 0.95:
                recommendations['model_changes'].append({
                    'model': model_name,
                    'issue': 'low_reliability',
                    'success_rate': success_rate,
                    'suggestion': 'Model may be unstable, consider alternative'
                })

        return recommendations

    def _find_faster_alternative(self, model_name: str) -> Optional[str]:
        """Find a faster alternative to the given model"""
        current_config = self.registry.get_model_config(model_name)
        if not current_config:
            return None

        provider = current_config.get('provider')
        provider_models = self.registry.get_models_by_provider(provider)

        # Find models with better speed rank (lower number = faster)
        current_speed = current_config.get('speed_rank', 3)
        faster_models = [
            name for name, config in provider_models.items()
            if config.get('speed_rank', 3) < current_speed
        ]

        return faster_models[0] if faster_models else None

    def _find_cheaper_alternative(self, model_name: str) -> Optional[str]:
        """Find a cheaper alternative to the given model"""
        current_config = self.registry.get_model_config(model_name)
        if not current_config:
            return None

        current_cost = current_config.get('cost_input', 0)
        cheaper_models = self.registry.get_models_by_criteria(
            max_cost_per_1k_tokens=current_cost * 0.7,  # 30% cheaper
            exclude_deprecated=True
        )

        # Return the highest quality among cheaper models
        if cheaper_models:
            quality_rankings = {"premium": 3, "high": 2, "medium": 1, "standard": 1}
            best_model = max(cheaper_models.items(),
                           key=lambda x: quality_rankings.get(x[1].get('quality_tier', 'standard'), 0))
            return best_model[0]

        return None

    def _find_higher_quality_alternative(self, model_name: str) -> Optional[str]:
        """Find a higher quality alternative to the given model"""
        current_config = self.registry.get_model_config(model_name)
        if not current_config:
            return None

        current_quality = current_config.get('quality_tier', 'standard')
        quality_rankings = {"premium": 3, "high": 2, "medium": 1, "standard": 1}
        current_rank = quality_rankings.get(current_quality, 0)

        # Find models with higher quality
        all_models = self.registry.MODELS.get('chat_models', {})
        higher_quality_models = [
            name for name, config in all_models.items()
            if (quality_rankings.get(config.get('quality_tier', 'standard'), 0) > current_rank and
                not config.get('deprecated', False))
        ]

        # Return the most cost-effective among higher quality models
        if higher_quality_models:
            cheapest_model = min(
                [(name, all_models[name]) for name in higher_quality_models],
                key=lambda x: x[1].get('cost_input', float('inf'))
            )
            return cheapest_model[0]

        return None