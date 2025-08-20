"""
مدل‌های مربوط به دسترسی به اطلاعات بیماران
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
import random
import string


class PatientAccessRequest(models.Model):
    """درخواست دسترسی پزشک به اطلاعات بیمار"""
    
    STATUS_CHOICES = [
        ('pending', 'در انتظار تایید'),
        ('verified', 'تایید شده'),
        ('expired', 'منقضی شده'),
        ('rejected', 'رد شده'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='patient_access_requests')
    patient_phone = models.CharField(max_length=15, help_text="شماره موبایل بیمار")
    
    # OTP fields
    otp_code = models.CharField(max_length=6, blank=True)
    otp_sent_at = models.DateTimeField(blank=True, null=True)
    otp_attempts = models.IntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    verified_at = models.DateTimeField(blank=True, null=True)
    
    # Access details
    access_token = models.CharField(max_length=64, blank=True, unique=True)
    access_expires_at = models.DateTimeField(blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient_phone', 'status']),
            models.Index(fields=['access_token']),
        ]
    
    def __str__(self):
        return f"دسترسی {self.doctor} به بیمار {self.patient_phone} - {self.get_status_display()}"
    
    def generate_otp(self):
        """تولید کد OTP جدید"""
        self.otp_code = ''.join(random.choices(string.digits, k=6))
        self.otp_sent_at = timezone.now()
        self.otp_attempts = 0
        self.save()
        return self.otp_code
    
    def verify_otp(self, code):
        """تایید کد OTP"""
        # بررسی منقضی شدن (5 دقیقه)
        if self.otp_sent_at and (timezone.now() - self.otp_sent_at).seconds > 300:
            self.status = 'expired'
            self.save()
            return False
        
        # بررسی تعداد تلاش‌ها
        if self.otp_attempts >= 3:
            self.status = 'rejected'
            self.save()
            return False
        
        self.otp_attempts += 1
        
        if self.otp_code == code:
            self.status = 'verified'
            self.verified_at = timezone.now()
            self.access_token = self.generate_access_token()
            self.access_expires_at = timezone.now() + timezone.timedelta(hours=24)
            self.save()
            return True
        
        self.save()
        return False
    
    def generate_access_token(self):
        """تولید توکن دسترسی یکتا"""
        return ''.join(random.choices(string.ascii_letters + string.digits, k=64))
    
    def is_access_valid(self):
        """بررسی معتبر بودن دسترسی"""
        if self.status != 'verified':
            return False
        if self.access_expires_at and timezone.now() > self.access_expires_at:
            return False
        return True


class PatientDataCache(models.Model):
    """کش اطلاعات بیمار دریافت شده از SOAPify"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    access_request = models.ForeignKey(PatientAccessRequest, on_delete=models.CASCADE, related_name='cached_data')
    
    # Patient info from SOAPify
    patient_id = models.CharField(max_length=255, help_text="ID کاربر در SOAPify")
    patient_name = models.CharField(max_length=255, blank=True)
    patient_phone = models.CharField(max_length=15)
    
    # Chat summary data
    latest_summary = models.JSONField(help_text="آخرین chat summary")
    summary_date = models.DateTimeField(help_text="تاریخ summary")
    
    # Metadata
    fetched_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-fetched_at']
    
    def __str__(self):
        return f"کش داده بیمار {self.patient_phone} - {self.fetched_at}"
    
    def is_valid(self):
        """بررسی معتبر بودن کش"""
        return timezone.now() < self.expires_at