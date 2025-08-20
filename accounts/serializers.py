"""
Serializers for accounts app.
"""

from rest_framework import serializers
from .models import User, PhoneVerification


class UserSerializer(serializers.ModelSerializer):
    """
    User serializer for API responses.
    """
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'role', 'phone_number', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class UserCreateSerializer(serializers.ModelSerializer):
    """
    User creation serializer.
    """
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role', 'phone_number']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class PhoneLoginSerializer(serializers.Serializer):
    """Phone number for login/registration"""
    phone_number = serializers.CharField(max_length=15)


class VerifyCodeSerializer(serializers.Serializer):
    """Verify phone with 6-digit code"""
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=6)


class LoginSerializer(serializers.Serializer):
    """Login with username/password"""
    username = serializers.CharField()
    password = serializers.CharField()


class RegisterSerializer(serializers.Serializer):
    """Register with phone verification"""
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=6)
    username = serializers.CharField()
    password = serializers.CharField(min_length=8)
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)
    role = serializers.ChoiceField(choices=['doctor', 'admin'], default='doctor')


class ResetPasswordSerializer(serializers.Serializer):
    """Reset password with phone verification"""
    phone_number = serializers.CharField(max_length=15)
    code = serializers.CharField(max_length=6, min_length=6)
    new_password = serializers.CharField(min_length=8)