"""
Views for output generation and patient linking.
"""

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from nlp.models import SOAPDraft
from .models import FinalizedSOAP, OutputFile, PatientLink
from .serializers import FinalizedSOAPSerializer, OutputFileSerializer, PatientLinkSerializer
from .tasks import finalize_soap_note, create_patient_link_and_notify
from .services.pdf_service import PDFService
from .services.patient_linking_service import PatientLinkingService
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_finalization(request, encounter_id):
    """
    Start SOAP finalization process.
    """
    try:
        # Get SOAP draft
        soap_draft = get_object_or_404(
            SOAPDraft,
            encounter_id=encounter_id,
            encounter__doctor=request.user
        )
        
        # Check if SOAP draft is ready for finalization
        if soap_draft.status not in ['draft', 'reviewed']:
            return Response(
                {'error': f'SOAP draft must be in draft or reviewed status. Current: {soap_draft.status}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Start finalization task
        task = finalize_soap_note.delay(soap_draft.id)
        
        logger.info(f"Started SOAP finalization for encounter {encounter_id}, task: {task.id}")
        
        return Response({
            'message': 'SOAP finalization started',
            'task_id': task.id,
            'soap_draft_id': soap_draft.id,
            'status': 'finalizing'
        })
        
    except Exception as e:
        logger.error(f"Failed to start finalization for encounter {encounter_id}: {e}")
        return Response(
            {'error': f'Failed to start finalization: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_finalized_soap(request, encounter_id):
    """
    Get finalized SOAP for an encounter.
    """
    # Get finalized SOAP - get_object_or_404 handles 404 response automatically
    finalized_soap = get_object_or_404(
        FinalizedSOAP,
        soap_draft__encounter_id=encounter_id,
        soap_draft__encounter__doctor=request.user
    )
    
    serializer = FinalizedSOAPSerializer(finalized_soap)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_output_files(request, encounter_id):
    """
    List all output files for an encounter.
    """
    # Get finalized SOAP - get_object_or_404 handles 404 response automatically
    finalized_soap = get_object_or_404(
        FinalizedSOAP,
        soap_draft__encounter_id=encounter_id,
        soap_draft__encounter__doctor=request.user
    )
    
    # Get output files
    output_files = OutputFile.objects.filter(
        finalized_soap=finalized_soap
    ).order_by('file_type')
    
    serializer = OutputFileSerializer(output_files, many=True)
    
    return Response({
        'encounter_id': encounter_id,
        'finalized_soap_id': finalized_soap.id,
        'output_files': serializer.data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_download_url(request, file_id):
    """
    Generate presigned download URL for an output file.
    """
    try:
        # Get output file and verify ownership
        output_file = get_object_or_404(
            OutputFile,
            id=file_id,
            finalized_soap__soap_draft__encounter__doctor=request.user
        )
        
        # Generate presigned URL
        pdf_service = PDFService()
        presigned_url = pdf_service.generate_presigned_download_url(
            output_file.file_path,
            expires_in=3600  # 1 hour
        )
        
        # Update OutputFile with new presigned URL
        output_file.presigned_url = presigned_url
        output_file.presigned_expires_at = timezone.now() + timezone.timedelta(hours=1)
        output_file.save()
        
        return Response({
            'download_url': presigned_url,
            'expires_at': output_file.presigned_expires_at,
            'file_type': output_file.file_type,
            'file_size_mb': output_file.get_file_size_mb()
        })
        
    except Exception as e:
        logger.error(f"Failed to generate download URL for file {file_id}: {e}")
        return Response(
            {'error': f'Failed to generate download URL: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_patient_link(request, encounter_id):
    """
    Create patient link for sharing SOAP note.
    """
    try:
        # Get finalized SOAP
        finalized_soap = get_object_or_404(
            FinalizedSOAP,
            soap_draft__encounter_id=encounter_id,
            soap_draft__encounter__doctor=request.user
        )
        
        # Check if finalized SOAP is ready
        if finalized_soap.status != 'exported':
            return Response(
                {'error': 'SOAP note must be fully processed before creating patient link'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get delivery info from request
        delivery_method = request.data.get('delivery_method', 'sms')
        patient_phone = request.data.get('patient_phone', '')
        patient_email = request.data.get('patient_email', '')
        expiry_hours = request.data.get('expiry_hours', 72)
        
        # Validate delivery info
        if delivery_method == 'sms' and not patient_phone:
            return Response(
                {'error': 'Patient phone number required for SMS delivery'},
                status=status.HTTP_400_BAD_REQUEST
            )
        elif delivery_method == 'email' and not patient_email:
            return Response(
                {'error': 'Patient email required for email delivery'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create patient link and send notification
        delivery_info = {
            'method': delivery_method,
            'phone': patient_phone,
            'email': patient_email,
            'expiry_hours': expiry_hours
        }
        
        task = create_patient_link_and_notify.delay(finalized_soap.id, delivery_info)
        
        logger.info(f"Created patient link task for encounter {encounter_id}, task: {task.id}")
        
        return Response({
            'message': 'Patient link creation started',
            'task_id': task.id,
            'delivery_method': delivery_method,
            'expiry_hours': expiry_hours
        })
        
    except Exception as e:
        logger.error(f"Failed to create patient link for encounter {encounter_id}: {e}")
        return Response(
            {'error': f'Failed to create patient link: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_patient_links(request, encounter_id):
    """
    List patient links for an encounter.
    """
    try:
        # Get finalized SOAP
        finalized_soap = get_object_or_404(
            FinalizedSOAP,
            soap_draft__encounter_id=encounter_id,
            soap_draft__encounter__doctor=request.user
        )
        
        # Get patient links
        patient_links = PatientLink.objects.filter(
            finalized_soap=finalized_soap
        ).order_by('-created_at')
        
        serializer = PatientLinkSerializer(patient_links, many=True)
        
        return Response({
            'encounter_id': encounter_id,
            'patient_links': serializer.data
        })
        
    except Exception as e:
        logger.error(f"Failed to list patient links for encounter {encounter_id}: {e}")
        return Response(
            {'error': f'Failed to list patient links: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# Public view for patient access (no authentication required)
@api_view(['GET'])
def access_patient_soap(request, link_id):
    """
    Public endpoint for patients to access their SOAP note.
    """
    try:
        access_token = request.GET.get('token')
        if not access_token:
            return Response(
                {'error': 'Access token required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Use patient linking service to access
        linking_service = PatientLinkingService()
        
        result = linking_service.access_patient_link(link_id, access_token)
        
        if 'error' in result:
            return Response(result, status=status.HTTP_403_FORBIDDEN)
        
        return Response(result)
        
    except Exception as e:
        logger.error(f"Failed to access patient SOAP for link {link_id}: {e}")
        return Response(
            {'error': 'Access failed'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
