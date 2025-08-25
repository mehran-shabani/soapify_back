"""
URL patterns for billing app.
"""

from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Wallet
    path('wallet/', views.get_wallet_info, name='wallet_info'),
    path('wallet/add-credit/', views.add_credit, name='add_credit'),
    
    # Subscriptions
    path('plans/', views.list_subscription_plans, name='subscription_plans'),
    path('subscription/', views.get_current_subscription, name='current_subscription'),
    path('subscription/create/', views.create_subscription, name='create_subscription'),
    path('subscription/cancel/', views.cancel_subscription, name='cancel_subscription'),
    
    # Transactions
    path('transactions/', views.list_transactions, name='transactions'),
    path('transactions/<int:transaction_id>/verify/', views.verify_payment, name='verify_payment'),
    
    # Usage
    path('usage/', views.get_usage_summary, name='usage_summary'),
]