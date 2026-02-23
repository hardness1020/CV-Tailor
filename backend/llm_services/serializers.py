"""
DRF serializers for LLM services API endpoints.
"""

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import models
from decimal import Decimal
from .models import (
    ModelPerformanceMetric,
    EnhancedEvidence,
    ModelCostTracking,
    CircuitBreakerState
)

User = get_user_model()


class ModelPerformanceMetricSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = ModelPerformanceMetric
        fields = [
            'id', 'model_name', 'task_type', 'processing_time_ms',
            'tokens_used', 'cost_usd', 'quality_score', 'success',
            'complexity_score', 'selection_strategy', 'fallback_used',
            'metadata', 'created_at', 'user_email'
        ]
        read_only_fields = ['id', 'created_at', 'user_email']


class CircuitBreakerStateSerializer(serializers.ModelSerializer):
    state_display = serializers.CharField(source='get_state_display', read_only=True)
    is_healthy = serializers.SerializerMethodField()

    class Meta:
        model = CircuitBreakerState
        fields = [
            'model_name', 'failure_count', 'last_failure', 'state',
            'state_display', 'failure_threshold', 'timeout_duration',
            'created_at', 'updated_at', 'is_healthy'
        ]
        read_only_fields = ['created_at', 'updated_at', 'state_display', 'is_healthy']

    def get_is_healthy(self, obj):
        return obj.state == 'closed'


class ModelCostTrackingSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = ModelCostTracking
        fields = [
            'id', 'user_email', 'date', 'model_name', 'total_cost_usd',
            'generation_count', 'avg_cost_per_generation',
            'total_tokens_used', 'avg_tokens_per_generation'
        ]
        read_only_fields = ['id', 'user_email']


class EnhancedEvidenceSerializer(serializers.ModelSerializer):
    user_email = serializers.CharField(source='user.email', read_only=True)
    evidence_id = serializers.IntegerField(source='evidence.id', read_only=True)

    class Meta:
        model = EnhancedEvidence
        fields = [
            'id', 'user_email', 'evidence', 'evidence_id', 'title', 'content_type',
            'raw_content', 'processed_content', 'processing_confidence',
            'langchain_version', 'processing_strategy', 'total_chunks',
            'processing_time_ms', 'llm_model_used', 'created_at', 'updated_at',
            'document_category', 'classification_confidence',
            'accepted', 'accepted_at', 'review_notes'  # ft-045: Evidence review fields
        ]
        read_only_fields = [
            'id', 'user_email', 'created_at', 'updated_at',
            'evidence', 'evidence_id', 'raw_content', 'processed_content',
            'processing_confidence'
        ]


class EnhancedEvidenceUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating enriched content (user-editable fields only)"""

    # Validate nested processed_content fields
    processed_content = serializers.JSONField(required=False)

    class Meta:
        model = EnhancedEvidence
        fields = ['processed_content']

    def validate_processed_content(self, value):
        """Validate processed_content structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("processed_content must be a dictionary")

        # Validate allowed fields
        allowed_fields = {'summary', 'description', 'technologies', 'achievements', 'skills'}
        for key in value.keys():
            if key not in allowed_fields:
                # Allow other fields to pass through but validate editable ones
                pass

        # Validate list fields are actually lists of strings
        list_fields = ['technologies', 'achievements', 'skills']
        for field in list_fields:
            if field in value:
                if not isinstance(value[field], list):
                    raise serializers.ValidationError(f"{field} must be a list")
                if not all(isinstance(item, str) for item in value[field]):
                    raise serializers.ValidationError(f"All items in {field} must be strings")

        # Validate string fields
        string_fields = ['summary', 'description']
        for field in string_fields:
            if field in value:
                if not isinstance(value[field], str):
                    raise serializers.ValidationError(f"{field} must be a string")

        return value

    def update(self, instance, validated_data):
        """Update only the processed_content fields"""
        if 'processed_content' in validated_data:
            # Merge with existing processed_content to preserve other fields
            existing_content = instance.processed_content or {}
            new_content = validated_data['processed_content']

            # Update only the provided fields
            for key, value in new_content.items():
                existing_content[key] = value

            instance.processed_content = existing_content
            instance.save()

        return instance


class ModelStatsSerializer(serializers.Serializer):
    """Aggregated model statistics"""
    model_name = serializers.CharField()
    total_requests = serializers.IntegerField()
    success_rate = serializers.FloatField()
    avg_processing_time_ms = serializers.FloatField()
    total_cost_usd = serializers.DecimalField(max_digits=10, decimal_places=6)
    avg_quality_score = serializers.FloatField(allow_null=True)
    last_used = serializers.DateTimeField()


class ModelSelectionRequestSerializer(serializers.Serializer):
    """Request serializer for model selection endpoint"""
    task_type = serializers.ChoiceField(choices=[
        'job_parsing', 'cv_generation'
    ])
    complexity_score = serializers.FloatField(min_value=0.0, max_value=1.0, required=False)
    user_budget = serializers.DecimalField(max_digits=10, decimal_places=6, min_value=Decimal('0.000001'), required=False)
    strategy = serializers.ChoiceField(
        choices=['cost_optimized', 'balanced', 'performance_first'],
        required=False
    )


class ModelSelectionResponseSerializer(serializers.Serializer):
    """Response serializer for model selection endpoint"""
    selected_model = serializers.CharField()
    reasoning = serializers.CharField()
    estimated_cost_usd = serializers.DecimalField(max_digits=10, decimal_places=6)
    fallback_models = serializers.ListField(child=serializers.CharField())


class SystemHealthSerializer(serializers.Serializer):
    """Overall system health status"""
    healthy_models = serializers.IntegerField()
    unhealthy_models = serializers.IntegerField()
    circuit_breakers_open = serializers.IntegerField()
    total_cost_today = serializers.DecimalField(max_digits=10, decimal_places=6)
    avg_response_time_ms = serializers.FloatField()
    success_rate = serializers.FloatField()