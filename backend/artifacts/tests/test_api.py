"""
Unit tests for artifacts app API endpoints
"""

from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from artifacts.models import Artifact, ArtifactProcessingJob

User = get_user_model()


@tag('medium', 'integration', 'artifacts', 'api')
class ArtifactAPITests(APITestCase):
    """Test cases for Artifact API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_create_artifact(self):
        """Test artifact creation via API"""
        # Get initial count
        initial_count = Artifact.objects.count()

        url = reverse('artifact_list_create')
        data = {
            'title': 'API Test Project',
            'description': 'Created via API',
            'artifact_type': 'project',
            'start_date': '2024-01-01',
            'end_date': '2024-06-01',
            'technologies': ['Python', 'Django', 'React'],
            'collaborators': ['Alice', 'Bob']
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # Check that count increased by 1
        self.assertEqual(Artifact.objects.count(), initial_count + 1)

        # Get the newly created artifact by checking the response data
        artifact_id = response.data['id']
        artifact = Artifact.objects.get(id=artifact_id)
        self.assertEqual(artifact.title, 'API Test Project')
        self.assertEqual(artifact.user, self.user)
        self.assertEqual(len(artifact.technologies), 3)

    def test_list_artifacts(self):
        """Test listing user's artifacts"""
        # Create test artifacts
        Artifact.objects.create(
            user=self.user,
            title='Project 1',
            description='First project'
        )
        Artifact.objects.create(
            user=self.user,
            title='Project 2',
            description='Second project'
        )

        url = reverse('artifact_list_create')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_retrieve_artifact(self):
        """Test retrieving specific artifact"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description'
        )

        url = reverse('artifact_detail', kwargs={'artifact_id': artifact.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'Test Project')

    def test_update_artifact(self):
        """Test updating artifact"""
        artifact = Artifact.objects.create(
            user=self.user,
            title='Original Title',
            description='Original description'
        )

        url = reverse('artifact_detail', kwargs={'artifact_id': artifact.pk})
        data = {
            'title': 'Updated Title',
            'description': 'Updated description',
            'technologies': ['Updated Tech']
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        artifact.refresh_from_db()
        self.assertEqual(artifact.title, 'Updated Title')

    def test_delete_artifact(self):
        """Test deleting artifact"""
        # Get initial count
        initial_count = Artifact.objects.count()

        artifact = Artifact.objects.create(
            user=self.user,
            title='To Delete',
            description='Will be deleted'
        )

        url = reverse('artifact_detail', kwargs={'artifact_id': artifact.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        # Check that count decreased by 1 (back to initial count)
        self.assertEqual(Artifact.objects.count(), initial_count)
        # Also check that the specific artifact no longer exists
        self.assertFalse(Artifact.objects.filter(id=artifact.id).exists())

    def test_unauthorized_access(self):
        """Test that unauthenticated users can't access artifacts"""
        self.client.credentials()  # Remove auth

        url = reverse('artifact_list_create')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_isolation(self):
        """Test that users can only see their own artifacts"""
        # Create another user with artifact
        other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='otherpass123'
        )
        Artifact.objects.create(
            user=other_user,
            title='Other User Project',
            description='Should not be visible'
        )

        # Create artifact for current user
        Artifact.objects.create(
            user=self.user,
            title='My Project',
            description='Should be visible'
        )

        url = reverse('artifact_list_create')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'My Project')

    def test_create_artifact_with_valid_github_evidence_type(self):
        """Test artifact creation with valid 'github' evidence type"""
        url = reverse('artifact_list_create')
        data = {
            'title': 'GitHub Project',
            'description': 'Project with GitHub evidence',
            'artifact_type': 'project',
            'start_date': '2024-01-01',
            'technologies': ['Python'],
            'evidence_links': [
                {
                    'url': 'https://github.com/user/repo',
                    'evidence_type': 'github',
                    'description': 'Source code'
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_artifact_with_valid_document_evidence_type(self):
        """Test artifact creation with valid 'document' evidence type"""
        url = reverse('artifact_list_create')
        data = {
            'title': 'Document Project',
            'description': 'Project with document evidence',
            'artifact_type': 'project',
            'start_date': '2024-01-01',
            'technologies': ['Python'],
            'evidence_links': [
                {
                    'url': 'http://example.com/doc.pdf',
                    'evidence_type': 'document',
                    'description': 'Documentation',
                    'file_path': 'uploads/test_doc.pdf'  # Required for document type
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_artifact_with_live_app_evidence_type_rejected(self):
        """Test artifact creation with deprecated 'live_app' evidence type is rejected"""
        url = reverse('artifact_list_create')
        data = {
            'title': 'Live App Project',
            'description': 'Project with live app evidence',
            'artifact_type': 'project',
            'start_date': '2024-01-01',
            'technologies': ['Python'],
            'evidence_links': [
                {
                    'url': 'https://example.com/app',
                    'evidence_type': 'live_app',
                    'description': 'Live application'
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidence', str(response.data).lower())

    def test_create_artifact_with_video_evidence_type_rejected(self):
        """Test artifact creation with deprecated 'video' evidence type is rejected"""
        url = reverse('artifact_list_create')
        data = {
            'title': 'Video Project',
            'description': 'Project with video evidence',
            'artifact_type': 'project',
            'start_date': '2024-01-01',
            'technologies': ['Python'],
            'evidence_links': [
                {
                    'url': 'https://youtube.com/watch?v=123',
                    'evidence_type': 'video',
                    'description': 'Video demo'
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidence', str(response.data).lower())

    def test_create_artifact_with_website_evidence_type_rejected(self):
        """Test artifact creation with deprecated 'website' evidence type is rejected"""
        url = reverse('artifact_list_create')
        data = {
            'title': 'Website Project',
            'description': 'Project with website evidence',
            'artifact_type': 'project',
            'start_date': '2024-01-01',
            'technologies': ['Python'],
            'evidence_links': [
                {
                    'url': 'https://example.com',
                    'evidence_type': 'website',
                    'description': 'Website'
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidence', str(response.data).lower())

    def test_create_artifact_with_other_evidence_type_rejected(self):
        """Test artifact creation with deprecated 'other' evidence type is rejected"""
        url = reverse('artifact_list_create')
        data = {
            'title': 'Other Project',
            'description': 'Project with other evidence',
            'artifact_type': 'project',
            'start_date': '2024-01-01',
            'technologies': ['Python'],
            'evidence_links': [
                {
                    'url': 'https://example.com/other',
                    'evidence_type': 'other',
                    'description': 'Other type'
                }
            ]
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('evidence', str(response.data).lower())


@tag('medium', 'integration', 'artifacts', 'api')
class ArtifactProcessingStatusAPITests(APITestCase):
    """Test cases for processing status endpoint"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        self.artifact = Artifact.objects.create(
            user=self.user,
            title='Test Project',
            description='Test description'
        )

    def test_processing_status_success(self):
        """Test successful processing status retrieval"""
        # Create processing job
        job = ArtifactProcessingJob.objects.create(
            artifact=self.artifact,
            status='completed',
            progress_percentage=100
        )

        url = reverse('artifact_processing_status', kwargs={'artifact_id': self.artifact.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'completed')
        self.assertEqual(response.data['progress_percentage'], 100)

    def test_processing_status_not_found(self):
        """Test processing status for non-existent artifact"""
        url = reverse('artifact_processing_status', kwargs={'artifact_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


@tag('medium', 'integration', 'artifacts', 'api')
class ArtifactSuggestionsAPITests(APITestCase):
    """Test cases for artifact suggestions endpoint"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

    def test_get_all_suggestions(self):
        """Test getting all technology suggestions"""
        url = reverse('artifact_suggestions')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('suggestions', response.data)
        self.assertTrue(len(response.data['suggestions']) > 0)

    def test_filter_suggestions(self):
        """Test filtering technology suggestions"""
        url = reverse('artifact_suggestions')
        response = self.client.get(url, {'q': 'python'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        suggestions = response.data['suggestions']

        # All suggestions should contain 'python' (case insensitive)
        for suggestion in suggestions:
            self.assertIn('python', suggestion.lower())


@tag('medium', 'integration', 'artifacts', 'api')
class ArtifactSuggestForJobAPITests(APITestCase):
    """Test cases for suggest-for-job endpoint (ft-007)"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Create test artifacts
        self.artifact1 = Artifact.objects.create(
            user=self.user,
            title='E-commerce Platform',
            description='Built scalable marketplace',
            technologies=['React', 'Node.js', 'PostgreSQL'],
            start_date='2023-01-01',
            end_date='2023-12-31'
        )
        self.artifact2 = Artifact.objects.create(
            user=self.user,
            title='API Gateway',
            description='RESTful API with OAuth',
            technologies=['Python', 'FastAPI', 'Redis'],
            start_date='2022-06-01',
            end_date='2023-05-31'
        )
        self.artifact3 = Artifact.objects.create(
            user=self.user,
            title='Mobile App',
            description='Cross-platform mobile app',
            technologies=['React Native', 'TypeScript'],
            start_date='2024-01-01'
        )

    def test_suggest_artifacts_for_job_success(self):
        """Test successful artifact suggestions for job description"""
        url = reverse('artifact-suggest-for-job')
        data = {
            'job_description': 'Looking for a full-stack developer with React and Node.js experience',
            'limit': 10
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('artifacts', response.data)
        self.assertIn('total_artifacts', response.data)
        self.assertIn('returned_count', response.data)

        # Should return artifacts ranked by relevance
        artifacts = response.data['artifacts']
        self.assertGreater(len(artifacts), 0)

        # First artifact should have highest relevance score
        self.assertIn('relevance_score', artifacts[0])
        self.assertIn('matched_keywords', artifacts[0])
        self.assertIn('exact_matches', artifacts[0])

    def test_suggest_artifacts_returns_top_n(self):
        """Test that suggest endpoint respects limit parameter"""
        url = reverse('artifact-suggest-for-job')
        data = {
            'job_description': 'Looking for Python or React experience',
            'limit': 2
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['returned_count'], 2)
        self.assertLessEqual(len(response.data['artifacts']), 2)

    def test_suggest_artifacts_validates_job_description_required(self):
        """Test that job_description is required"""
        url = reverse('artifact-suggest-for-job')
        data = {}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('job_description', str(response.data).lower())

    def test_suggest_artifacts_validates_min_length(self):
        """Test job_description minimum length validation"""
        url = reverse('artifact-suggest-for-job')
        data = {
            'job_description': 'short'  # Less than 10 characters
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_suggest_artifacts_handles_no_artifacts(self):
        """Test suggest endpoint when user has no artifacts"""
        # Create new user with no artifacts
        new_user = User.objects.create_user(
            email='new@example.com',
            username='newuser',
            password='testpass123'
        )
        new_token = RefreshToken.for_user(new_user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_token}')

        url = reverse('artifact-suggest-for-job')
        data = {
            'job_description': 'Looking for React developer'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_artifacts'], 0)
        self.assertEqual(len(response.data['artifacts']), 0)

    def test_suggest_artifacts_requires_authentication(self):
        """Test that unauthenticated users cannot access suggest endpoint"""
        self.client.credentials()  # Remove auth

        url = reverse('artifact-suggest-for-job')
        data = {
            'job_description': 'Looking for React developer'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_suggest_artifacts_user_isolation(self):
        """Test that suggestions only include user's own artifacts"""
        # Create another user with artifacts
        other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='testpass123'
        )
        Artifact.objects.create(
            user=other_user,
            title='Other User Project',
            description='Should not appear',
            technologies=['React', 'Node.js']
        )

        url = reverse('artifact-suggest-for-job')
        data = {
            'job_description': 'Looking for React and Node.js developer'
        }

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should only return artifacts from self.user (3 artifacts)
        self.assertEqual(response.data['total_artifacts'], 3)

        # Verify no artifact from other user
        artifact_ids = [a['id'] for a in response.data['artifacts']]
        other_artifact = Artifact.objects.filter(user=other_user).first()
        self.assertNotIn(other_artifact.id, artifact_ids)