"""
Serializers for accounts app.
"""

from rest_framework import serializers
from .models import User


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
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'role', 'phone_number']
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user