"""
Admin interface for billing models.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import Wallet, SubscriptionPlan, Subscription, Transaction, UsageLog


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ['user', 'balance_display', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['balance', 'created_at', 'updated_at']
    
    def balance_display(self, obj):
        if obj.balance >= 0:
            return format_html('<span style="color: green;">+{}</span>', obj.balance)
        return format_html('<span style="color: red;">{}</span>', obj.balance)
    balance_display.short_description = 'Balance'
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'plan_type', 'price', 'billing_period',
        'max_encounters_per_month', 'is_active'
    ]
    list_filter = ['plan_type', 'billing_period', 'is_active']
    search_fields = ['name', 'plan_type']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'plan_type', 'price', 'billing_period', 'is_active')
        }),
        ('Features', {
            'fields': (
                'max_encounters_per_month',
                'max_stt_minutes_per_month',
                'max_ai_requests_per_month',
                'includes_pdf_export',
                'includes_api_access',
                'includes_priority_support'
            )
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'status_badge', 'started_at', 'expires_at',
        'usage_summary', 'auto_renew'
    ]
    list_filter = ['status', 'plan', 'auto_renew', 'created_at']
    search_fields = ['user__username', 'user__email', 'plan__name']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'plan', 'status')
        }),
        ('Dates', {
            'fields': ('started_at', 'expires_at', 'cancelled_at')
        }),
        ('Usage', {
            'fields': ('encounters_used', 'stt_minutes_used', 'ai_requests_used')
        }),
        ('Settings', {
            'fields': ('auto_renew',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def status_badge(self, obj):
        colors = {
            'active': 'green',
            'pending': 'orange',
            'cancelled': 'red',
            'expired': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def usage_summary(self, obj):
        return format_html(
            'Encounters: {}/{}<br>STT: {}/{} min<br>AI: {}/{}',
            obj.encounters_used, obj.plan.max_encounters_per_month,
            obj.stt_minutes_used, obj.plan.max_stt_minutes_per_month,
            obj.ai_requests_used, obj.plan.max_ai_requests_per_month
        )
    usage_summary.short_description = 'Usage'
    
    actions = ['activate_subscriptions', 'cancel_subscriptions']
    
    def activate_subscriptions(self, request, queryset):
        count = 0
        for subscription in queryset.filter(status__in=['pending', 'cancelled']):
            subscription.activate()
            count += 1
        self.message_user(request, f'{count} subscriptions activated.')
    activate_subscriptions.short_description = 'Activate selected subscriptions'
    
    def cancel_subscriptions(self, request, queryset):
        count = 0
        for subscription in queryset.filter(status='active'):
            subscription.cancel()
            count += 1
        self.message_user(request, f'{count} subscriptions cancelled.')
    cancel_subscriptions.short_description = 'Cancel selected subscriptions'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        'reference_id', 'user', 'amount_display', 'transaction_type',
        'status_badge', 'created_at'
    ]
    list_filter = ['transaction_type', 'status', 'created_at']
    search_fields = ['user__username', 'user__email', 'reference_id', 'description']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        (None, {
            'fields': ('user', 'amount', 'transaction_type', 'status', 'description')
        }),
        ('Reference', {
            'fields': ('reference_id', 'subscription')
        }),
        ('Balance', {
            'fields': ('balance_before', 'balance_after')
        }),
        ('Gateway', {
            'fields': ('gateway_response',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'completed_at'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = [
        'balance_before', 'balance_after', 'created_at', 'completed_at'
    ]
    
    def amount_display(self, obj):
        if obj.amount >= 0:
            return format_html('<span style="color: green;">+{}</span>', obj.amount)
        return format_html('<span style="color: red;">{}</span>', obj.amount)
    amount_display.short_description = 'Amount'
    
    def status_badge(self, obj):
        colors = {
            'completed': 'green',
            'pending': 'orange',
            'processing': 'blue',
            'failed': 'red',
            'cancelled': 'gray'
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'
    
    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(UsageLog)
class UsageLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'feature', 'quantity', 'subscription', 'created_at']
    list_filter = ['feature', 'created_at']
    search_fields = ['user__username', 'user__email']
    date_hierarchy = 'created_at'
    
    readonly_fields = ['created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False