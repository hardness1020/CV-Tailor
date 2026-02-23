from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db import transaction
from .models import Artifact, Evidence, UploadedFile
from .serializers import (
    EvidenceCreateSerializer, EvidenceUpdateSerializer
)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def add_evidence_link(request, artifact_id):
    """
    Add a new evidence link to an artifact.
    """
    try:
        artifact = Artifact.objects.get(id=artifact_id, user=request.user)
    except Artifact.DoesNotExist:
        return Response({'error': 'Artifact not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = EvidenceCreateSerializer(data=request.data)
    if serializer.is_valid():
        evidence_link = serializer.save(artifact=artifact)
        return Response({
            'id': evidence_link.id,
            'url': evidence_link.url,
            'evidence_type': evidence_link.evidence_type,
            'description': evidence_link.description,
            'created_at': evidence_link.created_at
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([permissions.IsAuthenticated])
def evidence_link_detail(request, link_id):
    """
    Update or delete a specific evidence link.
    """
    try:
        evidence_link = Evidence.objects.select_related('artifact').get(
            id=link_id,
            artifact__user=request.user
        )
    except Evidence.DoesNotExist:
        return Response({'error': 'Evidence link not found'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'PUT':
        serializer = EvidenceUpdateSerializer(evidence_link, data=request.data)
        if serializer.is_valid():
            evidence_link = serializer.save()
            return Response({
                'id': evidence_link.id,
                'url': evidence_link.url,
                'evidence_type': evidence_link.evidence_type,
                'description': evidence_link.description,
                'updated_at': evidence_link.updated_at
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        evidence_link.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_artifact_file(request, file_id):
    """
    Delete a file associated with an artifact.
    """
    try:
        # Find and delete the uploaded file
        uploaded_file = UploadedFile.objects.get(id=file_id, user=request.user)

        # Find associated evidence link
        evidence_link = Evidence.objects.filter(
            file_path__contains=str(file_id),
            artifact__user=request.user
        ).first()

        # Delete the physical file
        if uploaded_file.file:
            uploaded_file.file.delete(save=False)

        # Delete the database record
        uploaded_file.delete()

        # Delete the associated evidence link if it exists
        if evidence_link:
            evidence_link.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    except UploadedFile.DoesNotExist:
        return Response({'error': 'File not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        return Response({
            'error': 'Failed to delete file',
            'detail': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
