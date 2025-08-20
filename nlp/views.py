"""
Views for NLP processing and SOAP draft management.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from encounters.models import Encounter
from .models import SOAPDraft, ChecklistItem
from .services.extraction_service import ExtractionService
from .serializers import SOAPDraftSerializer, ChecklistItemSerializer
from .tasks import extract_soap_from_encounter
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_soap_extraction(request, encounter_id):
    """
    Start SOAP extraction for an encounter.
    """
    try:
        # Get encounter and verify ownership
        encounter = get_object_or_404(
            Encounter,
            id=encounter_id,
            doctor=request.user
        )
        
        # Check if encounter has processed transcript
        processed_chunks = encounter.audio_chunks.filter(status='processed')
        if not processed_chunks.exists():
            return Response(
                {'error': 'No processed audio chunks found. Complete STT processing first.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if SOAP draft already exists
        soap_draft, created = SOAPDraft.objects.get_or_create(
            encounter=encounter,
            defaults={'status': 'extracting'}
        )
        
        if not created and soap_draft.status == 'extracting':
            return Response(
                {'message': 'SOAP extraction already in progress'},
                status=status.HTTP_200_OK
            )
        
        # Reset status if re-extracting
        if not created:
            soap_draft.status = 'extracting'
            soap_draft.save()
        
        # Start extraction task
        task = extract_soap_from_encounter.delay(encounter.id)
        
        logger.info(f"Started SOAP extraction for Encounter {encounter.id}, task: {task.id}")
        
        return Response({
            'message': 'SOAP extraction started',
            'task_id': task.id,
            'encounter_id': encounter.id,
            'soap_draft_id': soap_draft.id,
            'status': 'extracting'
        })
        
    except Exception as e:
        logger.error(f"Failed to start SOAP extraction for encounter {encounter_id}: {e}")
        return Response(
            {'error': f'Failed to start extraction: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_soap_draft(request, encounter_id):
    """
    Get SOAP draft for an encounter.
    """
    try:
        # Get encounter and verify ownership
        encounter = get_object_or_404(
            Encounter,
            id=encounter_id,
            doctor=request.user
        )
        
        # Get SOAP draft
        try:
            soap_draft = SOAPDraft.objects.get(encounter=encounter)
            serializer = SOAPDraftSerializer(soap_draft)
            return Response(serializer.data)
        except SOAPDraft.DoesNotExist:
            return Response(
                {'error': 'SOAP draft not found. Start extraction first.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
    except Exception as e:
        logger.error(f"Failed to get SOAP draft for encounter {encounter_id}: {e}")
        return Response(
            {'error': f'Failed to get SOAP draft: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_soap_section(request, encounter_id):
    """
    Update a specific section of SOAP draft.
    """
    try:
        # Get encounter and verify ownership
        encounter = get_object_or_404(
            Encounter,
            id=encounter_id,
            doctor=request.user
        )
        
        # Get SOAP draft
        soap_draft = get_object_or_404(SOAPDraft, encounter=encounter)
        
        section = request.data.get('section')
        field = request.data.get('field')
        value = request.data.get('value')
        
        if not all([section, field]):
            return Response(
                {'error': 'section and field are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Validate section
        valid_sections = ['subjective', 'objective', 'assessment', 'plan']
        if section not in valid_sections:
            return Response(
                {'error': f'Invalid section. Must be one of: {valid_sections}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update SOAP data
        if section not in soap_draft.soap_data:
            soap_draft.soap_data[section] = {}
        
        soap_draft.soap_data[section][field] = value
        soap_draft.updated_at = timezone.now()
        
        # Update status if still extracting
        if soap_draft.status == 'extracting':
            soap_draft.status = 'draft'
        
        soap_draft.save()
        
        # Update related checklist items
        _update_checklist_after_edit(soap_draft, section, field)
        
        logger.info(f"Updated SOAP section {section}.{field} for encounter {encounter_id}")
        
        return Response({
            'message': 'SOAP section updated',
            'section': section,
            'field': field,
            'completion_percentage': soap_draft.completion_percentage
        })
        
    except Exception as e:
        logger.error(f"Failed to update SOAP section for encounter {encounter_id}: {e}")
        return Response(
            {'error': f'Failed to update SOAP section: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_checklist(request, encounter_id):
    """
    Get dynamic checklist for an encounter.
    """
    try:
        # Get encounter and verify ownership
        encounter = get_object_or_404(
            Encounter,
            id=encounter_id,
            doctor=request.user
        )
        
        # Get SOAP draft
        try:
            soap_draft = SOAPDraft.objects.get(encounter=encounter)
        except SOAPDraft.DoesNotExist:
            return Response(
                {'error': 'SOAP draft not found. Start extraction first.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get checklist items
        checklist_items = ChecklistItem.objects.filter(
            soap_draft=soap_draft
        ).order_by('section', '-weight', 'title')
        
        serializer = ChecklistItemSerializer(checklist_items, many=True)
        
        # Calculate summary statistics
        total_items = checklist_items.count()
        complete_items = checklist_items.filter(status='complete').count()
        missing_items = checklist_items.filter(status='missing').count()
        critical_missing = checklist_items.filter(
            status='missing',
            item_type='required',
            weight__gte=8
        ).count()
        
        return Response({
            'checklist_items': serializer.data,
            'summary': {
                'total_items': total_items,
                'complete_items': complete_items,
                'missing_items': missing_items,
                'critical_missing': critical_missing,
                'completion_percentage': soap_draft.completion_percentage
            }
        })
        
    except Exception as e:
        logger.error(f"Failed to get checklist for encounter {encounter_id}: {e}")
        return Response(
            {'error': f'Failed to get checklist: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_checklist_item(request, item_id):
    """
    Update checklist item status manually.
    """
    try:
        # Get checklist item and verify ownership
        checklist_item = get_object_or_404(
            ChecklistItem,
            id=item_id,
            soap_draft__encounter__doctor=request.user
        )
        
        new_status = request.data.get('status')
        notes = request.data.get('notes', '')
        
        valid_statuses = ['missing', 'partial', 'complete', 'not_applicable']
        if new_status not in valid_statuses:
            return Response(
                {'error': f'Invalid status. Must be one of: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update item
        checklist_item.status = new_status
        checklist_item.notes = notes
        checklist_item.updated_at = timezone.now()
        checklist_item.save()
        
        logger.info(f"Updated checklist item {item_id} status to {new_status}")
        
        return Response({
            'message': 'Checklist item updated',
            'item': ChecklistItemSerializer(checklist_item).data
        })
        
    except Exception as e:
        logger.error(f"Failed to update checklist item {item_id}: {e}")
        return Response(
            {'error': f'Failed to update checklist item: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def _update_checklist_after_edit(soap_draft, section, field):
    """Update checklist items after SOAP section edit."""
    try:
        # Re-assess checklist items for the updated section
        extraction_service = ExtractionService()
        updated_items = extraction_service.generate_checklist_items(soap_draft.soap_data)
        
        # Update existing checklist items
        for item_data in updated_items:
            if item_data['section'] == section:
                ChecklistItem.objects.update_or_create(
                    soap_draft=soap_draft,
                    item_id=item_data['item_id'],
                    defaults={
                        'status': item_data['status'],
                        'confidence': item_data['confidence'],
                        'notes': item_data['notes'],
                    }
                )
    except Exception as e:
        logger.warning(f"Failed to update checklist after edit: {e}")
