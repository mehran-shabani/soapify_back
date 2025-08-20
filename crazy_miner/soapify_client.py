"""
کلاینت برای ارتباط با SOAPify و دریافت اطلاعات بیماران
"""
import requests
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class SOAPifyClient:
    """کلاینت برای ارتباط با دیتابیس SOAPify"""
    
    def __init__(self):
        # از تنظیمات یا اتصال مستقیم به دیتابیس
        self.base_url = getattr(settings, 'SOAPIFY_API_URL', 'http://localhost:8000/api')
        self.api_key = getattr(settings, 'SOAPIFY_API_KEY', '')
        self.timeout = 30
        
        # برای اتصال مستقیم به دیتابیس (اگر نیاز باشد)
        self.use_direct_db = getattr(settings, 'SOAPIFY_USE_DIRECT_DB', False)
    
    def get_user_by_phone(self, phone_number):
        """دریافت اطلاعات کاربر با شماره تلفن"""
        try:
            if self.use_direct_db:
                # اتصال مستقیم به دیتابیس SOAPify
                from accounts.models import User  # مدل User در SOAPify
                
                user = User.objects.filter(phone_number=phone_number).first()
                if user:
                    return {
                        'success': True,
                        'user': {
                            'id': str(user.id),
                            'phone_number': user.phone_number,
                            'username': user.username,
                            'email': user.email,
                        }
                    }
                else:
                    return {
                        'success': False,
                        'error': 'کاربری با این شماره یافت نشد'
                    }
            else:
                # ارتباط از طریق API
                response = requests.get(
                    f"{self.base_url}/users/by-phone/{phone_number}/",
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json'
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return {
                        'success': True,
                        'user': response.json()
                    }
                else:
                    return {
                        'success': False,
                        'error': f'خطا در دریافت اطلاعات کاربر: {response.status_code}'
                    }
                    
        except Exception as e:
            logger.error(f"خطا در دریافت کاربر با شماره {phone_number}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_latest_chat_summary(self, user_id):
        """دریافت آخرین chat summary کاربر"""
        try:
            if self.use_direct_db:
                # اتصال مستقیم به دیتابیس
                from chatbot.models import ChatSummary  # فرض بر وجود این مدل
                
                summary = ChatSummary.objects.filter(
                    user_id=user_id
                ).order_by('-updated_at').first()
                
                if summary:
                    return {
                        'success': True,
                        'summary': {
                            'id': str(summary.id),
                            'content': summary.content,
                            'summary_text': summary.summary_text,
                            'created_at': summary.created_at.isoformat(),
                            'updated_at': summary.updated_at.isoformat(),
                        }
                    }
                else:
                    return {
                        'success': False,
                        'error': 'خلاصه‌ای یافت نشد'
                    }
            else:
                # ارتباط از طریق API
                response = requests.get(
                    f"{self.base_url}/chat/summaries/latest/{user_id}/",
                    headers={
                        'Authorization': f'Bearer {self.api_key}',
                        'Content-Type': 'application/json'
                    },
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    return {
                        'success': True,
                        'summary': response.json()
                    }
                else:
                    return {
                        'success': False,
                        'error': f'خطا در دریافت خلاصه: {response.status_code}'
                    }
                    
        except Exception as e:
            logger.error(f"خطا در دریافت chat summary برای کاربر {user_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_patient_data(self, phone_number):
        """دریافت کامل اطلاعات بیمار (کاربر + آخرین summary)"""
        # ابتدا چک کردن کش
        cache_key = f"patient_data_{phone_number}"
        cached_data = cache.get(cache_key)
        if cached_data:
            logger.info(f"اطلاعات بیمار {phone_number} از کش خوانده شد")
            return cached_data
        
        # دریافت اطلاعات کاربر
        user_result = self.get_user_by_phone(phone_number)
        if not user_result['success']:
            return user_result
        
        user_data = user_result['user']
        user_id = user_data['id']
        
        # دریافت آخرین chat summary
        summary_result = self.get_latest_chat_summary(user_id)
        
        result = {
            'success': True,
            'patient': {
                'user': user_data,
                'latest_summary': summary_result.get('summary') if summary_result['success'] else None,
                'has_summary': summary_result['success']
            }
        }
        
        # ذخیره در کش برای 1 ساعت
        cache.set(cache_key, result, 3600)
        
        return result


# ایجاد نمونه singleton
soapify_client = SOAPifyClient()