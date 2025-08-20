
## Test Coverage Report

- Last total coverage (from latest run): **34.30%**.

### High-impact files to target for new tests
- accounts
  - `accounts/authentication.py` (58%)
  - `accounts/permissions.py` (30%)
  - `accounts/views.py` (48%)

- adminplus
  - `adminplus/services.py` (14%)
  - `adminplus/views.py` (0%)

- analytics
  - `analytics/services.py` (21%)
  - `analytics/views.py` (20%)

- checklist
  - `checklist/services.py` (16%)
  - `checklist/views.py` (0%)

- embeddings
  - `embeddings/services.py` (21%)
  - `embeddings/tasks.py` (0%)

- encounters
  - `encounters/views.py` (22%)

- integrations
  - `integrations/clients/gpt_client.py` (18%)
  - `integrations/services/jwt_window_service.py` (15%)
  - `integrations/views.py` (0%)

- nlp
  - `nlp/services/extraction_service.py` (12%)
  - `nlp/views.py` (6%)

- outputs
  - `outputs/services/finalization_service.py` (17%)
  - `outputs/services/pdf_service.py` (21%)
  - `outputs/services/template_service.py` (26%)
  - `outputs/services/patient_linking_service.py` (19%)
  - `outputs/tasks.py` (17%)
  - `outputs/views.py` (11%)

- search
  - `search/services.py` (10%)

- stt
  - `stt/services/whisper_service.py` (14%)
  - `stt/tasks.py` (38%)
  - `stt/views.py` (24%)

- infra
  - `infra/utils.py` (0%)
  - `infra/middleware/hmac_auth.py` (21%)
  - `infra/middleware/security.py` (29%)

### Notes
- Multiple test failures are due to missing or incomplete API view endpoints (e.g., STT, NLP, Outputs, Integrations). Implementing minimal happy-path and error-path handlers will both reduce failures and raise coverage.
- Prioritize service-layer unit tests with mocks for external APIs (OpenAI, S3, HTTP) and Celery task tests (eager execution is already enabled in test settings).
- Focus initially on modules under ~30% to quickly lift overall coverage toward the 90% threshold enforced by `pytest.ini`.


