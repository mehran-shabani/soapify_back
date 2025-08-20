# Authentication API Documentation

## Overview

The authentication system uses JWT tokens with mobile phone verification. 
- **Access Token**: Valid for 2 days
- **Refresh Token**: Valid for 10 days
- **Verification Code**: Valid for 15 minutes

## Endpoints

### 1. Send Verification Code
**Endpoint**: `POST /api/auth/send-code/`  
**Authentication**: Not required  
**Description**: Send a 6-digit verification code to the specified phone number.

**Request Body**:
```json
{
    "phone_number": "+1234567890",
    "purpose": "login"  // Options: "login", "register", "reset_password"
}
```

**Response**:
```json
{
    "message": "Verification code sent successfully",
    "phone_number": "+1234567890"
}
```

### 2. Register
**Endpoint**: `POST /api/auth/register/`  
**Authentication**: Not required  
**Description**: Register a new user with phone verification.

**Request Body**:
```json
{
    "phone_number": "+1234567890",
    "code": "123456",
    "username": "johndoe",
    "password": "securepassword123",
    "email": "john@example.com",  // optional
    "first_name": "John",  // optional
    "last_name": "Doe",  // optional
    "role": "doctor"  // Options: "doctor", "admin"
}
```

**Response** (201 Created):
```json
{
    "message": "User registered successfully",
    "user": {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "doctor",
        "phone_number": "+1234567890",
        "updated_at": "2024-01-01T12:00:00Z"
    }
}
```

### 3. Login with Username/Password
**Endpoint**: `POST /api/auth/login/`  
**Authentication**: Not required  
**Description**: Login with username and password.

**Request Body**:
```json
{
    "username": "johndoe",
    "password": "securepassword123"
}
```

**Response** (201 Created):
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "user": {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "doctor",
        "phone_number": "+1234567890",
        "updated_at": "2024-01-01T12:00:00Z"
    }
}
```

### 4. Login with Phone Number
**Endpoint**: `POST /api/auth/login-phone/`  
**Authentication**: Not required  
**Description**: Login with phone number and verification code.

**Request Body**:
```json
{
    "phone_number": "+1234567890",
    "code": "123456"
}
```

**Response** (201 Created):
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer",
    "user": {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "doctor",
        "phone_number": "+1234567890",
        "updated_at": "2024-01-01T12:00:00Z"
    }
}
```

### 5. Refresh Token
**Endpoint**: `POST /api/auth/refresh/`  
**Authentication**: Not required  
**Description**: Refresh access token using refresh token. Requires username and password for additional security.

**Request Body**:
```json
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "username": "johndoe",
    "password": "securepassword123"
}
```

**Response**:
```json
{
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "Bearer"
}
```

### 6. Reset Password
**Endpoint**: `POST /api/auth/reset-password/`  
**Authentication**: Not required  
**Description**: Reset password using phone verification.

**Request Body**:
```json
{
    "phone_number": "+1234567890",
    "code": "123456",
    "new_password": "newsecurepassword123"
}
```

**Response**:
```json
{
    "message": "Password reset successfully"
}
```

### 7. Get Current User
**Endpoint**: `GET /api/auth/current-user/`  
**Authentication**: Required (Bearer Token)  
**Description**: Get current authenticated user information.

**Headers**:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Response**:
```json
{
    "user": {
        "id": 1,
        "username": "johndoe",
        "email": "john@example.com",
        "first_name": "John",
        "last_name": "Doe",
        "role": "doctor",
        "phone_number": "+1234567890",
        "updated_at": "2024-01-01T12:00:00Z"
    }
}
```

### 8. Logout
**Endpoint**: `POST /api/auth/logout/`  
**Authentication**: Required (Bearer Token)  
**Description**: Logout user by blacklisting the refresh token.

**Headers**:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

**Request Body** (optional):
```json
{
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response**:
```json
{
    "message": "Logged out successfully"
}
```

## Using JWT Tokens

After successful login, include the access token in the Authorization header for all protected endpoints:

```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Error Responses

### 400 Bad Request
```json
{
    "error": "Username and password are required"
}
```

### 401 Unauthorized
```json
{
    "error": "Invalid credentials"
}
```

### 404 Not Found
```json
{
    "error": "User not found with this phone number"
}
```

## Phone Number Format

Phone numbers should be in international format with country code:
- US: +1234567890
- Iran: +989123456789
- UK: +447123456789