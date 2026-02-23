from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from artifacts.models import Artifact, Evidence, UploadedFile
from artifacts.serializers import (
    ArtifactUpdateSerializer, EvidenceCreateSerializer,
    EvidenceUpdateSerializer
)

User = get_user_model()


@tag('medium', 'integration', 'artifacts', 'api')
class ArtifactEditingAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpassword'
        )
        self.other_user = User.objects.create_user(
            username='other@example.com',
            email='other@example.com',
            password='testpassword'
        )

        # Create JWT token
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        # Create test artifacts
        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description',
            artifact_type='project',
            technologies=['Python', 'Django'],
            collaborators=['john@example.com']
        )

        self.other_artifact = Artifact.objects.create(
            user=self.other_user,
            title='Other User Project',
            description='Other description',
            artifact_type='project'
        )

    def test_partial_update_artifact(self):
        """Test partial artifact update with PATCH"""
        url = reverse('artifact_detail', kwargs={'artifact_id': self.artifact.pk})
        data = {
            'title': 'Updated Project Title',
            'description': 'Updated description'
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.artifact.refresh_from_db()
        self.assertEqual(self.artifact.title, 'Updated Project Title')
        self.assertEqual(self.artifact.description, 'Updated description')
        # Unchanged fields should remain the same
        self.assertEqual(self.artifact.artifact_type, 'project')

    def test_full_update_artifact(self):
        """Test full artifact update with PUT"""
        url = reverse('artifact_detail', kwargs={'artifact_id': self.artifact.pk})
        data = {
            'title': 'Completely New Title',
            'description': 'Completely new description',
            'artifact_type': 'publication',
            'start_date': '2023-01-01',
            'end_date': '2023-12-31',
            'technologies': ['Python', 'React'],
            'collaborators': ['jane@example.com']
        }

        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.artifact.refresh_from_db()
        self.assertEqual(self.artifact.title, 'Completely New Title')
        self.assertEqual(self.artifact.artifact_type, 'publication')
        self.assertEqual(self.artifact.technologies, ['Python', 'React'])

    def test_cannot_update_other_user_artifact(self):
        """Test that users cannot update other users' artifacts"""
        url = reverse('artifact_detail', kwargs={'artifact_id': self.other_artifact.pk})
        data = {'title': 'Hacked Title'}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.other_artifact.refresh_from_db()
        self.assertNotEqual(self.other_artifact.title, 'Hacked Title')

    def test_update_artifact_validation_errors(self):
        """Test validation errors during artifact update"""
        url = reverse('artifact_detail', kwargs={'artifact_id': self.artifact.pk})
        data = {
            'title': '',  # Required field
            'start_date': '2023-12-31',
            'end_date': '2023-01-01'  # End before start
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('title', response.data)

    def test_add_evidence_link(self):
        """Test adding evidence link to artifact"""
        url = reverse('add_evidence_link', kwargs={'artifact_id': self.artifact.pk})
        data = {
            'url': 'https://github.com/user/project',
            'evidence_type': 'github',
            'description': 'Project repository'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Evidence.objects.count(), 1)
        evidence_link = Evidence.objects.first()
        self.assertEqual(evidence_link.artifact, self.artifact)
        self.assertEqual(evidence_link.url, 'https://github.com/user/project')
        self.assertEqual(evidence_link.evidence_type, 'github')

    def test_add_evidence_link_invalid_url(self):
        """Test adding evidence link with invalid URL"""
        url = reverse('add_evidence_link', kwargs={'artifact_id': self.artifact.pk})
        data = {
            'url': 'invalid-url',
            'evidence_type': 'github',
            'description': 'Invalid URL'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data)
        self.assertEqual(Evidence.objects.count(), 0)

    def test_update_evidence_link(self):
        """Test updating existing evidence link"""
        evidence_link = Evidence.objects.create(
            artifact=self.artifact,
            url='https://old-url.com',
            evidence_type='website',
            description='Old description'
        )

        url = reverse('evidence_link_detail', kwargs={'link_id': evidence_link.pk})
        data = {
            'url': 'https://new-url.com',
            'evidence_type': 'github',
            'description': 'New description'
        }

        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        evidence_link.refresh_from_db()
        self.assertEqual(evidence_link.url, 'https://new-url.com')
        self.assertEqual(evidence_link.evidence_type, 'github')
        self.assertEqual(evidence_link.description, 'New description')

    def test_delete_evidence_link(self):
        """Test deleting evidence link"""
        evidence_link = Evidence.objects.create(
            artifact=self.artifact,
            url='https://example.com',
            evidence_type='website',
            description='Test link'
        )

        url = reverse('evidence_link_detail', kwargs={'link_id': evidence_link.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Evidence.objects.count(), 0)

    def test_cannot_update_other_user_evidence_link(self):
        """Test that users cannot update other users' evidence links"""
        evidence_link = Evidence.objects.create(
            artifact=self.other_artifact,
            url='https://example.com',
            evidence_type='website',
            description='Other user link'
        )

        url = reverse('evidence_link_detail', kwargs={'link_id': evidence_link.pk})
        data = {'url': 'https://hacked.com'}

        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        evidence_link.refresh_from_db()
        self.assertNotEqual(evidence_link.url, 'https://hacked.com')


@tag('medium', 'integration', 'artifacts', 'serializers')
class ArtifactEditingSerializerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpassword'
        )

        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description',
            artifact_type='project'
        )

    def test_artifact_update_serializer_validation(self):
        """Test ArtifactUpdateSerializer validation"""
        # Valid data
        data = {
            'title': 'Updated Title',
            'description': 'Updated description',
            'start_date': '2023-01-01',
            'end_date': '2023-12-31'
        }
        serializer = ArtifactUpdateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # Invalid date range - but this validation doesn't require title/description
        data = {
            'title': 'Test',
            'description': 'Test desc',
            'start_date': '2023-12-31',
            'end_date': '2023-01-01'
        }
        serializer = ArtifactUpdateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)

    def test_evidence_link_create_serializer(self):
        """Test EvidenceCreateSerializer"""
        # Valid data
        data = {
            'url': 'https://github.com/user/project',
            'evidence_type': 'github',
            'description': 'Project repository'
        }
        serializer = EvidenceCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        # Invalid URL
        data = {
            'url': 'invalid-url',
            'evidence_type': 'github',
            'description': 'Invalid URL'
        }
        serializer = EvidenceCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('url', serializer.errors)


