from rest_framework import serializers
from .models import GeneratedDocument, JobDescription, GenerationFeedback, CVTemplate, BulletPoint


class GenerationRequestSerializer(serializers.Serializer):
    """Serializer for document generation requests (CV, cover letter, etc.)."""

    job_description = serializers.CharField()
    company_name = serializers.CharField(max_length=255, required=False)
    role_title = serializers.CharField(max_length=255, required=False)
    label_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    artifact_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=False,
        help_text='Manual artifact selection (ft-007). If provided, skip automatic ranking.'
    )
    template_id = serializers.IntegerField(default=1)
    custom_sections = serializers.DictField(required=False, default=dict)
    generation_preferences = serializers.DictField(required=False, default=dict)

    def validate_artifact_ids(self, value):
        """Validate artifact IDs list (ft-007)."""
        if value is None:
            return value

        if len(value) == 0:
            raise serializers.ValidationError("artifact_ids cannot be empty if provided")

        if len(value) > 50:
            raise serializers.ValidationError("Maximum 50 artifacts allowed")

        # Check for duplicates
        if len(value) != len(set(value)):
            raise serializers.ValidationError("Duplicate artifact IDs not allowed")

        return value

    def validate_generation_preferences(self, value):
        """Validate generation preferences structure."""
        allowed_tones = ['professional', 'technical', 'creative']
        allowed_lengths = ['concise', 'detailed']

        if 'tone' in value and value['tone'] not in allowed_tones:
            raise serializers.ValidationError(f"Tone must be one of: {allowed_tones}")

        if 'length' in value and value['length'] not in allowed_lengths:
            raise serializers.ValidationError(f"Length must be one of: {allowed_lengths}")

        return value

    def validate_custom_sections(self, value):
        """Validate custom sections structure."""
        allowed_sections = [
            'include_publications',
            'include_certifications',
            'include_volunteer'
        ]

        for key in value.keys():
            if key not in allowed_sections:
                raise serializers.ValidationError(f"Unknown section: {key}")

        return value


class GeneratedDocumentSerializer(serializers.ModelSerializer):
    """Serializer for generated documents."""

    # Map document_type → type for frontend consistency (aligns with Artifacts pattern)
    type = serializers.CharField(source='document_type', read_only=True)

    class Meta:
        model = GeneratedDocument
        fields = ('id', 'type', 'status', 'progress_percentage', 'content',
                 'metadata', 'error_message', 'user_rating', 'user_feedback',
                 'created_at', 'completed_at')
        read_only_fields = ('id', 'created_at')


class GeneratedDocumentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for generated documents list view.

    Excludes heavy fields like 'content' to optimize list view performance.
    Use GeneratedDocumentDetailSerializer for detail views.
    """

    # Map document_type → type for frontend consistency
    type = serializers.CharField(source='document_type', read_only=True)

    # Job information from related JobDescription
    jobTitle = serializers.SerializerMethodField()
    companyName = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedDocument
        fields = ('id', 'type', 'status', 'progress_percentage',
                 'error_message', 'user_rating', 'created_at', 'completed_at',
                 'jobTitle', 'companyName')
        read_only_fields = ('id', 'created_at')

    def get_jobTitle(self, obj):
        """Get job title from related JobDescription."""
        if obj.job_description:
            return obj.job_description.role_title
        return None

    def get_companyName(self, obj):
        """Get company name from related JobDescription."""
        if obj.job_description:
            return obj.job_description.company_name
        return None


class GeneratedDocumentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for generated documents with full content."""

    # Map document_type → type for frontend consistency (aligns with Artifacts pattern)
    type = serializers.CharField(source='document_type', read_only=True)

    class Meta:
        model = GeneratedDocument
        fields = ('id', 'type', 'job_description_hash', 'label_ids',
                 'template_id', 'custom_sections', 'generation_preferences',
                 'content', 'metadata', 'status', 'progress_percentage',
                 'error_message', 'artifacts_used', 'model_version',
                 'generation_time_ms', 'user_rating', 'user_feedback',
                 'created_at', 'completed_at', 'expires_at')
        read_only_fields = ('id', 'job_description_hash', 'artifacts_used',
                           'model_version', 'generation_time_ms', 'created_at',
                           'completed_at', 'expires_at')


class JobDescriptionSerializer(serializers.ModelSerializer):
    """Serializer for job descriptions."""

    class Meta:
        model = JobDescription
        fields = ('id', 'content_hash', 'raw_content', 'parsed_data',
                 'company_name', 'role_title', 'parsing_confidence', 'created_at')
        read_only_fields = ('id', 'content_hash', 'parsed_data', 'parsing_confidence',
                           'created_at')


