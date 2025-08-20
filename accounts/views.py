"""
Views for accounts app.
"""

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import User
from .serializers import UserSerializer, UserCreateSerializer


class UserListCreateView(generics.ListCreateAPIView):
    """
    List users or create a new user.
    """
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer


class UserRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    Retrieve or update user details.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """
    Login endpoint that returns auth token.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    if user:
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user': UserSerializer(user).data
        })
    
    return Response(
        {'error': 'Invalid credentials'}, 
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    """
    Logout endpoint that deletes auth token.
    """
    try:
        request.user.auth_token.delete()
        return Response({'message': 'Logged out successfully'})
    except AttributeError:
        # This can happen if the user is authenticated via session and has no token.
        return Response({'error': 'No active token to log out.'}, status=status.HTTP_400_BAD_REQUEST)