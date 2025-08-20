# SOAPify API Documentation

This document provides comprehensive documentation for the SOAPify REST API.

## Base URL

```bash
Production: https://api.soapify.com
Development: http://localhost:8000/api
```

## Authentication

SOAPify uses JWT (JSON Web Tokens) for API authentication.

### Obtain Access Token

**Endpoint:** `POST /api/auth/token/`

**Request:**
```json
{
    "username": "your_username",
    "password": "your_password"
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Refresh Token

**Endpoint:** `POST /api/auth/token/refresh/`

**Request:**
```json
{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Verify Token

**Endpoint:** `POST /api/auth/token/verify/`

**Request:**
```json
{
    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Login/Logout

**Endpoint:** `POST /api/auth/login/`
**Request:**
```json
{
    "username": "your_username",
    "password": "your_password"
}
```

**Endpoint:** `POST /api/auth/logout/`

### Using the Token

Include the access token in the Authorization header:
```bash
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...
```

## Error Handling

### HTTP Status Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

### Error Response Format

```json
{
    "error": "Error message",
    "details": "Additional error details",
    "code": "ERROR_CODE"
}
```

## API Endpoints

### 1. Users Management

#### List/Create Users
- **Endpoint:** `GET/POST /api/users/`
- **Query:** `page` (for pagination)

#### Get/Update User
- **Endpoint:** `GET/PUT/PATCH /api/users/{id}/`

### 2. Encounters API

#### Create Encounter
**Endpoint:** `POST /api/encounters/create/`

**Request:**
```json
{
    "patient_ref": "patient-001"
}
```

#### List Encounters
**Endpoint:** `GET /api/encounters/`

#### Get Encounter Details
**Endpoint:** `GET /api/encounters/{encounter_id}/`

### 3. Audio Management

#### Get Pre-signed URL for Upload
**Endpoint:** `POST /api/audio/presigned-url/`

**Request:**
```json
{
    "filename": "audio_chunk_1.wav",
    "content_type": "audio/wav"
}
```

#### Commit Audio File
**Endpoint:** `POST /api/audio/commit/`

**Request:**
```json
{
    "s3_key": "uploads/audio_chunk_1.wav",
    "etag": "abc123def456",
    "sha256_hash": "hash_value",
    "idempotency_key": "unique_key"
}
```

### 4. STT (Speech to Text) API

#### Transcribe Audio Chunk
**Endpoint:** `POST /api/stt/transcribe/`

**Request:**
```json
{
    "chunk_id": 123
}
```

#### Process Encounter STT
**Endpoint:** `POST /api/stt/encounter/{encounter_id}/process/`

#### Get Transcript
**Endpoint:** `GET /api/stt/transcript/{audio_chunk_id}/`

#### Get Encounter Transcript
**Endpoint:** `GET /api/stt/encounter/{encounter_id}/transcript/`

#### Update Transcript Segment
**Endpoint:** `PUT /api/stt/transcript/{segment_id}/`

#### Search Transcript
**Endpoint:** `GET /api/stt/search/`
**Query:** `q` (search query)

### 5. NLP API

#### Generate SOAP Draft
**Endpoint:** `POST /api/nlp/generate/{encounter_id}/`

#### Get SOAP Draft
**Endpoint:** `GET /api/nlp/drafts/{encounter_id}/`

#### Update SOAP Section
**Endpoint:** `PUT /api/nlp/drafts/{encounter_id}/update-section/`

**Request:**
```json
{
    "section": "assessment",
    "content": "Updated assessment content"
}
```

#### Get Dynamic Checklist
**Endpoint:** `GET /api/nlp/drafts/{encounter_id}/checklist/`

#### Update Checklist Item
**Endpoint:** `PUT /api/nlp/drafts/{encounter_id}/checklist/{item_id}/`

### 6. Checklist API

#### Catalog Management
- **List/Create:** `GET/POST /api/checklist/catalog/`
- **Get/Update/Delete:** `GET/PUT/PATCH/DELETE /api/checklist/catalog/{id}/`

**Catalog Item Schema:**
```json
{
    "title": "Chief Complaint",
    "description": "Document patient's primary concern",
    "category": "subjective",
    "priority": "high",
    "keywords": {"synonyms": ["complaint", "concern"]},
    "question_template": "What is the patient's chief complaint?",
    "is_active": true
}
```

#### Template Management
- **List/Create:** `GET/POST /api/checklist/templates/`
- **Get/Update/Delete:** `GET/PUT/PATCH/DELETE /api/checklist/templates/{id}/`
- **Get Related Items:** `GET /api/checklist/templates/{id}/catalog_items/`

#### Evaluations
- **List/Create:** `GET/POST /api/checklist/evaluations/`
- **Get/Update/Delete:** `GET/PUT/PATCH/DELETE /api/checklist/evaluations/{id}/`
- **Evaluate Encounter:** `POST /api/checklist/evaluations/evaluate_encounter/`
- **Get Summary:** `GET /api/checklist/evaluations/summary/?encounter_id={id}`

### 7. Search API

#### Hybrid Search
**Endpoint:** `GET /api/search/`

**Query Parameters:**
- `q` (required) - Search query
- `encounter_id` - Filter by encounter
- `content_type` - Filter by type (transcript|soap|checklist|notes)
- `date_from`, `date_to` - Date range (YYYY-MM-DD)
- `page`, `page_size` - Pagination

#### Search Suggestions
**Endpoint:** `GET /api/search/suggestions/`

**Query:** `q`, `limit` (default: 10)

#### Search Analytics
**Endpoint:** `GET /api/search/analytics/`

**Query:** `days` (default: 30)

#### Reindex Content
**Endpoint:** `POST /api/search/reindex/`

**Request:**
```json
{
    "encounter_id": "123"
}
```

### 8. Analytics API

#### System Overview
**Endpoint:** `GET /api/analytics/overview/`

#### Performance Analytics
**Endpoint:** `GET /api/analytics/performance/`
**Query:** `days` (default: 7)

#### User Analytics
**Endpoint:** `GET /api/analytics/users/`
**Query:** `user_id`, `days` (default: 30)

#### Alerts
- **List Active:** `GET /api/analytics/alerts/`
- **Check Rules:** `POST /api/analytics/alerts/check/`
- **Acknowledge:** `POST /api/analytics/alerts/{alert_id}/acknowledge/`

#### Metrics
**Endpoint:** `POST /api/analytics/metric/`

**Request:**
```json
{
    "name": "queue_depth",
    "value": 42,
    "metric_type": "gauge",
    "tags": {"queue": "stt"}
}
```

#### Activity Tracking
**Endpoint:** `POST /api/analytics/activity/`

**Request:**
```json
{
    "action": "view_encounter",
    "resource": "encounter",
    "resource_id": "123",
    "metadata": {}
}
```

#### Business Metrics
**Endpoint:** `POST /api/analytics/business-metrics/`

**Request:**
```json
{
    "date_from": "2024-01-01",
    "date_to": "2024-01-31"
}
```

### 9. Integrations API

#### Health Check
**Endpoint:** `GET /api/integrations/health/`

#### OTP Management
- **Send OTP:** `POST /api/integrations/otp/send/`
- **Verify OTP:** `POST /api/integrations/otp/verify/`

#### Session Management
- **Get Status:** `GET /api/integrations/session/status/`
- **Extend Session:** `POST /api/integrations/session/extend/`
- **Logout:** `POST /api/integrations/logout/`

#### Helssa Patients (Read-only)
- **Search:** `GET /api/integrations/patients/search/?q={query}`
- **Get Info:** `GET /api/integrations/patients/{patient_ref}/info/`
- **Request Access:** `POST /api/integrations/patients/{patient_ref}/access/`

### 10. Outputs API

#### Finalize SOAP Note
**Endpoint:** `POST /api/outputs/finalize/`

**Request:**
```json
{
    "encounter_id": 123,
    "export_formats": ["pdf", "markdown"],
    "send_sms": true,
    "recipient_phone": "+1234567890"
}
```

#### Get Finalized SOAP
**Endpoint:** `GET /api/outputs/finalized/{encounter_id}/`

#### List Output Files
**Endpoint:** `GET /api/outputs/files/{encounter_id}/`

#### Generate Download URL
**Endpoint:** `POST /api/outputs/download/{file_id}/`

#### Create Patient Link
**Endpoint:** `POST /api/outputs/link-patient/`

**Request:**
```json
{
    "encounter_id": 123,
    "expires_in_days": 7
}
```

#### Access Patient SOAP (Public)
**Endpoint:** `GET /api/outputs/access/{link_id}/`

### 11. Uploads API

#### Session-based Upload
- **Create Session:** `POST /api/uploads/session/create/`
- **Upload Chunk:** `POST /api/uploads/chunk/` (multipart/form-data)
- **Commit Session:** `POST /api/uploads/commit/`
- **Get Final:** `GET /api/uploads/final/{session_id}/`

#### S3 Direct Upload
- **Get Pre-sign URL:** `POST /api/uploads/s3/presign/`
- **Confirm Upload:** `POST /api/uploads/s3/confirm/`

### 12. AdminPlus API

#### Dashboard & Monitoring
- **Dashboard:** `GET /adminplus/`
- **System Health:** `GET /adminplus/api/health/`
- **Task Monitor:** `GET /adminplus/api/tasks/`
- **Task Stats:** `GET /adminplus/api/tasks/stats/`

#### Task Management
- **Retry Task:** `POST /adminplus/api/tasks/retry/`
- **Cancel Task:** `POST /adminplus/api/tasks/cancel/`

#### Logs & Export
- **Operation Logs:** `GET /adminplus/api/logs/`
- **Export Data:** `POST /adminplus/api/export/`

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Authentication endpoints:** 10 requests per minute
- **General API endpoints:** 60 requests per minute
- **Upload endpoints:** 20 requests per minute

## Pagination

List endpoints support pagination with the following parameters:

- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

Response includes:
```json
{
    "count": 150,
    "next": "http://api.soapify.com/endpoint?page=2",
    "previous": null,
    "results": [...]
}
```

## Webhooks

SOAPify can send webhooks for the following events:

- `encounter.created`
- `transcription.completed`
- `soap.generated`
- `soap.finalized`
- `patient.link.created`

## SDK & Client Libraries

Official SDKs are available for:

- Python: `pip install soapify-sdk`
- JavaScript/Node.js: `npm install @soapify/sdk`
- PHP: `composer require soapify/sdk`

## Support

For API support and questions:
- Email: api-support@soapify.com
- Documentation: https://docs.soapify.com
- Status Page: https://status.soapify.com

## Changelog

### v1.0.0 (Current)
- Initial API release
- Full SOAP note generation pipeline
- Checklist evaluation system
- Hybrid search functionality
- Analytics and monitoring
- External integrations (Helssa, SMS)