"""
Unit tests for enrichment-related serializers
"""

from django.test import TestCase, tag
from django.contrib.auth import get_user_model

from artifacts.models import Artifact
from artifacts.serializers import ArtifactSerializer, EnrichedContentUpdateSerializer

User = get_user_model()


@tag('medium', 'integration', 'artifacts', 'serializers')
class ArtifactSerializerEnrichmentTests(TestCase):
    """Test that ArtifactSerializer includes enriched fields"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_artifact_serializer_includes_enriched_fields(self):
        """Test ArtifactSerializer exposes enriched fields"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Original description',
            artifact_type='project',
            technologies=['Python'],
            unified_description='AI-enhanced description',
            enriched_technologies=['Python', 'Django', 'PostgreSQL'],
            enriched_achievements=['Improved performance by 50%'],
            processing_confidence=0.85
        )

        serializer = ArtifactSerializer(artifact)

        # Verify enriched fields are in serialized data
        self.assertIn('unified_description', serializer.data)
        self.assertIn('enriched_technologies', serializer.data)
        self.assertIn('enriched_achievements', serializer.data)
        self.assertIn('processing_confidence', serializer.data)

        # Verify values are correct
        self.assertEqual(serializer.data['unified_description'], 'AI-enhanced description')
        self.assertEqual(len(serializer.data['enriched_technologies']), 3)
        self.assertEqual(len(serializer.data['enriched_achievements']), 1)
        self.assertEqual(serializer.data['processing_confidence'], 0.85)

    def test_artifact_serializer_enriched_fields_read_only(self):
        """Test enriched fields are read-only in ArtifactSerializer"""
        serializer = ArtifactSerializer()

        # Verify enriched fields are in read-only fields
        read_only_fields = serializer.Meta.read_only_fields
        self.assertIn('unified_description', read_only_fields)
        self.assertIn('enriched_technologies', read_only_fields)
        self.assertIn('enriched_achievements', read_only_fields)
        self.assertIn('processing_confidence', read_only_fields)


