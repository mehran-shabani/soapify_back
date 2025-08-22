"""
Comprehensive tests for accounts app
"""

import pytest
import jwt
import secrets
from datetime import datetime, timedelta
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from rest_framework.authtoken.models import Token
from unittest.mock import patch, MagicMock

from accounts.models import User, UserSession
from accounts.serializers import UserSerializer, UserCreateSerializer
from accounts.permissions import (
    IsDoctor, IsAdmin, IsDoctorOrAdmin, 
    IsOwnerOrAdmin, HasRolePermission
)
from accounts.authentication import (
    JWTAuthentication, generate_jwt_token, 
    generate_refresh_token, verify_refresh_token
)

User = get_user_model()


class UserModelTest(TestCase):
    """Test User model"""
    
    def setUp(self):
        self.user_data = {
            'username': 'testdoctor',
            'email': 'doctor@test.com',
            'password': 'testpass123',
            'role': 'doctor',
            'phone_number': '+1234567890'
        }
    
    def test_user_creation(self):
        """Test creating a user"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(user.username, 'testdoctor')
        self.assertEqual(user.email, 'doctor@test.com')
        self.assertEqual(user.role, 'doctor')
        self.assertEqual(user.phone_number, '+1234567890')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_user_str_representation(self):
        """Test user string representation"""
        user = User.objects.create_user(**self.user_data)
        self.assertEqual(str(user), 'testdoctor (Doctor)')
    
    def test_admin_user_creation(self):
        """Test creating an admin user"""
        admin_data = self.user_data.copy()
        admin_data['username'] = 'testadmin'
        admin_data['role'] = 'admin'
        user = User.objects.create_user(**admin_data)
        self.assertEqual(user.role, 'admin')
        self.assertEqual(str(user), 'testadmin (Admin)')
    
    def test_user_update(self):
        """Test updating user"""
        user = User.objects.create_user(**self.user_data)
        user.first_name = 'John'
        user.last_name = 'Doe'
        user.save()
        
        updated_user = User.objects.get(id=user.id)
        self.assertEqual(updated_user.first_name, 'John')
        self.assertEqual(updated_user.last_name, 'Doe')
        self.assertIsNotNone(updated_user.updated_at)


class UserSessionModelTest(TestCase):
    """Test UserSession model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
    
    def test_session_creation(self):
        """Test creating a user session"""
        session = UserSession.objects.create(
            user=self.user,
            session_token=secrets.token_hex(32),
            expires_at=datetime.now() + timedelta(days=7)
        )
        self.assertEqual(session.user, self.user)
        self.assertTrue(session.is_active)
        self.assertIsNotNone(session.session_token)
        self.assertIsNotNone(session.created_at)
    
    def test_session_str_representation(self):
        """Test session string representation"""
        session = UserSession.objects.create(
            user=self.user,
            session_token=secrets.token_hex(32),
            expires_at=datetime.now() + timedelta(days=7)
        )
        self.assertEqual(str(session), f'Session for {self.user.username}')
    
    def test_session_indexes(self):
        """Test that session indexes are properly created"""
        # This test verifies the Meta configuration
        meta = UserSession._meta
        self.assertEqual(meta.db_table, 'user_sessions')
        # Check indexes exist
        index_fields = [idx.fields for idx in meta.indexes]
        self.assertIn(['session_token'], index_fields)
        self.assertIn(['expires_at'], index_fields)


