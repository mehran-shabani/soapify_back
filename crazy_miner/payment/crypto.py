"""
Simple encryption utilities for payment data
Using Fernet symmetric encryption from cryptography library
"""
import base64
import json
from cryptography.fernet import Fernet
from django.conf import settings
import hashlib


class PaymentCrypto:
    """Simple encryption/decryption for payment data"""
    
    def __init__(self):
        # Generate key from Django SECRET_KEY
        self.key = self._generate_key_from_secret()
        self.cipher = Fernet(self.key)
    
    def _generate_key_from_secret(self):
        """Generate a valid Fernet key from Django's SECRET_KEY"""
        # Use Django's SECRET_KEY to generate a consistent key
        secret = getattr(settings, 'SECRET_KEY', 'default-secret-key')
        # Create a 32-byte key using SHA256
        hash_obj = hashlib.sha256(secret.encode())
        # Fernet requires base64-encoded 32-byte key
        return base64.urlsafe_b64encode(hash_obj.digest())
    
    def encrypt_data(self, data):
        """
        Encrypt dictionary data
        
        Args:
            data (dict): Data to encrypt
            
        Returns:
            str: Encrypted data as string
        """
        try:
            # Convert dict to JSON string
            json_data = json.dumps(data)
            # Encrypt the JSON string
            encrypted = self.cipher.encrypt(json_data.encode())
            # Return as base64 string for storage
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            raise Exception(f"Encryption failed: {str(e)}")
    
    def decrypt_data(self, encrypted_data):
        """
        Decrypt data back to dictionary
        
        Args:
            encrypted_data (str): Encrypted data string
            
        Returns:
            dict: Decrypted data
        """
        try:
            # Decode from base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            # Decrypt the data
            decrypted = self.cipher.decrypt(encrypted_bytes)
            # Convert JSON string back to dict
            return json.loads(decrypted.decode())
        except Exception as e:
            raise Exception(f"Decryption failed: {str(e)}")
    
    def encrypt_field(self, value):
        """Encrypt a single field value"""
        if not value:
            return ""
        try:
            encrypted = self.cipher.encrypt(str(value).encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception:
            return ""
    
    def decrypt_field(self, encrypted_value):
        """Decrypt a single field value"""
        if not encrypted_value:
            return ""
        try:
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception:
            return ""


# Create a singleton instance
payment_crypto = PaymentCrypto()