@tag('medium', 'integration', 'artifacts', 'serializers')
class EnrichedContentUpdateSerializerTests(TestCase):
    """Test cases for EnrichedContentUpdateSerializer"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Original description',
            artifact_type='project',
            unified_description='AI description',
            enriched_technologies=['Python'],
            enriched_achievements=['Achievement 1']
        )

    def test_update_unified_description(self):
        """Test updating unified description"""
        data = {
            'unified_description': 'Manually edited AI description'
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_artifact = serializer.save()

        self.assertEqual(updated_artifact.unified_description, 'Manually edited AI description')

    def test_update_enriched_technologies(self):
        """Test updating enriched technologies"""
        data = {
            'enriched_technologies': ['Python', 'Django', 'React', 'PostgreSQL']
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_artifact = serializer.save()

        self.assertEqual(len(updated_artifact.enriched_technologies), 4)
        self.assertIn('React', updated_artifact.enriched_technologies)

    def test_update_enriched_achievements(self):
        """Test updating enriched achievements"""
        data = {
            'enriched_achievements': [
                'Achievement 1',
                'Achievement 2',
                'Improved performance by 50%'
            ]
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_artifact = serializer.save()

        self.assertEqual(len(updated_artifact.enriched_achievements), 3)

    def test_update_all_fields_at_once(self):
        """Test updating all enriched fields simultaneously"""
        data = {
            'unified_description': 'Comprehensive update',
            'enriched_technologies': ['Python', 'Django', 'Vue.js'],
            'enriched_achievements': ['New achievement']
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data)

        self.assertTrue(serializer.is_valid())
        updated_artifact = serializer.save()

        self.assertEqual(updated_artifact.unified_description, 'Comprehensive update')
        self.assertEqual(len(updated_artifact.enriched_technologies), 3)
        self.assertEqual(len(updated_artifact.enriched_achievements), 1)

    def test_validate_description_max_length(self):
        """Test unified description validates max length"""
        data = {
            'unified_description': 'x' * 5001  # Over 5000 character limit
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn('unified_description', serializer.errors)

    def test_validate_technologies_is_list(self):
        """Test enriched technologies must be a list"""
        data = {
            'enriched_technologies': 'not-a-list'
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn('enriched_technologies', serializer.errors)

    def test_validate_technologies_max_count(self):
        """Test enriched technologies enforces max count"""
        data = {
            'enriched_technologies': [f'Tech{i}' for i in range(51)]  # Over 50 limit
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn('enriched_technologies', serializer.errors)

    def test_validate_technologies_all_strings(self):
        """Test enriched technologies must all be strings"""
        data = {
            'enriched_technologies': ['Python', 123, 'Django']  # Contains non-string
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn('enriched_technologies', serializer.errors)

    def test_validate_achievements_is_list(self):
        """Test enriched achievements must be a list"""
        data = {
            'enriched_achievements': 'not-a-list'
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn('enriched_achievements', serializer.errors)

    def test_validate_achievements_max_count(self):
        """Test enriched achievements enforces max count"""
        data = {
            'enriched_achievements': [f'Achievement {i}' for i in range(21)]  # Over 20 limit
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn('enriched_achievements', serializer.errors)

    def test_validate_achievements_all_strings(self):
        """Test enriched achievements must all be strings"""
        data = {
            'enriched_achievements': ['Achievement 1', {'not': 'string'}, 'Achievement 2']
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertFalse(serializer.is_valid())
        self.assertIn('enriched_achievements', serializer.errors)

    def test_partial_update_preserves_other_fields(self):
        """Test partial update doesn't affect unspecified fields"""
        original_technologies = self.artifact.enriched_technologies.copy()
        original_achievements = self.artifact.enriched_achievements.copy()

        data = {
            'unified_description': 'Updated description only'
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_artifact = serializer.save()

        # Other fields should remain unchanged
        self.assertEqual(updated_artifact.enriched_technologies, original_technologies)
        self.assertEqual(updated_artifact.enriched_achievements, original_achievements)

    def test_empty_lists_allowed(self):
        """Test empty lists are valid for technologies and achievements"""
        data = {
            'enriched_technologies': [],
            'enriched_achievements': []
        }
        serializer = EnrichedContentUpdateSerializer(self.artifact, data=data, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_artifact = serializer.save()

        self.assertEqual(updated_artifact.enriched_technologies, [])
        self.assertEqual(updated_artifact.enriched_achievements, [])


@tag('medium', 'integration', 'artifacts', 'serializers')
class ArtifactSerializerUserContextTests(TestCase):
    """Test user_context field in serializers (ft-018)"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )

    def test_artifact_serializer_includes_user_context(self):
        """Test ArtifactSerializer includes user_context field"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description',
            user_context='Led a team of 6 engineers. Reduced costs by 40%.'
        )

        from artifacts.serializers import ArtifactSerializer
        serializer = ArtifactSerializer(artifact)

        # Verify user_context is in serialized data
        self.assertIn('user_context', serializer.data)
        self.assertEqual(serializer.data['user_context'], 'Led a team of 6 engineers. Reduced costs by 40%.')

    def test_artifact_serializer_user_context_optional(self):
        """Test ArtifactSerializer handles missing user_context"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description'
            # user_context not provided
        )

        from artifacts.serializers import ArtifactSerializer
        serializer = ArtifactSerializer(artifact)

        # Should be empty string
        self.assertIn('user_context', serializer.data)
        self.assertEqual(serializer.data['user_context'], '')

    def test_artifact_create_serializer_accepts_user_context(self):
        """Test ArtifactCreateSerializer accepts user_context"""
        from artifacts.serializers import ArtifactCreateSerializer
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.post('/artifacts/')
        request.user = self.user

        data = {
            'title': 'Test Project',
            'description': 'Test description',
            'user_context': 'Led a team of 6 engineers',
            'artifact_type': 'project'
        }

        serializer = ArtifactCreateSerializer(data=data, context={'request': request})

        self.assertTrue(serializer.is_valid(), serializer.errors)
        artifact = serializer.save()
        self.assertEqual(artifact.user_context, 'Led a team of 6 engineers')

    def test_artifact_update_serializer_accepts_user_context(self):
        """Test ArtifactUpdateSerializer allows editing user_context"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description',
            user_context='Original context'
        )

        from artifacts.serializers import ArtifactUpdateSerializer

        data = {
            'user_context': 'Updated context: Led a team of 8 engineers'
        }

        serializer = ArtifactUpdateSerializer(artifact, data=data, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_artifact = serializer.save()

        self.assertEqual(updated_artifact.user_context, 'Updated context: Led a team of 8 engineers')

    def test_enriched_content_update_excludes_user_context(self):
        """Test EnrichedContentUpdateSerializer does NOT include user_context"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description',
            user_context='User context should not be editable here',
            unified_description='Original unified description'
        )

        # Should not be able to update user_context via EnrichedContentUpdateSerializer
        data = {
            'user_context': 'Attempting to change context',
            'unified_description': 'New unified description'
        }

        serializer = EnrichedContentUpdateSerializer(artifact, data=data, partial=True)

        self.assertTrue(serializer.is_valid())
        updated_artifact = serializer.save()

        # user_context should remain unchanged
        self.assertEqual(updated_artifact.user_context, 'User context should not be editable here')
        # unified_description should be updated
        self.assertEqual(updated_artifact.unified_description, 'New unified description')