@tag('medium', 'integration', 'artifacts', 'models')
class ArtifactEditingModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpassword'
        )

    def test_artifact_update_preserves_metadata(self):
        """Test that artifact updates preserve extracted metadata"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Original Title',
            description='Original description',
            extracted_metadata={'key': 'value', 'processed': True}
        )

        # Update artifact
        artifact.title = 'Updated Title'
        artifact.save()

        artifact.refresh_from_db()
        self.assertEqual(artifact.title, 'Updated Title')
        self.assertEqual(artifact.extracted_metadata, {'key': 'value', 'processed': True})

    def test_evidence_link_cascade_delete(self):
        """Test that evidence links are deleted when artifact is deleted"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description'
        )

        evidence_link = Evidence.objects.create(
            artifact=artifact,
            url='https://example.com',
            evidence_type='website',
            description='Test link'
        )

        self.assertEqual(Evidence.objects.count(), 1)

        artifact.delete()

        self.assertEqual(Evidence.objects.count(), 0)

    def test_evidence_link_validation_metadata_updates(self):
        """Test evidence link validation metadata handling"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description'
        )

        evidence_link = Evidence.objects.create(
            artifact=artifact,
            url='https://example.com',
            evidence_type='website',
            description='Test link',
            validation_metadata={'status': 'pending'}
        )

        # Update validation metadata
        evidence_link.validation_metadata = {'status': 'validated', 'response_code': 200}
        evidence_link.is_accessible = True
        evidence_link.save()

        evidence_link.refresh_from_db()
        self.assertEqual(evidence_link.validation_metadata['status'], 'validated')
        self.assertTrue(evidence_link.is_accessible)


@tag('medium', 'integration', 'artifacts', 'api')
class EvidenceFieldCompatibilityTestCase(APITestCase):
    """Test that evidence link endpoints accept both evidence_type and link_type fields"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpassword'
        )

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description',
            artifact_type='project'
        )

    def test_add_evidence_link_with_link_type_field(self):
        """Test adding evidence link using link_type field (frontend format)"""
        url = reverse('add_evidence_link', kwargs={'artifact_id': self.artifact.pk})
        data = {
            'url': 'https://github.com/user/project',
            'link_type': 'github',  # Frontend sends link_type
            'description': 'Project repository'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Evidence.objects.count(), 1)
        evidence_link = Evidence.objects.first()
        self.assertEqual(evidence_link.evidence_type, 'github')

    def test_add_evidence_link_with_evidence_type_field(self):
        """Test adding evidence link using evidence_type field (backend format)"""
        url = reverse('add_evidence_link', kwargs={'artifact_id': self.artifact.pk})
        data = {
            'url': 'https://github.com/user/project',
            'evidence_type': 'github',  # Backend format
            'description': 'Project repository'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Evidence.objects.count(), 1)
        evidence_link = Evidence.objects.first()
        self.assertEqual(evidence_link.evidence_type, 'github')

    def test_update_evidence_link_with_link_type_field(self):
        """Test updating evidence link using link_type field"""
        evidence_link = Evidence.objects.create(
            artifact=self.artifact,
            url='https://old-url.com',
            evidence_type='website',
            description='Old description'
        )

        url = reverse('evidence_link_detail', kwargs={'link_id': evidence_link.pk})
        data = {
            'url': 'https://new-url.com',
            'link_type': 'github',  # Frontend sends link_type
            'description': 'New description'
        }

        response = self.client.put(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        evidence_link.refresh_from_db()
        self.assertEqual(evidence_link.evidence_type, 'github')

    def test_serializer_accepts_link_type(self):
        """Test EvidenceCreateSerializer accepts link_type field"""
        data = {
            'url': 'https://github.com/user/project',
            'link_type': 'github',
            'description': 'Project repository'
        }
        serializer = EvidenceCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid(), f"Serializer errors: {serializer.errors}")

        # Verify it saves with evidence_type
        evidence = serializer.save(artifact=self.artifact)
        self.assertEqual(evidence.evidence_type, 'github')


@tag('medium', 'integration', 'artifacts', 'api')
class ErrorMessageQualityTestCase(APITestCase):
    """Test that error messages are specific and helpful"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser@example.com',
            email='testuser@example.com',
            password='testpassword'
        )

        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_add_evidence_link_with_invalid_url_shows_specific_error(self):
        """Test that invalid URL shows specific error message"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description'
        )

        url = reverse('add_evidence_link', kwargs={'artifact_id': artifact.pk})
        data = {
            'url': 'not-a-url',
            'evidence_type': 'github',
            'description': 'Invalid'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('url', response.data)
        # Should contain specific message about URL validation
        self.assertTrue('url' in str(response.data).lower() or 'valid' in str(response.data).lower())