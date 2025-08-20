"""
Payment Gateway Client
Handles communication with external payment server
"""
import requests
import logging
from django.conf import settings
from .crypto import payment_crypto

logger = logging.getLogger(__name__)


class PaymentGatewayClient:
    """Client for external payment gateway"""
    
    def __init__(self):
        # Base URL from settings or default to api.medogram.ir
        self.base_url = getattr(settings, 'PAYMENT_GATEWAY_URL', 'https://api.medogram.ir')
        self.api_key = getattr(settings, 'PAYMENT_API_KEY', '')
        self.timeout = 30  # seconds
        
        # Payment endpoints - these should not change as per requirements
        self.endpoints = {
            'create_payment': '/payment/gateway-send',
            'verify_payment': '/payment/gateway-result-second',
            'get_payment': '/payment/gateway-{id}-get'
        }
    
    def _prepare_headers(self):
        """Prepare request headers"""
        return {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
    
    def _encrypt_sensitive_data(self, data):
        """Encrypt sensitive fields in the data"""
        sensitive_fields = ['card_number', 'cvv', 'pin', 'password']
        encrypted_data = data.copy()
        
        for field in sensitive_fields:
            if field in encrypted_data and encrypted_data[field]:
                encrypted_data[field] = payment_crypto.encrypt_field(encrypted_data[field])
        
        return encrypted_data
    
    def create_payment_request(self, amount, order_id, redirect_url, user_data=None):
        """
        Create a payment request
        
        Args:
            amount: Payment amount
            order_id: Unique order/transaction ID
            redirect_url: URL to redirect after payment
            user_data: Additional user data (optional)
            
        Returns:
            dict: Response from payment gateway
        """
        try:
            # Prepare payment data
            payment_data = {
                'api': self.api_key,
                'amount': amount,
                'factorId': order_id,
                'redirect': redirect_url,
            }
            
            # Add optional user data if provided
            if user_data:
                payment_data.update(user_data)
            
            # Log the request (without sensitive data)
            logger.info(f"Creating payment request for order {order_id}, amount: {amount}")
            
            # Make the request
            response = requests.post(
                f"{self.base_url}{self.endpoints['create_payment']}",
                json=payment_data,
                headers=self._prepare_headers(),
                timeout=self.timeout
            )
            
            # Check response
            if response.status_code == 200:
                result = response.json()
                
                # Extract payment ID from response
                if isinstance(result, (int, str)) and int(result) > 0:
                    payment_id = str(result)
                    payment_url = self.endpoints['get_payment'].format(id=payment_id)
                    
                    return {
                        'success': True,
                        'payment_id': payment_id,
                        'payment_url': f"{self.base_url}{payment_url}",
                        'raw_response': result
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Invalid response from payment gateway',
                        'raw_response': result
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"Payment request timeout for order {order_id}")
            return {
                'success': False,
                'error': 'Payment gateway timeout'
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for order {order_id}")
            return {
                'success': False,
                'error': 'Failed to connect to payment gateway'
            }
        except Exception as e:
            logger.error(f"Payment request error for order {order_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_payment(self, trans_id, id_get):
        """
        Verify a payment transaction
        
        Args:
            trans_id: Transaction ID from callback
            id_get: Payment ID from gateway
            
        Returns:
            dict: Verification result
        """
        try:
            verify_data = {
                'api': self.api_key,
                'id_get': id_get,
                'trans_id': trans_id
            }
            
            logger.info(f"Verifying payment: trans_id={trans_id}, id_get={id_get}")
            
            response = requests.post(
                f"{self.base_url}{self.endpoints['verify_payment']}",
                json=verify_data,
                headers=self._prepare_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Check if payment is verified (response > 0 means success)
                if isinstance(result, (int, str)) and int(result) > 0:
                    return {
                        'success': True,
                        'verified': True,
                        'amount': result,
                        'raw_response': result
                    }
                else:
                    return {
                        'success': True,
                        'verified': False,
                        'error': 'Payment not verified',
                        'raw_response': result
                    }
            else:
                return {
                    'success': False,
                    'verified': False,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            return {
                'success': False,
                'verified': False,
                'error': str(e)
            }
    
    def get_payment_status(self, payment_id):
        """
        Get payment status (optional method)
        
        Args:
            payment_id: Payment ID to check
            
        Returns:
            dict: Payment status
        """
        try:
            url = f"{self.base_url}{self.endpoints['get_payment'].format(id=payment_id)}"
            
            response = requests.get(
                url,
                headers=self._prepare_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Create singleton instance
payment_gateway = PaymentGatewayClient()