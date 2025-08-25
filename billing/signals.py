"""
Signals for billing app - automatic wallet creation and transaction handling.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from decimal import Decimal
from .models import Wallet, Transaction, Subscription

User = get_user_model()

# Initial bonus amount for new users
INITIAL_BONUS_AMOUNT = Decimal('500.00')  # 500 تومان هدیه اولیه


@receiver(post_save, sender=User)
def create_user_wallet(sender, instance, created, **kwargs):
    """
    Create wallet for new users with initial bonus.
    """
    if created:
        wallet = Wallet.objects.create(user=instance)
        
        # Add initial bonus
        if INITIAL_BONUS_AMOUNT > 0:
            wallet.add_credit(
                amount=INITIAL_BONUS_AMOUNT,
                description="Welcome bonus for new user"
            )


@receiver(post_save, sender=Transaction)
def update_wallet_after_transaction(sender, instance, created, **kwargs):
    """
    Update wallet balance after successful transaction.
    This is for external payment gateway transactions.
    """
    if not created:
        # Only process on update, not on create
        if instance.status == 'completed' and instance.transaction_type in ['credit', 'refund']:
            # Transaction just became successful
            try:
                wallet = instance.user.wallet
            except Wallet.DoesNotExist:
                wallet = Wallet.objects.create(user=instance.user)
            
            # Update wallet balance
            # Note: This is different from wallet.add_credit() to avoid circular transaction creation
            wallet.balance += abs(instance.amount)
            wallet.save()
            
            # Update transaction balance tracking
            instance.balance_after = wallet.balance
            instance.save(update_fields=['balance_after'])


@receiver(post_save, sender=Subscription)
def handle_subscription_activation(sender, instance, created, **kwargs):
    """
    Handle subscription activation - deduct from wallet if needed.
    """
    if not created and instance.status == 'active' and not instance.started_at:
        # Subscription just activated
        try:
            wallet = instance.user.wallet
            
            # Deduct subscription fee from wallet
            if wallet.has_sufficient_balance(instance.plan.price):
                transaction = wallet.deduct(
                    amount=instance.plan.price,
                    description=f"Subscription payment for {instance.plan.name}"
                )
                
                # Link transaction to subscription
                transaction.subscription = instance
                transaction.transaction_type = 'subscription'
                transaction.save()
                
                # Activate the subscription
                instance.activate()
            else:
                # Insufficient balance - mark subscription as pending
                instance.status = 'pending'
                instance.save()
                
        except Wallet.DoesNotExist:
            # Create wallet if it doesn't exist
            Wallet.objects.create(user=instance.user)