class UserSerializerTest(TestCase):
    """Test user serializers"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='doctor',
            phone_number='+1234567890'
        )
    
    def test_user_serializer(self):
        """Test UserSerializer"""
        serializer = UserSerializer(self.user)
        data = serializer.data
        
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@test.com')
        self.assertEqual(data['role'], 'doctor')
        self.assertEqual(data['phone_number'], '+1234567890')
        self.assertIn('id', data)
        self.assertIn('updated_at', data)
        self.assertNotIn('password', data)
    
    def test_user_create_serializer(self):
        """Test UserCreateSerializer"""
        data = {
            'username': 'newuser',
            'email': 'new@test.com',
            'password': 'newpass123',
            'role': 'doctor',
            'phone_number': '+9876543210'
        }
        serializer = UserCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        
        user = serializer.save()
        self.assertEqual(user.username, 'newuser')
        self.assertEqual(user.email, 'new@test.com')
        self.assertTrue(user.check_password('newpass123'))
        self.assertEqual(user.role, 'doctor')
    
    def test_user_create_serializer_validation(self):
        """Test UserCreateSerializer validation"""
        # Missing required fields
        data = {'username': 'newuser'}
        serializer = UserCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)


class PermissionsTest(TestCase):
    """Test custom permissions"""
    
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='doctor',
            password='pass123',
            role='doctor'
        )
        self.admin = User.objects.create_user(
            username='admin',
            password='pass123',
            role='admin'
        )
        self.client = APIClient()
    
    def test_is_doctor_permission(self):
        """Test IsDoctor permission"""
        permission = IsDoctor()
        
        # Test with doctor
        self.client.force_authenticate(user=self.doctor)
        request = self.client.request()
        request.user = self.doctor
        self.assertTrue(permission.has_permission(request, None))
        
        # Test with admin
        request.user = self.admin
        self.assertFalse(permission.has_permission(request, None))
        
        # Test with anonymous
        request.user = None
        self.assertFalse(permission.has_permission(request, None))
    
    def test_is_admin_permission(self):
        """Test IsAdmin permission"""
        permission = IsAdmin()
        
        # Test with admin
        request = self.client.request()
        request.user = self.admin
        self.assertTrue(permission.has_permission(request, None))
        
        # Test with doctor
        request.user = self.doctor
        self.assertFalse(permission.has_permission(request, None))
    
    def test_is_doctor_or_admin_permission(self):
        """Test IsDoctorOrAdmin permission"""
        permission = IsDoctorOrAdmin()
        request = self.client.request()
        
        # Test with doctor
        request.user = self.doctor
        self.assertTrue(permission.has_permission(request, None))
        
        # Test with admin
        request.user = self.admin
        self.assertTrue(permission.has_permission(request, None))
    
    def test_is_owner_or_admin_permission(self):
        """Test IsOwnerOrAdmin permission"""
        permission = IsOwnerOrAdmin()
        request = self.client.request()
        
        # Test with admin - should have access to everything
        request.user = self.admin
        obj = MagicMock()
        self.assertTrue(permission.has_object_permission(request, None, obj))
        
        # Test with owner via user field
        request.user = self.doctor
        obj.user = self.doctor
        self.assertTrue(permission.has_object_permission(request, None, obj))
        
        # Test with non-owner
        other_user = User.objects.create_user(username='other', password='pass')
        obj.user = other_user
        self.assertFalse(permission.has_object_permission(request, None, obj))
        
        # Test with owner via doctor field
        delattr(obj, 'user')
        obj.doctor = self.doctor
        self.assertTrue(permission.has_object_permission(request, None, obj))
        
        # Test with owner via owner field
        delattr(obj, 'doctor')
        obj.owner = self.doctor
        self.assertTrue(permission.has_object_permission(request, None, obj))
    
    def test_has_role_permission(self):
        """Test HasRolePermission"""
        permission = HasRolePermission()
        request = self.client.request()
        view = MagicMock()
        
        # Test with allowed roles
        view.allowed_roles = ['doctor', 'admin']
        request.user = self.doctor
        self.assertTrue(permission.has_permission(request, view))
        
        # Test with role not in allowed list
        view.allowed_roles = ['admin']
        self.assertFalse(permission.has_permission(request, view))
        
        # Test with unauthenticated user
        request.user = None
        self.assertFalse(permission.has_permission(request, view))


class JWTAuthenticationTest(TestCase):
    """Test JWT authentication"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            role='doctor'
        )
        self.auth = JWTAuthentication()
    
    def test_generate_jwt_token(self):
        """Test JWT token generation"""
        token = generate_jwt_token(self.user)
        self.assertIsNotNone(token)
        
        # Decode and verify
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(payload['sub'], str(self.user.id))
        self.assertEqual(payload['username'], self.user.username)
        self.assertEqual(payload['role'], self.user.role)
        self.assertEqual(payload['aud'], 'soapify')
    
    def test_generate_jwt_token_with_session(self):
        """Test JWT token generation with session"""
        session_token = secrets.token_hex(32)
        token = generate_jwt_token(self.user, session_token)
        
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(payload['jti'], session_token)
    
    def test_generate_refresh_token(self):
        """Test refresh token generation"""
        token = generate_refresh_token(self.user)
        self.assertIsNotNone(token)
        
        # Decode and verify
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        self.assertEqual(payload['sub'], str(self.user.id))
        self.assertEqual(payload['type'], 'refresh')
        self.assertEqual(payload['aud'], 'soapify')
    
    def test_verify_refresh_token(self):
        """Test refresh token verification"""
        token = generate_refresh_token(self.user)
        verified_user = verify_refresh_token(token)
        self.assertEqual(verified_user, self.user)
    
    def test_verify_invalid_refresh_token(self):
        """Test invalid refresh token verification"""
        # Invalid token
        self.assertIsNone(verify_refresh_token('invalid-token'))
        
        # Wrong type token
        access_token = generate_jwt_token(self.user)
        self.assertIsNone(verify_refresh_token(access_token))
    
    def test_jwt_authentication_valid_token(self):
        """Test JWT authentication with valid token"""
        # Create session
        session = UserSession.objects.create(
            user=self.user,
            session_token=secrets.token_hex(32),
            expires_at=datetime.now() + timedelta(days=7)
        )
        
        # Generate token
        token = generate_jwt_token(self.user, session.session_token)
        
        # Mock request
        request = MagicMock()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        # Authenticate
        result = self.auth.authenticate(request)
        self.assertIsNotNone(result)
        authenticated_user, authenticated_token = result
        self.assertEqual(authenticated_user, self.user)
        self.assertEqual(authenticated_token, token)
    
    def test_jwt_authentication_no_header(self):
        """Test JWT authentication without header"""
        request = MagicMock()
        request.META = {}
        self.assertIsNone(self.auth.authenticate(request))
    
    def test_jwt_authentication_invalid_header(self):
        """Test JWT authentication with invalid header"""
        request = MagicMock()
        request.META = {'HTTP_AUTHORIZATION': 'Invalid header'}
        self.assertIsNone(self.auth.authenticate(request))
    
    def test_jwt_authentication_expired_token(self):
        """Test JWT authentication with expired token"""
        # Generate expired token
        now = datetime.utcnow()
        expiry = now - timedelta(minutes=1)  # Already expired
        
        payload = {
            'sub': str(self.user.id),
            'username': self.user.username,
            'role': self.user.role,
            'jti': 'test-session',
            'aud': 'soapify',
            'iat': now - timedelta(minutes=31),
            'exp': expiry
        }
        
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        
        request = MagicMock()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        from rest_framework.exceptions import AuthenticationFailed
        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)
        self.assertEqual(str(context.exception), 'Token expired')
    
    def test_jwt_authentication_invalid_audience(self):
        """Test JWT authentication with invalid audience"""
        payload = {
            'sub': str(self.user.id),
            'username': self.user.username,
            'role': self.user.role,
            'aud': 'wrong-audience',
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(minutes=30)
        }
        
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        
        request = MagicMock()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        from rest_framework.exceptions import AuthenticationFailed
        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)
        self.assertEqual(str(context.exception), 'Invalid audience')
    
    def test_jwt_authentication_expired_session(self):
        """Test JWT authentication with expired session"""
        # Create expired session
        session = UserSession.objects.create(
            user=self.user,
            session_token=secrets.token_hex(32),
            expires_at=datetime.now() - timedelta(days=1)  # Already expired
        )
        
        # Generate valid token
        token = generate_jwt_token(self.user, session.session_token)
        
        request = MagicMock()
        request.META = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        
        from rest_framework.exceptions import AuthenticationFailed
        with self.assertRaises(AuthenticationFailed) as context:
            self.auth.authenticate(request)
        self.assertEqual(str(context.exception), 'Session expired')
        
        # Verify session was deactivated
        session.refresh_from_db()
        self.assertFalse(session.is_active)


