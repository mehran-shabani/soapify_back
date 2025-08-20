"""
Custom permissions for RBAC (Role-Based Access Control)
"""

from rest_framework import permissions


class IsDoctor(permissions.BasePermission):
    """
    Allow access only to users with doctor role
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'doctor'
        )


class IsAdmin(permissions.BasePermission):
    """
    Allow access only to users with admin role
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'admin'
        )


class IsDoctorOrAdmin(permissions.BasePermission):
    """
    Allow access to doctors or admins
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role in ['doctor', 'admin']
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Object-level permission to only allow owners or admins
    """
    
    def has_object_permission(self, request, view, obj):
        # Admin can access everything
        if request.user.role == 'admin':
            return True
        
        # Check if object has owner/user field
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'doctor'):
            return obj.doctor == request.user
        
        return False


class HasRolePermission(permissions.BasePermission):
    """
    Generic role-based permission class
    Usage: Set allowed_roles on the view
    """
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        allowed_roles = getattr(view, 'allowed_roles', [])
        return request.user.role in allowed_roles