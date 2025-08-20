"""
Crazy Miner API client for OTP/SMS services.
"""

import hmac
import hashlib
import time
import uuid
import requests
import logging
from typing import Dict, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class CrazyMinerClient:
    """Client for Crazy Miner API integration."""
    
    def __init__(self):
        # For tests, allow initialization without API credentials
        self.base_url = getattr(settings, 'CRAZY_MINER_BASE', 'https://api.test.com')
        self.api_key = getattr(settings, 'CRAZY_MINER_API_KEY', 'test-key')
        self.shared_secret = getattr(settings, 'CRAZY_MINER_SHARED_SECRET', 'test-secret')
        self.timeout = 30
        self.max_retries = 3
    
    def send_otp(self, phone_number: str, message: str = None) -> Dict:
        """
        Send OTP to phone number via Crazy Miner.
        
        Args:
            phone_number: Target phone number
            message: Custom OTP message (optional)
            
        Returns:
            Dict with OTP sending result
        """
        try:
            # Prepare request data
            data = {
                'phone_number': phone_number,
                'service': 'soapify_otp'
            }
            
            if message:
                data['message'] = message
            
            # Make authenticated request
            response = self._make_authenticated_request(
                'POST',
                '/api/v1/otp/send',
                data
            )
            
            if response.get('success'):
                logger.info(f"OTP sent successfully to {phone_number}")
                return {
                    'success': True,
                    'otp_id': response.get('otp_id'),
                    'expires_at': response.get('expires_at'),
                    'message': 'OTP sent successfully'
                }
            else:
                logger.error(f"Failed to send OTP to {phone_number}: {response.get('error')}")
                return {
                    'success': False,
                    'error': response.get('error', 'Unknown error')
                }
                
        except Exception as e:
            logger.error(f"OTP sending failed for {phone_number}: {e}")
            return {
                'success': False,
                'error': f'OTP sending failed: {str(e)}'
            }
    
    def verify_otp(self, phone_number: str, otp_code: str, otp_id: str = None) -> Dict:
        """
        Verify OTP code.
        
        Args:
            phone_number: Phone number that received OTP
            otp_code: OTP code to verify
            otp_id: OTP ID from send_otp (optional)
            
        Returns:
            Dict with verification result
        """
        try:
            # Prepare request data
            data = {
                'phone_number': phone_number,
                'otp_code': otp_code
            }
            
            if otp_id:
                data['otp_id'] = otp_id
            
            # Make authenticated request
            response = self._make_authenticated_request(
                'POST',
                '/api/v1/otp/verify',
                data
            )
            
            if response.get('success'):
                logger.info(f"OTP verified successfully for {phone_number}")
                return {
                    'success': True,
                    'verified': True,
                    'user_data': response.get('user_data', {}),
                    'session_token': response.get('session_token'),
                    'expires_at': response.get('expires_at')
                }
            else:
                logger.warning(f"OTP verification failed for {phone_number}: {response.get('error')}")
                return {
                    'success': False,
                    'verified': False,
                    'error': response.get('error', 'Invalid OTP')
                }
                
        except Exception as e:
            logger.error(f"OTP verification failed for {phone_number}: {e}")
            return {
                'success': False,
                'verified': False,
                'error': f'Verification failed: {str(e)}'
            }
    
    def send_sms(self, phone_number: str, message: str) -> Dict:
        """
        Send SMS message via Crazy Miner.
        
        Args:
            phone_number: Target phone number
            message: SMS message content
            
        Returns:
            Dict with SMS sending result
        """
        try:
            # Prepare request data
            data = {
                'phone_number': phone_number,
                'message': message,
                'service': 'soapify_notification'
            }
            
            # Make authenticated request
            response = self._make_authenticated_request(
                'POST',
                '/api/v1/sms/send',
                data
            )
            
            if response.get('success'):
                logger.info(f"SMS sent successfully to {phone_number}")
                return {
                    'success': True,
                    'message_id': response.get('message_id'),
                    'status': response.get('status', 'sent')
                }
            else:
                logger.error(f"Failed to send SMS to {phone_number}: {response.get('error')}")
                return {
                    'success': False,
                    'error': response.get('error', 'SMS sending failed')
                }
                
        except Exception as e:
            logger.error(f"SMS sending failed for {phone_number}: {e}")
            return {
                'success': False,
                'error': f'SMS sending failed: {str(e)}'
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
            logger.error(f"Request failed: {e}")
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
