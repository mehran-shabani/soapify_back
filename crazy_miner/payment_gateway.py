"""
Payment Gateway Client برای CrazyMiner
مدیریت ارتباط با سرور خارجی پرداخت و دریافت اطلاعات کاربر
"""
import requests
import logging
from django.conf import settings
from .payment_crypto import crazy_crypto

logger = logging.getLogger(__name__)


class CrazyMinerGateway:
    """کلاینت برای درگاه پرداخت خارجی و دریافت اطلاعات کاربر"""
    
    def __init__(self):
        # Base URL از تنظیمات یا پیش‌فرض api.medogram.ir
        self.base_url = getattr(settings, 'PAYMENT_GATEWAY_URL', 'https://api.medogram.ir')
        self.api_key = getattr(settings, 'PAYMENT_API_KEY', '')
        self.timeout = 30  # ثانیه
        
        # نقاط پایانی پرداخت - اینها نباید تغییر کنند طبق نیازمندی
        self.endpoints = {
            'create_payment': '/payment/gateway-send',
            'verify_payment': '/payment/gateway-result-second',
            'get_payment': '/payment/gateway-{id}-get',
            'get_user_info': '/api/v1/user/info',  # endpoint برای دریافت اطلاعات کاربر
        }
    
    def _prepare_headers(self, auth_token=None):
        """آماده‌سازی هدرهای درخواست"""
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        
        if auth_token:
            headers['Authorization'] = f'Bearer {auth_token}'
        
        return headers
    
    def get_user_info(self, user_identifier, auth_token=None):
        """
        دریافت اطلاعات کاربر از سرور اصلی
        
        Args:
            user_identifier: شناسه کاربر (phone_number یا user_id)
            auth_token: توکن احراز هویت (اختیاری)
            
        Returns:
            dict: اطلاعات کاربر یا خطا
        """
        try:
            # آماده‌سازی داده درخواست
            request_data = {
                'identifier': user_identifier,
                'source': 'crazy_miner'
            }
            
            logger.info(f"درخواست اطلاعات کاربر: {user_identifier}")
            
            response = requests.post(
                f"{self.base_url}{self.endpoints['get_user_info']}",
                json=request_data,
                headers=self._prepare_headers(auth_token),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                user_data = response.json()
                
                # ذخیره اطلاعات حساس به صورت رمزنگاری شده
                if 'sensitive_data' in user_data:
                    encrypted_info = crazy_crypto.encrypt_user_info(user_data['sensitive_data'])
                    user_data['encrypted_info'] = encrypted_info
                    # حذف اطلاعات حساس از پاسخ
                    del user_data['sensitive_data']
                
                return {
                    'success': True,
                    'user_data': user_data
                }
            else:
                return {
                    'success': False,
                    'error': f'خطا در دریافت اطلاعات کاربر: HTTP {response.status_code}',
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات کاربر {user_identifier}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def create_payment_request(self, amount, order_id, redirect_url, user_data=None):
        """
        ایجاد درخواست پرداخت
        
        Args:
            amount: مبلغ پرداخت (ریال)
            order_id: شناسه یکتای سفارش/تراکنش
            redirect_url: URL بازگشت پس از پرداخت
            user_data: اطلاعات اضافی کاربر (اختیاری)
            
        Returns:
            dict: پاسخ از درگاه پرداخت
        """
        try:
            # آماده‌سازی داده‌های پرداخت
            payment_data = {
                'api': self.api_key,
                'amount': int(amount),  # اطمینان از ارسال به صورت عدد صحیح
                'factorId': str(order_id),
                'redirect': redirect_url,
            }
            
            # افزودن اطلاعات کاربر در صورت وجود
            if user_data:
                # رمزنگاری اطلاعات حساس قبل از ارسال
                if 'user_info' in user_data:
                    encrypted_info = crazy_crypto.encrypt_user_info(user_data['user_info'])
                    payment_data['encrypted_user_info'] = encrypted_info
                else:
                    payment_data.update(user_data)
            
            logger.info(f"ایجاد درخواست پرداخت برای سفارش {order_id}, مبلغ: {amount} ریال")
            
            # ارسال درخواست
            response = requests.post(
                f"{self.base_url}{self.endpoints['create_payment']}",
                json=payment_data,
                headers=self._prepare_headers(),
                timeout=self.timeout
            )
            
            # بررسی پاسخ
            if response.status_code == 200:
                result = response.json()
                
                # استخراج شناسه پرداخت از پاسخ
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
                        'error': 'پاسخ نامعتبر از درگاه پرداخت',
                        'raw_response': result
                    }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'status_code': response.status_code
                }
                
        except requests.exceptions.Timeout:
            logger.error(f"تایم‌اوت درخواست پرداخت برای سفارش {order_id}")
            return {
                'success': False,
                'error': 'تایم‌اوت درگاه پرداخت'
            }
        except requests.exceptions.ConnectionError:
            logger.error(f"خطای اتصال برای سفارش {order_id}")
            return {
                'success': False,
                'error': 'عدم اتصال به درگاه پرداخت'
            }
        except Exception as e:
            logger.error(f"خطای درخواست پرداخت برای سفارش {order_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def verify_payment(self, trans_id, id_get):
        """
        تایید تراکنش پرداخت
        
        Args:
            trans_id: شناسه تراکنش از callback
            id_get: شناسه پرداخت از درگاه
            
        Returns:
            dict: نتیجه تایید
        """
        try:
            verify_data = {
                'api': self.api_key,
                'id_get': id_get,
                'trans_id': trans_id
            }
            
            logger.info(f"تایید پرداخت: trans_id={trans_id}, id_get={id_get}")
            
            response = requests.post(
                f"{self.base_url}{self.endpoints['verify_payment']}",
                json=verify_data,
                headers=self._prepare_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # بررسی تایید پرداخت (پاسخ > 0 یعنی موفق)
                if isinstance(result, (int, str)) and int(result) > 0:
                    return {
                        'success': True,
                        'verified': True,
                        'amount': int(result),
                        'raw_response': result
                    }
                else:
                    return {
                        'success': True,
                        'verified': False,
                        'error': 'پرداخت تایید نشد',
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
            logger.error(f"خطای تایید پرداخت: {str(e)}")
            return {
                'success': False,
                'verified': False,
                'error': str(e)
            }


# ایجاد نمونه singleton
crazy_gateway = CrazyMinerGateway()