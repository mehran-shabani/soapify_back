"""
ابزارهای رمزنگاری ساده برای داده‌های پرداخت
استفاده از رمزنگاری متقارن Fernet از کتابخانه cryptography
"""
import base64
import json
from cryptography.fernet import Fernet
from django.conf import settings
import hashlib


class CrazyMinerCrypto:
    """رمزنگاری/رمزگشایی ساده برای داده‌های پرداخت"""
    
    def __init__(self):
        # تولید کلید از SECRET_KEY جنگو
        self.key = self._generate_key_from_secret()
        self.cipher = Fernet(self.key)
    
    def _generate_key_from_secret(self):
        """تولید کلید معتبر Fernet از SECRET_KEY جنگو"""
        # استفاده از SECRET_KEY جنگو برای تولید کلید ثابت
        secret = getattr(settings, 'SECRET_KEY', 'crazyminer-default-secret-key')
        # ایجاد کلید 32 بایتی با SHA256
        hash_obj = hashlib.sha256(secret.encode())
        # Fernet نیاز به کلید 32 بایتی کدگذاری شده base64 دارد
        return base64.urlsafe_b64encode(hash_obj.digest())
    
    def encrypt_data(self, data):
        """
        رمزنگاری داده‌های دیکشنری
        
        Args:
            data (dict): داده برای رمزنگاری
            
        Returns:
            str: داده رمزنگاری شده به صورت رشته
        """
        try:
            # تبدیل دیکشنری به رشته JSON
            json_data = json.dumps(data, ensure_ascii=False)
            # رمزنگاری رشته JSON
            encrypted = self.cipher.encrypt(json_data.encode())
            # بازگشت به صورت رشته base64 برای ذخیره‌سازی
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            raise Exception(f"خطا در رمزنگاری: {str(e)}")
    
    def decrypt_data(self, encrypted_data):
        """
        رمزگشایی داده به دیکشنری
        
        Args:
            encrypted_data (str): رشته داده رمزنگاری شده
            
        Returns:
            dict: داده رمزگشایی شده
        """
        try:
            # دیکد از base64
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data.encode())
            # رمزگشایی داده
            decrypted = self.cipher.decrypt(encrypted_bytes)
            # تبدیل رشته JSON به دیکشنری
            return json.loads(decrypted.decode())
        except Exception as e:
            raise Exception(f"خطا در رمزگشایی: {str(e)}")
    
    def encrypt_payment_data(self, payment_data):
        """رمزنگاری اطلاعات پرداخت"""
        if not payment_data:
            return ""
        
        # فقط اطلاعات ضروری پرداخت رمزنگاری می‌شود
        sensitive_data = {
            'amount': str(payment_data.get('amount', '')),
            'transaction_id': str(payment_data.get('transaction_id', '')),
            'timestamp': str(payment_data.get('timestamp', '')),
        }
        
        return self.encrypt_data(sensitive_data)
    
    def decrypt_payment_data(self, encrypted_payment_data):
        """رمزگشایی اطلاعات پرداخت"""
        if not encrypted_payment_data:
            return {}
        
        return self.decrypt_data(encrypted_payment_data)


# ایجاد نمونه singleton
crazy_crypto = CrazyMinerCrypto()