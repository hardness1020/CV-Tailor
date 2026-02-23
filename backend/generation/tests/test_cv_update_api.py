"""
Unit tests for CV metadata update API endpoint (PATCH /api/v1/generate/{id}/)

Testing the ability to update CV metadata like template selection,
custom sections, and generation preferences after generation.
"""

import uuid
from django.test import TestCase, tag
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from generation.models import GeneratedDocument, CVTemplate
from artifacts.models import Artifact

User = get_user_model()


@tag('medium', 'integration', 'generation', 'api')
class CVMetadataUpdateAPITests(APITestCase):
    """Test cases for CV metadata update endpoint (PATCH /api/v1/generate/{id}/)"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass123'
        )
        self.token = RefreshToken.for_user(self.user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')

        # Create test CV
        self.generation = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='abc123',
            status='completed',
            template_id=1,
            custom_sections={
                'include_publications': True,
                'include_certifications': False
            },
            generation_preferences={
                'tone': 'professional',
                'length': 'detailed'
            },
            content={
                'professional_summary': 'Experienced developer',
                'key_skills': ['Python', 'Django']
            }
        )

        # Create test templates
        self.template1 = CVTemplate.objects.create(
            name='Modern',
            category='modern',
            description='Modern template',
            prompt_template='Test template 1',
            is_active=True
        )
        self.template2 = CVTemplate.objects.create(
            name='Classic',
            category='classic',
            description='Classic template',
            prompt_template='Test template 2',
            is_active=True
        )

    def test_update_cv_template_id_success(self):
        """Test successfully updating CV template ID"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})
        data = {'template_id': self.template2.id}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.generation.refresh_from_db()
        self.assertEqual(self.generation.template_id, self.template2.id)

    def test_update_cv_custom_sections_success(self):
        """Test successfully updating CV custom sections"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})
        data = {
            'custom_sections': {
                'include_publications': False,
                'include_certifications': True,
                'include_volunteer': True
            }
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.generation.refresh_from_db()
        self.assertEqual(self.generation.custom_sections['include_publications'], False)
        self.assertEqual(self.generation.custom_sections['include_certifications'], True)
        self.assertEqual(self.generation.custom_sections['include_volunteer'], True)

    def test_update_cv_generation_preferences_success(self):
        """Test successfully updating CV generation preferences"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})
        data = {
            'generation_preferences': {
                'tone': 'technical',
                'length': 'concise'
            }
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.generation.refresh_from_db()
        self.assertEqual(self.generation.generation_preferences['tone'], 'technical')
        self.assertEqual(self.generation.generation_preferences['length'], 'concise')

    def test_update_cv_partial_update_success(self):
        """Test partial update (only updating one field)"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})

        # Only update template_id, leave other fields unchanged
        data = {'template_id': self.template2.id}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.generation.refresh_from_db()
        # Template should be updated
        self.assertEqual(self.generation.template_id, self.template2.id)
        # Other fields should remain unchanged
        self.assertEqual(self.generation.custom_sections['include_publications'], True)
        self.assertEqual(self.generation.generation_preferences['tone'], 'professional')

    def test_update_cv_multiple_fields_success(self):
        """Test updating multiple fields at once"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})
        data = {
            'template_id': self.template2.id,
            'custom_sections': {
                'include_certifications': True
            },
            'generation_preferences': {
                'tone': 'creative',
                'length': 'concise'
            }
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.generation.refresh_from_db()
        self.assertEqual(self.generation.template_id, self.template2.id)
        self.assertEqual(self.generation.custom_sections['include_certifications'], True)
        self.assertEqual(self.generation.generation_preferences['tone'], 'creative')
        self.assertEqual(self.generation.generation_preferences['length'], 'concise')

    def test_update_cv_invalid_template_id(self):
        """Test updating with invalid template ID fails"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})
        data = {'template_id': 99999}  # Non-existent template

        response = self.client.patch(url, data, format='json')

        # Should return 400 Bad Request with validation error
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('template_id', str(response.data).lower())

    def test_update_cv_invalid_custom_sections(self):
        """Test updating with invalid custom sections fails"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})
        data = {
            'custom_sections': {
                'invalid_section': True  # Not in allowed sections
            }
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_cv_invalid_generation_preferences(self):
        """Test updating with invalid generation preferences fails"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})
        data = {
            'generation_preferences': {
                'tone': 'invalid_tone'  # Not in allowed tones
            }
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_cv_unauthorized(self):
        """Test unauthenticated user cannot update CV"""
        self.client.credentials()  # Remove authentication

        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})
        data = {'template_id': self.template2.id}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_update_cv_user_isolation(self):
        """Test user cannot update another user's CV"""
        # Create another user and their CV
        user2 = User.objects.create_user(
            email='user2@example.com',
            username='user2',
            password='password123'
        )
        generation2 = GeneratedDocument.objects.create(
            user=user2,
            document_type='cv',
            job_description_hash='def456',
            status='completed',
            template_id=1
        )

        # Try to update user2's CV while authenticated as user1
        url = reverse('generation_status', kwargs={'generation_id': generation2.id})
        data = {'template_id': self.template2.id}

        response = self.client.patch(url, data, format='json')

        # Should return 404 Not Found (user isolation)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        # Verify CV was not updated
        generation2.refresh_from_db()
        self.assertEqual(generation2.template_id, 1)

    def test_update_cv_nonexistent_generation(self):
        """Test updating non-existent CV returns 404"""
        fake_id = str(uuid.uuid4())
        url = reverse('generation_status', kwargs={'generation_id': fake_id})
        data = {'template_id': self.template2.id}

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_cv_processing_status(self):
        """Test updating CV in processing status is allowed"""
        # Create CV in processing status
        processing_gen = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='xyz789',
            status='processing',
            template_id=1
        )

        url = reverse('generation_status', kwargs={'generation_id': processing_gen.id})
        data = {'template_id': self.template2.id}

        response = self.client.patch(url, data, format='json')

        # Should allow update even in processing status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        processing_gen.refresh_from_db()
        self.assertEqual(processing_gen.template_id, self.template2.id)

    def test_update_cv_failed_status(self):
        """Test updating CV in failed status is allowed"""
        # Create CV in failed status
        failed_gen = GeneratedDocument.objects.create(
            user=self.user,
            document_type='cv',
            job_description_hash='failed123',
            status='failed',
            template_id=1,
            error_message='Generation failed'
        )

        url = reverse('generation_status', kwargs={'generation_id': failed_gen.id})
        data = {'template_id': self.template2.id}

        response = self.client.patch(url, data, format='json')

        # Should allow update even in failed status
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        failed_gen.refresh_from_db()
        self.assertEqual(failed_gen.template_id, self.template2.id)

    def test_update_cv_read_only_fields_ignored(self):
        """Test that read-only fields are ignored during update"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})

        # Try to update read-only fields
        data = {
            'template_id': self.template2.id,
            'id': str(uuid.uuid4()),  # Try to change ID (read-only)
            'user': 999,  # Try to change user (read-only)
            'job_description_hash': 'hacked',  # Read-only
            'status': 'failed',  # Read-only
            'created_at': '2020-01-01T00:00:00Z',  # Read-only
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.generation.refresh_from_db()
        # Template should be updated (writable field)
        self.assertEqual(self.generation.template_id, self.template2.id)
        # Read-only fields should remain unchanged
        self.assertNotEqual(str(self.generation.id), data['id'])
        self.assertEqual(self.generation.user, self.user)
        self.assertEqual(self.generation.job_description_hash, 'abc123')
        self.assertEqual(self.generation.status, 'completed')

    def test_update_cv_returns_updated_data(self):
        """Test that PATCH returns the updated CV data"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})
        data = {
            'template_id': self.template2.id,
            'generation_preferences': {
                'tone': 'technical',
                'length': 'concise'
            }
        }

        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify response contains updated data
        self.assertEqual(response.data['template_id'], self.template2.id)
        self.assertEqual(response.data['generation_preferences']['tone'], 'technical')
        self.assertEqual(response.data['generation_preferences']['length'], 'concise')
        # Verify other fields are still present
        self.assertIn('id', response.data)
        self.assertIn('status', response.data)
        self.assertIn('content', response.data)

    def test_update_cv_empty_data(self):
        """Test PATCH with empty data returns 200 OK (no changes)"""
        url = reverse('generation_status', kwargs={'generation_id': self.generation.id})
        data = {}

        response = self.client.patch(url, data, format='json')

        # Should return 200 OK with no changes
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify no fields were changed
        self.generation.refresh_from_db()
        self.assertEqual(self.generation.template_id, 1)
        self.assertEqual(self.generation.generation_preferences['tone'], 'professional')