class GenerationFeedbackSerializer(serializers.ModelSerializer):
    """Serializer for generation feedback."""

    class Meta:
        model = GenerationFeedback
        fields = ('id', 'generation', 'feedback_type', 'feedback_data', 'created_at')
        read_only_fields = ('id', 'created_at')


class CVTemplateSerializer(serializers.ModelSerializer):
    """Serializer for CV templates."""

    class Meta:
        model = CVTemplate
        fields = ('id', 'name', 'category', 'description', 'preview_image_url',
                 'template_config', 'is_premium', 'is_active')
        read_only_fields = ('id', 'template_config')


class DocumentRatingSerializer(serializers.Serializer):
    """Serializer for rating generated documents."""

    rating = serializers.IntegerField(min_value=1, max_value=10)
    feedback = serializers.CharField(required=False, allow_blank=True)

    def validate_rating(self, value):
        if value < 1 or value > 10:
            raise serializers.ValidationError("Rating must be between 1 and 10")
        return value


class CVMetadataUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating CV metadata (template, custom sections, preferences)."""

    class Meta:
        model = GeneratedDocument
        fields = ('template_id', 'custom_sections', 'generation_preferences')

    def validate_template_id(self, value):
        """Validate template exists and is active."""
        if value:
            try:
                template = CVTemplate.objects.get(id=value)
                if not template.is_active:
                    raise serializers.ValidationError("Selected template is not active")
            except CVTemplate.DoesNotExist:
                raise serializers.ValidationError("Template does not exist")
        return value

    def validate_custom_sections(self, value):
        """Validate custom sections structure."""
        allowed_sections = [
            'include_publications',
            'include_certifications',
            'include_volunteer'
        ]

        for key in value.keys():
            if key not in allowed_sections:
                raise serializers.ValidationError(f"Unknown section: {key}")

        return value

    def validate_generation_preferences(self, value):
        """Validate generation preferences structure."""
        allowed_tones = ['professional', 'technical', 'creative']
        allowed_lengths = ['concise', 'detailed']

        if 'tone' in value and value['tone'] not in allowed_tones:
            raise serializers.ValidationError(f"Tone must be one of: {allowed_tones}")

        if 'length' in value and value['length'] not in allowed_lengths:
            raise serializers.ValidationError(f"Length must be one of: {allowed_lengths}")

        return value


# ===== ft-006 Bullet Point Serializers =====
# Added for three-bullets-per-artifact feature
# Reference: spec-20251001-ft006-implementation.md


class JobContextSerializer(serializers.Serializer):
    """
    Serializer for job context used in bullet generation.

    Job context provides the requirements and context needed to
    tailor bullets to specific job postings.
    """

    role_title = serializers.CharField(
        max_length=255,
        help_text='Job role title (e.g., "Senior Software Engineer")'
    )
    key_requirements = serializers.ListField(
        child=serializers.CharField(max_length=100),
        help_text='Must-have skills and requirements',
        allow_empty=False
    )
    preferred_skills = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
        help_text='Nice-to-have skills'
    )
    company_name = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text='Company name for context'
    )
    seniority_level = serializers.ChoiceField(
        choices=['entry', 'mid', 'senior', 'staff', 'principal', 'executive'],
        required=False,
        help_text='Job seniority level'
    )
    industry = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        help_text='Industry context (e.g., "fintech", "healthtech")'
    )


class BulletGenerationRequestSerializer(serializers.Serializer):
    """
    Serializer for bullet generation requests.

    Validates input for POST /api/v1/generations/{generation_id}/bullets/

    ADR-038: Updated to use generation-scoped endpoints.
    - artifact_id moved from URL to body
    - cv_generation_id removed (now in URL path as generation_id)
    """

    artifact_id = serializers.IntegerField(
        help_text='Artifact to generate bullets for'
    )
    job_context = JobContextSerializer(
        help_text='Job requirements and context for bullet generation'
    )
    regenerate = serializers.BooleanField(
        default=False,
        help_text='Force regeneration even if bullets exist'
    )
    optimization_level = serializers.ChoiceField(
        choices=['conservative', 'standard', 'aggressive'],
        default='standard',
        help_text='Bullet optimization aggressiveness'
    )

    def validate(self, data):
        """Cross-field validation"""
        # Ensure key_requirements is not empty
        job_context = data.get('job_context', {})
        if not job_context.get('key_requirements'):
            raise serializers.ValidationError({
                'job_context': {
                    'key_requirements': 'At least one key requirement is required'
                }
            })
        return data


class BulletPointSerializer(serializers.ModelSerializer):
    """
    Serializer for individual bullet points.

    Converted to ModelSerializer now that BulletPoint model exists.
    """

    # Override ForeignKey fields to return IDs instead of nested objects
    artifact = serializers.PrimaryKeyRelatedField(read_only=True)
    cv_generation = serializers.PrimaryKeyRelatedField(read_only=True)
    approved_by = serializers.PrimaryKeyRelatedField(read_only=True)
    position = serializers.IntegerField(
        min_value=1,
        max_value=3,
        help_text='Position in 3-bullet set (1, 2, or 3)'
    )
    bullet_type = serializers.ChoiceField(
        choices=['achievement', 'technical', 'impact'],
        help_text='Structured hierarchy type'
    )
    text = serializers.CharField(
        min_length=60,
        max_length=150,
        help_text='Bullet point text (60-150 characters)'
    )
    keywords = serializers.ListField(
        child=serializers.CharField(max_length=50),
        default=list,
        help_text='ATS-relevant keywords'
    )
    metrics = serializers.DictField(
        default=dict,
        help_text='Quantified metrics (e.g., {"performance_improvement": "40%"})'
    )
    confidence_score = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        help_text='LLM confidence in bullet quality'
    )
    quality_score = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        default=0.0,
        help_text='Validation quality score'
    )
    has_action_verb = serializers.BooleanField(
        default=False,
        help_text='Starts with strong action verb'
    )
    keyword_relevance_score = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        default=0.0,
        help_text='Job keyword relevance score'
    )
    user_approved = serializers.BooleanField(
        default=False,
        read_only=True,
        help_text='User explicitly approved this bullet'
    )
    user_edited = serializers.BooleanField(
        default=False,
        read_only=True,
        help_text='User manually edited this bullet'
    )
    created_at = serializers.DateTimeField(
        read_only=True,
        help_text='Creation timestamp'
    )

    # ft-030: Anti-Hallucination Verification Fields
    confidence = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        read_only=True,
        required=False,
        help_text='Overall confidence score (weighted: extraction 30%, generation 20%, verification 50%)'
    )
    confidence_tier = serializers.ChoiceField(
        choices=['HIGH', 'MEDIUM', 'LOW', 'CRITICAL'],
        read_only=True,
        required=False,
        help_text='Confidence tier classification (HIGH ≥0.85, MEDIUM ≥0.70, LOW ≥0.50, CRITICAL <0.50)'
    )
    requires_review = serializers.BooleanField(
        default=False,
        read_only=True,
        help_text='Flagged for user review (LOW/CRITICAL tiers)'
    )
    is_blocked = serializers.BooleanField(
        default=False,
        read_only=True,
        help_text='Blocked from finalization (CRITICAL tier only)'
    )
    verification_status = serializers.ChoiceField(
        choices=['VERIFIED', 'INFERRED', 'UNSUPPORTED', 'PENDING', 'ERROR'],
        default='PENDING',
        read_only=True,
        help_text='Verification classification result'
    )
    verification_confidence = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        read_only=True,
        required=False,
        help_text='Verification layer confidence (0.0-1.0)'
    )
    hallucination_risk = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'critical'],
        read_only=True,
        required=False,
        help_text='Hallucination risk assessment'
    )
    source_attribution = serializers.ListField(
        child=serializers.DictField(),
        default=list,
        read_only=True,
        help_text='Source quotes with attribution ({"quote": "...", "location": "...", "confidence": 0.9})'
    )
    claim_results = serializers.ListField(
        child=serializers.DictField(),
        default=list,
        read_only=True,
        help_text='Verified claims with evidence ({"claim": "...", "classification": "VERIFIED", "evidence": "..."})'
    )
    confidence_breakdown = serializers.DictField(
        default=dict,
        read_only=True,
        help_text='Confidence calculation breakdown (base, penalties, final)'
    )

    # ft-030: Review Workflow Fields
    is_approved = serializers.BooleanField(
        default=False,
        read_only=True,
        help_text='User approved after review (ft-030)'
    )
    approved_by = serializers.IntegerField(
        source='approved_by_id',
        read_only=True,
        required=False,
        allow_null=True,
        help_text='User ID who approved this bullet'
    )
    approved_at = serializers.DateTimeField(
        read_only=True,
        required=False,
        allow_null=True,
        help_text='Timestamp of approval'
    )

    def validate(self, data):
        """Validate bullet structure"""
        # Validate hierarchy based on position
        expected_types = {
            1: 'achievement',
            2: 'technical',
            3: 'impact'
        }
        position = data.get('position')
        bullet_type = data.get('bullet_type')

        if position in expected_types:
            if bullet_type != expected_types[position]:
                raise serializers.ValidationError(
                    f"Position {position} must be '{expected_types[position]}' type, "
                    f"got '{bullet_type}'"
                )

        return data

    class Meta:
        model = BulletPoint
        fields = '__all__'


class BulletGenerationResponseSerializer(serializers.Serializer):
    """
    Serializer for bullet generation responses.

    Used for both immediate (200 OK) and async (202 Accepted) responses.
    """

    # Async response fields (202 Accepted)
    status = serializers.ChoiceField(
        choices=['pending', 'processing', 'completed', 'failed', 'needs_review'],
        help_text='Generation status'
    )
    artifact_id = serializers.IntegerField(
        help_text='Artifact ID'
    )
    estimated_completion_time = serializers.DateTimeField(
        required=False,
        help_text='Estimated completion time'
    )
    generation_id = serializers.UUIDField(
        required=False,
        help_text='Generation UUID for status polling (ft-026)'
    )
    status_endpoint = serializers.CharField(
        required=False,
        help_text='URL endpoint for polling generation status (ft-026)'
    )
    message = serializers.CharField(
        required=False,
        help_text='Status message'
    )

    # Immediate response fields (200 OK)
    bullet_points = BulletPointSerializer(
        many=True,
        required=False,
        help_text='Generated bullet points (if completed)'
    )
    metadata = serializers.DictField(
        required=False,
        help_text='Generation metadata (timing, costs, model used)'
    )


class BulletApprovalSerializer(serializers.Serializer):
    """
    Serializer for bullet approval/rejection requests.

    Used for POST /api/v1/cv/artifacts/{id}/bullets/approve/
    """

    bullet_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text='List of bullet IDs to approve/reject/edit'
    )
    action = serializers.ChoiceField(
        choices=['approve', 'reject', 'edit'],
        help_text='Action to take on bullets'
    )
    edits = serializers.DictField(
        child=serializers.CharField(min_length=60, max_length=150),
        required=False,
        default=dict,
        help_text='Edited text for bullets (key=bullet_id, value=new_text). Required if action="edit"'
    )
    feedback = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text='Optional user feedback'
    )

    def validate(self, data):
        """Cross-field validation"""
        action = data.get('action')
        edits = data.get('edits', {})

        # If action is 'edit', edits must be provided
        if action == 'edit':
            if not edits:
                raise serializers.ValidationError({
                    'edits': 'Edits are required when action is "edit"'
                })

            # Validate edit keys match bullet_ids
            bullet_ids = set(str(bid) for bid in data.get('bullet_ids', []))
            edit_ids = set(edits.keys())

            if not edit_ids.issubset(bullet_ids):
                raise serializers.ValidationError({
                    'edits': 'Edit keys must match bullet_ids'
                })

        return data


class BulletValidationSerializer(serializers.Serializer):
    """
    Serializer for bullet validation requests.

    Used for POST /api/v1/cv/bullets/validate/
    """

    bullets = serializers.ListField(
        child=serializers.DictField(),
        help_text='List of bullets to validate (text and type required)'
    )
    job_context = JobContextSerializer(
        help_text='Job context for keyword validation'
    )

    def validate_bullets(self, value):
        """Validate bullets structure"""
        if len(value) != 3:
            raise serializers.ValidationError("Exactly 3 bullets required for validation")

        # Validate each bullet has required fields
        for i, bullet in enumerate(value):
            if 'text' not in bullet:
                raise serializers.ValidationError(f"Bullet {i+1} missing 'text' field")
            if 'bullet_type' not in bullet:
                raise serializers.ValidationError(f"Bullet {i+1} missing 'bullet_type' field")
            if bullet['bullet_type'] not in ['achievement', 'technical', 'impact']:
                raise serializers.ValidationError(
                    f"Bullet {i+1} has invalid bullet_type: {bullet['bullet_type']}"
                )

        return value


class ValidationResultSerializer(serializers.Serializer):
    """
    Serializer for validation results.

    Used in validation response.
    """

    is_valid = serializers.BooleanField(
        help_text='Overall validation passed'
    )
    overall_quality_score = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        help_text='Average quality score'
    )
    structure_valid = serializers.BooleanField(
        help_text='Structure requirements met'
    )
    bullet_scores = serializers.ListField(
        child=serializers.FloatField(min_value=0.0, max_value=1.0),
        help_text='Quality scores for each bullet'
    )
    issues = serializers.ListField(
        child=serializers.CharField(),
        help_text='List of validation issues'
    )
    suggestions = serializers.ListField(
        child=serializers.CharField(),
        help_text='List of improvement suggestions'
    )
    similarity_pairs = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField()),
        help_text='Redundant bullet pairs [(idx1, idx2, similarity), ...]'
    )
    ats_compatibility_score = serializers.FloatField(
        min_value=0.0,
        max_value=1.0,
        required=False,
        help_text='ATS compatibility score'
    )