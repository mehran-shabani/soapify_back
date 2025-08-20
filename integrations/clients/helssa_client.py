"""
Helssa API client for read-only patient data access.
"""

import hmac
import hashlib
import time
import uuid
import requests
import logging
from typing import Dict, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class HelssaClient:
    """Client for Helssa API integration (read-only)."""
    
    def __init__(self):
        self.base_url = getattr(settings, 'HELSSA_BASE_URL', 'https://api.helssa.com')
        self.api_key = getattr(settings, 'HELSSA_API_KEY', '')
        self.shared_secret = getattr(settings, 'HELSSA_SHARED_SECRET', '')
        self.timeout = 30
        self.max_retries = 3
    
    def search_patients(self, query: str, limit: int = 20) -> Dict:
        """
        Search patients by name, phone, or national ID.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            Dict with search results (no PHI)
        """
        try:
            # Prepare request data
            data = {
                'query': query,
                'limit': min(limit, 50),  # Max 50 results
                'fields': ['patient_ref', 'display_name', 'age_group', 'gender']  # No PHI
            }
            
            # Make authenticated request
            response = self._make_authenticated_request(
                'GET',
                '/api/v1/patients/search',
                data
            )
            
            if response.get('success'):
                patients = response.get('patients', [])
                # Filter out any PHI that might accidentally be included
                filtered_patients = []
                for patient in patients:
                    filtered_patient = {
                        'patient_ref': patient.get('patient_ref'),
                        'display_name': self._mask_name(patient.get('display_name', '')),
                        'age_group': patient.get('age_group'),
                        'gender': patient.get('gender'),
                        'last_visit': patient.get('last_visit_date')
                    }
                    filtered_patients.append(filtered_patient)
                
                logger.info(f"Patient search completed: {len(filtered_patients)} results")
                return {
                    'success': True,
                    'patients': filtered_patients,
                    'total_results': len(filtered_patients)
                }
            else:
                logger.error(f"Patient search failed: {response.get('error')}")
                return {
                    'success': False,
                    'error': response.get('error', 'Search failed')
                }
                
        except Exception as e:
            logger.error(f"Patient search failed: {e}")
            return {
                'success': False,
                'error': f'Search failed: {str(e)}'
            }
    
    def get_patient_basic_info(self, patient_ref: str) -> Dict:
        """
        Get basic patient information (no PHI).
        
        Args:
            patient_ref: Patient reference ID
            
        Returns:
            Dict with basic patient info
        """
        try:
            # Prepare request data
            data = {
                'patient_ref': patient_ref,
                'fields': ['patient_ref', 'age_group', 'gender', 'last_visit_date']
            }
            
            # Make authenticated request
            response = self._make_authenticated_request(
                'GET',
                f'/api/v1/patients/{patient_ref}/basic',
                data
            )
            
            if response.get('success'):
                patient_data = response.get('patient', {})
                # Ensure no PHI is included
                filtered_data = {
                    'patient_ref': patient_data.get('patient_ref'),
                    'age_group': patient_data.get('age_group'),
                    'gender': patient_data.get('gender'),
                    'last_visit_date': patient_data.get('last_visit_date'),
                    'active_status': patient_data.get('active_status', True)
                }
                
                logger.info(f"Retrieved basic info for patient {patient_ref}")
                return {
                    'success': True,
                    'patient': filtered_data
                }
            else:
                logger.error(f"Failed to get patient info for {patient_ref}: {response.get('error')}")
                return {
                    'success': False,
                    'error': response.get('error', 'Patient not found')
                }
                
        except Exception as e:
            logger.error(f"Failed to get patient info for {patient_ref}: {e}")
            return {
                'success': False,
                'error': f'Failed to get patient info: {str(e)}'
            }
    
    def verify_patient_access(self, patient_ref: str, doctor_id: str) -> Dict:
        """
        Verify if doctor has access to patient records.
        
        Args:
            patient_ref: Patient reference ID
            doctor_id: Doctor ID or username
            
        Returns:
            Dict with access verification result
        """
        try:
            # Prepare request data
            data = {
                'patient_ref': patient_ref,
                'doctor_id': doctor_id,
                'access_type': 'read_only'
            }
            
            # Make authenticated request
            response = self._make_authenticated_request(
                'POST',
                '/api/v1/access/verify',
                data
            )
            
            if response.get('success'):
                logger.info(f"Access verified for doctor {doctor_id} to patient {patient_ref}")
                return {
                    'success': True,
                    'access_granted': response.get('access_granted', False),
                    'access_level': response.get('access_level', 'none'),
                    'expires_at': response.get('expires_at')
                }
            else:
                logger.warning(f"Access verification failed: {response.get('error')}")
                return {
                    'success': False,
                    'access_granted': False,
                    'error': response.get('error', 'Access denied')
                }
                
        except Exception as e:
            logger.error(f"Access verification failed: {e}")
            return {
                'success': False,
                'access_granted': False,
                'error': f'Verification failed: {str(e)}'
            }
    
    def _make_authenticated_request(self, method: str, endpoint: str, data: Dict) -> Dict:
        """Make authenticated request with HMAC."""
        try:
            url = f"{self.base_url.rstrip('/')}{endpoint}"
            timestamp = str(int(time.time()))
            nonce = str(uuid.uuid4())
            
            headers = {
                'Content-Type': 'application/json',
                'X-API-Key': self.api_key,
                'X-HMAC-Timestamp': timestamp,
                'X-HMAC-Nonce': nonce,
                'User-Agent': 'SOAPify/1.0'
            }
            
            # Calculate HMAC signature
            signature = self._calculate_hmac_signature(
                method, endpoint, timestamp, nonce, data
            )
            headers['X-HMAC-Signature'] = signature
            
            # Make request
            if method.upper() == 'GET':
                response = requests.get(url, params=data, headers=headers, timeout=self.timeout)
            else:
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text[:200]}'
                }
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _calculate_hmac_signature(
        self, 
        method: str, 
        endpoint: str, 
        timestamp: str, 
        nonce: str, 
        data: Dict
    ) -> str:
        """Calculate HMAC signature for request."""
        import json
        body = json.dumps(data, sort_keys=True, separators=(',', ':'))
        
        message_parts = [
            method.upper(),
            endpoint,
            timestamp,
            nonce,
            body
        ]
        message = '\n'.join(message_parts)
        
        signature = hmac.new(
            self.shared_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _mask_name(self, name: str) -> str:
        """Mask patient name to protect privacy."""
        if not name or len(name) < 3:
            return "***"
        
        # Show first and last character, mask middle
        return f"{name[0]}{'*' * (len(name) - 2)}{name[-1]}"
    
    def health_check(self) -> bool:
        """Check if Helssa API is accessible."""
        try:
            response = self._make_authenticated_request(
                'GET',
                '/api/v1/health',
                {}
            )
            return response.get('success', False)
            
        except Exception as e:
            logger.error(f"Helssa health check failed: {e}")
            return False
