from rest_framework import serializers
from django.db import transaction
from .models import Artifact, Evidence, ArtifactProcessingJob, UploadedFile


class EvidenceSerializer(serializers.ModelSerializer):
    enhanced_content = serializers.SerializerMethodField()

    class Meta:
        model = Evidence
        fields = ('id', 'url', 'evidence_type', 'description', 'file_path', 'file_size',
                 'mime_type', 'validation_metadata', 'last_validated', 'is_accessible',
                 'created_at', 'updated_at', 'enhanced_content')
        read_only_fields = ('id', 'validation_metadata', 'last_validated', 'is_accessible',
                           'created_at', 'updated_at', 'enhanced_content')

    def get_enhanced_content(self, obj):
        """
        Get enriched content from EnhancedEvidence if available.

        Uses prefetched data when available (from queryset with prefetch_related)
        to avoid N+1 queries. Falls back to database query if not prefetched.
        """
        try:
            # Import here to avoid circular dependency
            from llm_services.models import EnhancedEvidence

            # Try to use prefetched relation first (optimized path)
            try:
                enhanced = obj.enhanced_version  # Access prefetched reverse relation
            except EnhancedEvidence.DoesNotExist:
                # No enhanced evidence exists for this evidence
                return None

            if enhanced and enhanced.processed_content:
                return {
                    'summary': enhanced.processed_content.get('summary', ''),
                    'technologies': enhanced.processed_content.get('technologies', []),
                    'achievements': enhanced.processed_content.get('achievements', []),
                    'metrics': enhanced.processed_content.get('metrics', []),
                    'confidence': enhanced.processing_confidence,
                    'project_type': enhanced.processed_content.get('project_type', ''),
                }
            return None
        except Exception as e:
            # Log error but don't fail serialization
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to get enhanced content for evidence {obj.id}: {e}")
            return None


class ArtifactSerializer(serializers.ModelSerializer):
    evidence_links = EvidenceSerializer(many=True, read_only=True, source='evidence')

    class Meta:
        model = Artifact
        fields = ('id', 'title', 'description', 'artifact_type', 'start_date', 'end_date',
                 'technologies', 'collaborators', 'extracted_metadata', 'evidence_links',
                 'user_context', 'unified_description', 'enriched_technologies', 'enriched_achievements',
                 'processing_confidence', 'status', 'wizard_completed_at', 'last_wizard_step',
                 'created_at', 'updated_at')
        read_only_fields = ('id', 'extracted_metadata', 'unified_description',
                           'enriched_technologies', 'enriched_achievements',
                           'processing_confidence', 'status', 'wizard_completed_at', 'last_wizard_step',
                           'created_at', 'updated_at')


class ArtifactUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Artifact
        fields = ('id', 'title', 'description', 'user_context', 'artifact_type', 'start_date', 'end_date',
                 'technologies', 'collaborators', 'last_wizard_step', 'created_at', 'updated_at')
        read_only_fields = ('id', 'extracted_metadata', 'created_at', 'updated_at')

    def validate(self, data):
        if data.get('end_date') and data.get('start_date'):
            if data['end_date'] < data['start_date']:
                raise serializers.ValidationError(
                    "End date must be after start date"
                )
        return data


class EvidenceCreateSerializer(serializers.ModelSerializer):
    # Accept both evidence_type (backend) and link_type (frontend) for backward compatibility
    link_type = serializers.CharField(write_only=True, required=False)
    evidence_type = serializers.ChoiceField(
        choices=['github', 'document'],
        required=False,
        help_text='Only github and document types are supported'
    )

    class Meta:
        model = Evidence
        fields = ('url', 'evidence_type', 'description', 'link_type')

    def validate(self, data):
        # Handle link_type → evidence_type mapping for frontend compatibility
        if 'link_type' in data and 'evidence_type' not in data:
            data['evidence_type'] = data.pop('link_type')
        elif 'link_type' in data:
            # Both provided - remove link_type, use evidence_type
            data.pop('link_type')

        # Ensure evidence_type is present
        if 'evidence_type' not in data:
            raise serializers.ValidationError("Either 'evidence_type' or 'link_type' is required")

        return data

    def validate_evidence_type(self, value):
        """Validate that only supported evidence types are used"""
        if value not in ['github', 'document']:
            raise serializers.ValidationError(
                f"Evidence type '{value}' is not supported. Use 'github' or 'document'."
            )
        return value

    def validate_url(self, value):
        # Basic URL validation - could be enhanced with accessibility check
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value