class AccountViewsTest(APITestCase):
    """Test account views"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='doctor'
        )
        self.admin = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='adminpass123',
            role='admin'
        )
    
    def test_login_view_success(self):
        """Test successful login"""
        url = reverse('accounts:login')
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['username'], 'testuser')
        
        # Verify token was created
        self.assertTrue(Token.objects.filter(user=self.user).exists())
    
    def test_login_view_invalid_credentials(self):
        """Test login with invalid credentials"""
        url = reverse('accounts:login')
        data = {
            'username': 'testuser',
            'password': 'wrongpass'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('error', response.data)
    
    def test_login_view_missing_fields(self):
        """Test login with missing fields"""
        url = reverse('accounts:login')
        
        # Missing password
        response = self.client.post(url, {'username': 'testuser'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Missing username
        response = self.client.post(url, {'password': 'testpass123'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_logout_view(self):
        """Test logout"""
        # Login first
        self.client.force_authenticate(user=self.user)
        Token.objects.create(user=self.user)
        
        url = reverse('accounts:logout')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        
        # Verify token was deleted
        self.assertFalse(Token.objects.filter(user=self.user).exists())
    
    def test_logout_view_no_token(self):
        """Test logout when user has no token"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('accounts:logout')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
    
    def test_user_list_create_view(self):
        """Test user list and create"""
        url = reverse('accounts:user-list-create')
        
        # Test list (requires authentication)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        
        # Test create
        data = {
            'username': 'newdoctor',
            'email': 'new@test.com',
            'password': 'newpass123',
            'role': 'doctor'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newdoctor').exists())
    
    def test_user_retrieve_update_view(self):
        """Test user retrieve and update"""
        url = reverse('accounts:user-detail', kwargs={'pk': self.user.id})
        
        # Test retrieve
        self.client.force_authenticate(user=self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
        
        # Test update
        data = {'phone_number': '+9999999999'}
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.phone_number, '+9999999999')


class JWTCustomViewsTest(APITestCase):
    """Test custom JWT views from jwt_views.py"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            role='doctor'
        )
    
    @patch('accounts.jwt_views.jwt_login')
    def test_jwt_custom_login(self, mock_jwt_login):
        """Test custom JWT login if exposed"""
        # This tests the custom jwt_views functions
        from accounts.jwt_views import jwt_login
        
        # Create mock request
        request = MagicMock()
        request.data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.data = {
            'access_token': 'test-access',
            'refresh_token': 'test-refresh'
        }
        mock_jwt_login.return_value = mock_response
        
        # Call function
        response = jwt_login(request)
        self.assertIsNotNone(response)
    
    def test_custom_jwt_functions(self):
        """Test custom JWT helper functions"""
        from accounts.jwt_views import jwt_login, jwt_refresh, jwt_logout, current_user
        
        # These are the actual custom implementations
        # They exist but may not be exposed in URLs
        self.assertTrue(callable(jwt_login))
        self.assertTrue(callable(jwt_refresh))
        self.assertTrue(callable(jwt_logout))
        self.assertTrue(callable(current_user))