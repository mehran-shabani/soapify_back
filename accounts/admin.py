from django.contrib import admin
from .models import User, UserSession, PhoneVerification

class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'role', 'phone_number', 'updated_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'role')
    list_per_page = 25
    ordering = ('-updated_at',)
    readonly_fields = ('updated_at', 'date_joined')
    fieldsets = (
        (None, {
            'fields': ('username', 'email', 'first_name', 'last_name', 'password')
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Custom fields', {'fields': ('role', 'phone_number')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2'),
        }),
        ('Permissions', {
            'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Custom fields', {'fields': ('role', 'phone_number')}),
    )

class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_token', 'created_at', 'expires_at', 'is_active')
    search_fields = ('user__username', 'user__email', 'session_token')
    list_filter = ('is_active',)
    list_per_page = 25
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'expires_at')
    fieldsets = (
        (None, {'fields': ('user', 'session_token', 'created_at', 'expires_at', 'is_active')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('user', 'session_token', 'created_at', 'expires_at', 'is_active')}),
    )
    raw_id_fields = ('user',)
    list_select_related = ('user',)
    list_display_links = ('user', 'session_token')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    list_per_page = 25
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'expires_at')
    fieldsets = (
        (None, {'fields': ('user', 'session_token', 'created_at', 'expires_at', 'is_active')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('user', 'session_token', 'created_at', 'expires_at', 'is_active')}),
    )

class PhoneVerificationAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'code', 'purpose', 'is_used', 'created_at')
    search_fields = ('phone_number', 'code')
    list_filter = ('purpose', 'is_used', 'created_at')
    list_per_page = 25
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)

admin.site.register(User, UserAdmin)
admin.site.register(UserSession, UserSessionAdmin)
admin.site.register(PhoneVerification, PhoneVerificationAdmin)
