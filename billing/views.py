"""
Views for billing app.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal

from .models import Wallet, SubscriptionPlan, Subscription, Transaction, UsageLog
from .serializers import (
    WalletSerializer, SubscriptionPlanSerializer, SubscriptionSerializer,
    TransactionSerializer, AddCreditSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_wallet_info(request):
    """Get user's wallet information."""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    serializer = WalletSerializer(wallet)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_subscription_plans(request):
    """List all active subscription plans."""
    plans = SubscriptionPlan.objects.filter(is_active=True)
    serializer = SubscriptionPlanSerializer(plans, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_subscription(request):
    """Get user's current active subscription."""
    subscription = Subscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    if subscription:
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data)
    
    return Response(
        {'detail': 'No active subscription found'},
        status=status.HTTP_404_NOT_FOUND
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    """Create a new subscription for the user."""
    serializer = SubscriptionSerializer(data=request.data)
    
    if serializer.is_valid():
        # Check if user already has an active subscription
        existing = Subscription.objects.filter(
            user=request.user,
            status='active'
        ).exists()
        
        if existing:
            return Response(
                {'error': 'User already has an active subscription'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create subscription
        subscription = serializer.save(user=request.user)
        
        # Try to activate if user has sufficient balance
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        if wallet.has_sufficient_balance(subscription.plan.price):
            with db_transaction.atomic():
                # Deduct from wallet
                wallet.deduct(
                    amount=subscription.plan.price,
                    description=f"Subscription: {subscription.plan.name}"
                )
                # Activate subscription
                subscription.activate()
        
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """Cancel user's active subscription."""
    subscription = get_object_or_404(
        Subscription,
        user=request.user,
        status='active'
    )
    
    subscription.cancel()
    
    return Response({
        'message': 'Subscription cancelled successfully',
        'subscription_id': subscription.id
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_credit(request):
    """Add credit to user's wallet."""
    serializer = AddCreditSerializer(data=request.data)
    
    if serializer.is_valid():
        amount = serializer.validated_data['amount']
        gateway = serializer.validated_data['gateway']
        
        # Create pending transaction
        transaction = Transaction.objects.create(
            user=request.user,
            amount=amount,
            transaction_type='credit',
            status='pending',
            description=f'Add credit via {gateway}'
        )
        
        # Here you would integrate with payment gateway
        # For now, we'll just return the transaction info
        
        return Response({
            'transaction_id': transaction.id,
            'amount': amount,
            'gateway': gateway,
            'payment_url': f'/pay/{gateway}/{transaction.id}/',  # Mock URL
            'message': 'Redirect user to payment gateway'
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_transactions(request):
    """List user's transactions."""
    transactions = Transaction.objects.filter(user=request.user)
    
    # Filter by type if provided
    transaction_type = request.query_params.get('type')
    if transaction_type:
        transactions = transactions.filter(transaction_type=transaction_type)
    
    # Filter by status if provided
    status_filter = request.query_params.get('status')
    if status_filter:
        transactions = transactions.filter(status=status_filter)
    
    # Pagination
    limit = int(request.query_params.get('limit', 20))
    offset = int(request.query_params.get('offset', 0))
    
    transactions = transactions[offset:offset + limit]
    
    serializer = TransactionSerializer(transactions, many=True)
    return Response({
        'results': serializer.data,
        'count': len(serializer.data),
        'limit': limit,
        'offset': offset
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_usage_summary(request):
    """Get user's usage summary for current subscription."""
    subscription = Subscription.objects.filter(
        user=request.user,
        status='active'
    ).first()
    
    if not subscription:
        return Response(
            {'error': 'No active subscription found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get usage logs for current month
    from django.utils import timezone
    from datetime import timedelta
    
    start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0)
    usage_logs = UsageLog.objects.filter(
        user=request.user,
        subscription=subscription,
        created_at__gte=start_of_month
    )
    
    # Calculate usage by feature
    usage_summary = {
        'encounters': {
            'used': subscription.encounters_used,
            'limit': subscription.plan.max_encounters_per_month,
            'percentage': round((subscription.encounters_used / subscription.plan.max_encounters_per_month) * 100, 2)
        },
        'stt_minutes': {
            'used': subscription.stt_minutes_used,
            'limit': subscription.plan.max_stt_minutes_per_month,
            'percentage': round((subscription.stt_minutes_used / subscription.plan.max_stt_minutes_per_month) * 100, 2)
        },
        'ai_requests': {
            'used': subscription.ai_requests_used,
            'limit': subscription.plan.max_ai_requests_per_month,
            'percentage': round((subscription.ai_requests_used / subscription.plan.max_ai_requests_per_month) * 100, 2)
        }
    }
    
    return Response({
        'subscription_id': subscription.id,
        'plan_name': subscription.plan.name,
        'expires_at': subscription.expires_at,
        'usage_summary': usage_summary
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def verify_payment(request, transaction_id):
    """Verify payment and complete transaction."""
    transaction = get_object_or_404(
        Transaction,
        id=transaction_id,
        user=request.user,
        status='pending'
    )
    
    # Here you would verify with payment gateway
    # For now, we'll just simulate success
    
    # Simulate verification
    verified = request.data.get('verified', False)
    reference = request.data.get('reference', '')
    
    if verified:
        with db_transaction.atomic():
            # Update transaction
            transaction.status = 'completed'
            transaction.reference_id = reference
            transaction.complete()
            
            # Update wallet
            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            wallet.balance += transaction.amount
            wallet.save()
            
            # Update transaction balance
            transaction.balance_after = wallet.balance
            transaction.save()
        
        return Response({
            'message': 'Payment verified successfully',
            'transaction_id': transaction.id,
            'new_balance': wallet.balance
        })
    else:
        transaction.fail('Payment verification failed')
        
        return Response(
            {'error': 'Payment verification failed'},
            status=status.HTTP_400_BAD_REQUEST
        )