class EvidenceUpdateSerializer(serializers.ModelSerializer):
    # Accept both evidence_type (backend) and link_type (frontend) for backward compatibility
    link_type = serializers.CharField(write_only=True, required=False)
    evidence_type = serializers.ChoiceField(
        choices=['github', 'document'],
        required=False,
        help_text='Only github and document types are supported'
    )

    class Meta:
        model = Evidence
        fields = ('url', 'evidence_type', 'description', 'link_type')

    def validate(self, data):
        # Handle link_type → evidence_type mapping for frontend compatibility
        if 'link_type' in data and 'evidence_type' not in data:
            data['evidence_type'] = data.pop('link_type')
        elif 'link_type' in data:
            # Both provided - remove link_type, use evidence_type
            data.pop('link_type')

        return data

    def validate_evidence_type(self, value):
        """Validate that only supported evidence types are used"""
        if value not in ['github', 'document']:
            raise serializers.ValidationError(
                f"Evidence type '{value}' is not supported. Use 'github' or 'document'."
            )
        return value

    def validate_url(self, value):
        # Basic URL validation - could be enhanced with accessibility check
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value


class ArtifactCreateSerializer(serializers.ModelSerializer):
    # Make description optional - AI will generate unified_description from evidence + user_context
    description = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Optional brief summary (AI will enhance this using evidence)'
    )

    evidence_links = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=False
    )

    class Meta:
        model = Artifact
        fields = ('id', 'title', 'description', 'user_context', 'artifact_type', 'start_date', 'end_date',
                 'technologies', 'collaborators', 'evidence_links')
        read_only_fields = ('id',)

    def create(self, validated_data):
        evidence_links_data = validated_data.pop('evidence_links', [])
        # Set initial status to 'draft' for wizard workflow (ft-045)
        artifact = Artifact.objects.create(
            user=self.context['request'].user,
            status='draft',
            **validated_data
        )

        # Create evidence links with validation
        for link_data in evidence_links_data:
            # Map 'type' to 'evidence_type' if present
            if 'type' in link_data:
                link_data['evidence_type'] = link_data.pop('type')

            # Validate evidence type
            evidence_type = link_data.get('evidence_type')
            if evidence_type and evidence_type not in ['github', 'document']:
                raise serializers.ValidationError({
                    'evidence_links': f"Evidence type '{evidence_type}' is not supported. Use 'github' or 'document'."
                })

            # Additional validation for evidence type constraints
            if evidence_type == 'github':
                url = link_data.get('url', '')
                if 'github.com' not in url.lower():
                    raise serializers.ValidationError({
                        'evidence_links': 'GitHub evidence must be a github.com URL'
                    })
                if link_data.get('file_path'):
                    raise serializers.ValidationError({
                        'evidence_links': 'GitHub evidence cannot have uploaded files (must be URL only)'
                    })
            elif evidence_type == 'document':
                if not link_data.get('file_path'):
                    raise serializers.ValidationError({
                        'evidence_links': 'Document evidence requires an uploaded file (file_path required)'
                    })

            Evidence.objects.create(artifact=artifact, **link_data)

        return artifact


class ArtifactProcessingJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArtifactProcessingJob
        fields = ('id', 'artifact', 'status', 'progress_percentage', 'error_message',
                 'metadata_extracted', 'evidence_validation_results', 'created_at', 'completed_at')
        read_only_fields = ('id', 'created_at', 'completed_at')


class UploadedFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedFile
        fields = ('id', 'file', 'original_filename', 'file_size', 'mime_type',
                 'is_processed', 'processing_error', 'created_at')
        read_only_fields = ('id', 'original_filename', 'file_size', 'mime_type', 'is_processed', 'processing_error',
                           'created_at')

    def create(self, validated_data):
        file_obj = validated_data['file']
        validated_data['original_filename'] = file_obj.name
        validated_data['file_size'] = file_obj.size
        validated_data['mime_type'] = getattr(file_obj, 'content_type', 'application/octet-stream')
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class EnrichedContentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating enriched content fields.
    Allows users to manually edit LLM-generated enriched content.
    Note: user_context is intentionally excluded as it's edited via ArtifactUpdateSerializer.
    """

    class Meta:
        model = Artifact
        fields = ('unified_description', 'enriched_technologies', 'enriched_achievements')

    def validate_unified_description(self, value):
        """Validate unified description"""
        if value and len(value) > 5000:
            raise serializers.ValidationError("Unified description must be less than 5000 characters")
        return value

    def validate_enriched_technologies(self, value):
        """Validate enriched technologies list"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Enriched technologies must be a list")

        if len(value) > 50:
            raise serializers.ValidationError("Maximum 50 technologies allowed")

        # Ensure all items are strings
        if not all(isinstance(tech, str) for tech in value):
            raise serializers.ValidationError("All technologies must be strings")

        return value

    def validate_enriched_achievements(self, value):
        """Validate enriched achievements list"""
        if not isinstance(value, list):
            raise serializers.ValidationError("Enriched achievements must be a list")

        if len(value) > 20:
            raise serializers.ValidationError("Maximum 20 achievements allowed")

        # Ensure all items are strings
        if not all(isinstance(achievement, str) for achievement in value):
            raise serializers.ValidationError("All achievements must be strings")

        return value