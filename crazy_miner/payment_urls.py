"""
URL patterns برای CrazyMiner Payment
"""
from django.urls import path
from .payment_views import (
    CrazyMinerCreatePaymentView,
    CrazyMinerPaymentCallbackView,
    CrazyMinerPaymentStatusView,
    CrazyMinerPaymentListView
)

app_name = 'crazyminer_payment'

urlpatterns = [
    # ایجاد پرداخت جدید
    path('create/', CrazyMinerCreatePaymentView.as_view(), name='create'),
    
    # دریافت callback از درگاه
    path('callback/', CrazyMinerPaymentCallbackView.as_view(), name='callback'),
    
    # بررسی وضعیت پرداخت
    path('status/<uuid:transaction_id>/', CrazyMinerPaymentStatusView.as_view(), name='status'),
    
    # لیست پرداخت‌های کاربر
    path('list/', CrazyMinerPaymentListView.as_view(), name='list'),
]