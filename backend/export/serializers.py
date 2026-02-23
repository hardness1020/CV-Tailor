from rest_framework import serializers
from .models import ExportJob, ExportTemplate, ExportAnalytics


class ExportRequestSerializer(serializers.Serializer):
    """Serializer for export requests."""

    format = serializers.ChoiceField(choices=['pdf', 'docx'])
    template_id = serializers.IntegerField(required=False)
    options = serializers.DictField(required=False, default=dict)
    sections = serializers.DictField(required=False, default=dict)
    watermark = serializers.DictField(required=False)

    def validate_format(self, value):
        """Validate export format."""
        if value not in ['pdf', 'docx']:
            raise serializers.ValidationError("Format must be 'pdf' or 'docx'")
        return value

    def validate_options(self, value):
        """Validate export options."""
        allowed_options = [
            'include_evidence',
            'evidence_format',
            'page_margins',
            'font_size',
            'color_scheme'
        ]

        for key in value.keys():
            if key not in allowed_options:
                raise serializers.ValidationError(f"Unknown option: {key}")

        # Validate specific option values
        if 'evidence_format' in value:
            allowed_formats = ['hyperlinks', 'footnotes', 'qr_codes']
            if value['evidence_format'] not in allowed_formats:
                raise serializers.ValidationError(f"Evidence format must be one of: {allowed_formats}")

        if 'page_margins' in value:
            allowed_margins = ['narrow', 'normal', 'wide']
            if value['page_margins'] not in allowed_margins:
                raise serializers.ValidationError(f"Page margins must be one of: {allowed_margins}")

        if 'font_size' in value:
            try:
                font_size = int(value['font_size'])
                if font_size < 10 or font_size > 14:
                    raise serializers.ValidationError("Font size must be between 10 and 14")
            except (ValueError, TypeError):
                raise serializers.ValidationError("Font size must be a number")

        if 'color_scheme' in value:
            allowed_schemes = ['monochrome', 'accent', 'full_color']
            if value['color_scheme'] not in allowed_schemes:
                raise serializers.ValidationError(f"Color scheme must be one of: {allowed_schemes}")

        return value

    def validate_sections(self, value):
        """Validate section configuration."""
        allowed_sections = [
            'include_professional_summary',
            'include_skills',
            'include_experience',
            'include_projects',
            'include_education',
            'include_certifications'
        ]

        for key in value.keys():
            if key not in allowed_sections:
                raise serializers.ValidationError(f"Unknown section: {key}")

        return value

    def validate_watermark(self, value):
        """Validate watermark configuration."""
        if value:
            if 'text' not in value:
                raise serializers.ValidationError("Watermark must include 'text' field")

            if 'opacity' in value:
                try:
                    opacity = float(value['opacity'])
                    if opacity < 0.1 or opacity > 0.5:
                        raise serializers.ValidationError("Watermark opacity must be between 0.1 and 0.5")
                except (ValueError, TypeError):
                    raise serializers.ValidationError("Watermark opacity must be a number")

        return value


class ExportJobSerializer(serializers.ModelSerializer):
    """Serializer for export jobs."""

    download_url = serializers.ReadOnlyField()

    class Meta:
        model = ExportJob
        fields = ('id', 'format', 'status', 'progress_percentage', 'error_message',
                 'file_size', 'download_count', 'download_url', 'created_at',
                 'completed_at', 'expires_at')
        read_only_fields = ('id', 'status', 'progress_percentage', 'error_message',
                           'file_size', 'download_count', 'download_url',
                           'created_at', 'completed_at', 'expires_at')


class ExportJobDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for export jobs."""

    download_url = serializers.ReadOnlyField()
    template_name = serializers.CharField(source='template.name', read_only=True)

    class Meta:
        model = ExportJob
        fields = ('id', 'generated_document', 'format', 'template', 'template_name',
                 'export_options', 'status', 'progress_percentage', 'error_message',
                 'file_path', 'file_size', 'download_count', 'download_url',
                 'created_at', 'completed_at', 'expires_at')
        read_only_fields = ('id', 'template_name', 'status', 'progress_percentage',
                           'error_message', 'file_path', 'file_size', 'download_count',
                           'download_url', 'created_at', 'completed_at', 'expires_at')


class ExportTemplateSerializer(serializers.ModelSerializer):
    """Serializer for export templates."""

    class Meta:
        model = ExportTemplate
        fields = ('id', 'name', 'category', 'description', 'preview_image_url',
                 'is_premium', 'is_active')
        read_only_fields = ('id',)


class ExportAnalyticsSerializer(serializers.ModelSerializer):
    """Serializer for export analytics."""

    class Meta:
        model = ExportAnalytics
        fields = ('id', 'export_job', 'event_type', 'metadata', 'created_at')
        read_only_fields = ('id', 'created_at')