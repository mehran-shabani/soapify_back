"""
URL patterns برای دسترسی به اطلاعات بیماران
"""
from django.urls import path
from .patient_access_views import (
    RequestPatientAccessView,
    VerifyPatientAccessView,
    GetPatientDataView,
    CreateSOAPifyPaymentView
)

app_name = 'patient_access'

urlpatterns = [
    # دسترسی به اطلاعات بیمار
    path('request/', RequestPatientAccessView.as_view(), name='request_access'),
    path('verify/', VerifyPatientAccessView.as_view(), name='verify_access'),
    path('data/', GetPatientDataView.as_view(), name='get_patient_data'),
    
    # پرداخت برای SOAPify
    path('soapify-payment/', CreateSOAPifyPaymentView.as_view(), name='soapify_payment'),
]