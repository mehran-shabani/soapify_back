"""
Patient linking service for sharing SOAP notes with patients.
"""

import secrets
import logging
from datetime import timedelta
from typing import Dict, Optional
from django.utils import timezone
from ..models import PatientLink, FinalizedSOAP

logger = logging.getLogger(__name__)


class PatientLinkingService:
    """Service for creating and managing patient links."""
    
    def __init__(self):
        self.default_expiry_hours = 72  # 3 days
        self.max_views = 5
        self.token_length = 32
    
    def create_patient_link(
        self,
        finalized_soap: FinalizedSOAP,
        delivery_method: str = 'sms',
        patient_phone: str = '',
        patient_email: str = '',
        custom_expiry_hours: Optional[int] = None
    ) -> PatientLink:
        """
        Create a secure patient link for accessing SOAP note.
        
        Args:
            finalized_soap: FinalizedSOAP instance
            delivery_method: 'sms', 'email', or 'direct'
            patient_phone: Patient phone number for SMS
            patient_email: Patient email for email delivery
            custom_expiry_hours: Custom expiration time
            
        Returns:
            PatientLink instance
        """
        try:
            # Generate secure access token
            access_token = secrets.token_urlsafe(self.token_length)
            
            # Calculate expiry time
            expiry_hours = custom_expiry_hours or self.default_expiry_hours
            expires_at = timezone.now() + timedelta(hours=expiry_hours)
            
            # Create patient link
            patient_link = PatientLink.objects.create(
                finalized_soap=finalized_soap,
                access_token=access_token,
                patient_phone=patient_phone,
                patient_email=patient_email,
                delivery_method=delivery_method,
                expires_at=expires_at,
                max_views=self.max_views
            )
            
            logger.info(
                f"Created patient link {patient_link.link_id} for {finalized_soap.patient_ref}"
            )
            
            return patient_link
            
        except Exception as e:
            logger.error(f"Failed to create patient link: {e}")
            raise
    
    def get_link_status(self, link_id: str) -> Dict:
        """
        Get status information for a patient link.
        
        Args:
            link_id: UUID of the patient link
            
        Returns:
            Dict with link status and accessibility info
        """
        try:
            patient_link = PatientLink.objects.get(link_id=link_id)
            
            return {
                'link_id': str(patient_link.link_id),
                'status': patient_link.status,
                'is_accessible': patient_link.is_accessible,
                'is_expired': patient_link.is_expired,
                'view_count': patient_link.view_count,
                'max_views': patient_link.max_views,
                'expires_at': patient_link.expires_at,
                'created_at': patient_link.created_at,
                'sent_at': patient_link.sent_at,
                'first_viewed_at': patient_link.first_viewed_at,
                'last_viewed_at': patient_link.last_viewed_at
            }
            
        except PatientLink.DoesNotExist:
            return {'error': 'Link not found'}
        except Exception as e:
            logger.error(f"Failed to get link status: {e}")
            return {'error': str(e)}
    
    def access_patient_link(self, link_id: str, access_token: str) -> Dict:
        """
        Access patient link and return SOAP data if valid.
        
        Args:
            link_id: UUID of the patient link
            access_token: Access token for verification
            
        Returns:
            Dict with SOAP data or error message
        """
        try:
            patient_link = PatientLink.objects.get(
                link_id=link_id,
                access_token=access_token
            )
            
            # Check if link is accessible
            if not patient_link.is_accessible:
                if patient_link.is_expired:
                    return {'error': 'Link has expired'}
                elif patient_link.view_count >= patient_link.max_views:
                    return {'error': 'Maximum views exceeded'}
                else:
                    return {'error': 'Link is not accessible'}
            
            # Update view tracking
            patient_link.view_count += 1
            if patient_link.view_count == 1:
                patient_link.first_viewed_at = timezone.now()
                patient_link.status = 'viewed'
            patient_link.last_viewed_at = timezone.now()
            patient_link.save()
            
            # Get finalized SOAP data
            finalized_soap = patient_link.finalized_soap
            
            # Return patient-friendly data
            return {
                'patient_ref': finalized_soap.patient_ref,
                'doctor_name': finalized_soap.soap_draft.encounter.doctor.get_full_name(),
                'encounter_date': finalized_soap.soap_draft.encounter.created_at,
                'soap_data': finalized_soap.finalized_data,
                'view_count': patient_link.view_count,
                'max_views': patient_link.max_views,
                'expires_at': patient_link.expires_at
            }
            
        except PatientLink.DoesNotExist:
            return {'error': 'Invalid link or token'}
        except Exception as e:
            logger.error(f"Failed to access patient link: {e}")
            return {'error': 'Access failed'}
    
    def mark_link_as_sent(self, link_id: str) -> bool:
        """Mark patient link as sent."""
        try:
            patient_link = PatientLink.objects.get(link_id=link_id)
            patient_link.status = 'sent'
            patient_link.sent_at = timezone.now()
            patient_link.save()
            
            logger.info(f"Marked link {link_id} as sent")
            return True
            
        except PatientLink.DoesNotExist:
            logger.error(f"Patient link {link_id} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to mark link as sent: {e}")
            return False
    
    def expire_link(self, link_id: str) -> bool:
        """Manually expire a patient link."""
        try:
            patient_link = PatientLink.objects.get(link_id=link_id)
            patient_link.status = 'expired'
            patient_link.expires_at = timezone.now()
            patient_link.save()
            
            logger.info(f"Expired link {link_id}")
            return True
            
        except PatientLink.DoesNotExist:
            logger.error(f"Patient link {link_id} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to expire link: {e}")
            return False
    
    def cleanup_expired_links(self) -> int:
        """Clean up expired patient links."""
        try:
            expired_links = PatientLink.objects.filter(
                expires_at__lt=timezone.now(),
                status__in=['pending', 'sent', 'viewed']
            )
            
            count = expired_links.count()
            expired_links.update(status='expired')
            
            logger.info(f"Cleaned up {count} expired patient links")
            return count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired links: {e}")
            return 0
    
    def get_link_statistics(self, finalized_soap_id: int) -> Dict:
        """Get statistics for patient links of a finalized SOAP."""
        try:
            links = PatientLink.objects.filter(finalized_soap_id=finalized_soap_id)
            
            return {
                'total_links': links.count(),
                'sent_links': links.filter(status='sent').count(),
                'viewed_links': links.filter(status='viewed').count(),
                'expired_links': links.filter(status='expired').count(),
                'total_views': sum(link.view_count for link in links),
                'last_viewed': links.filter(last_viewed_at__isnull=False)
                                  .order_by('-last_viewed_at')
                                  .first()
            }
            
        except Exception as e:
            logger.error(f"Failed to get link statistics: {e}")
            return {'error': str(e)}

