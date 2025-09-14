# Health Connect Integration Gameplan

## Overview
This plan outlines integrating Google's Health Connect data into the Flexingg Django application using the HCGateway API (Docker service at http://localhost:6644). The goal is to allow users to connect their HCGateway account, fetch all available Health Connect data types (e.g., steps, heartRate, activeCaloriesBurned, etc.), and store raw records in the Django database linked to their UserProfile. No gamification (e.g., mapping to currencies/XP) is implemented yet – focus on ingestion and storage. Future phases can add utilization.

Key Benefits:
- Centralized fitness data alongside Garmin/Liftosaur.
- Enables future features like cross-integration analytics, rewards.
- Uses API for secure, structured access (no direct MongoDB).

Assumptions:
- HCGateway Docker is running (ports 6644 for API, 27017 for Mongo).
- Users have HCGateway accounts via Android app.
- All data types fetched via /fetch/{method} endpoints.
- Tokens expire in 12h; auto-refresh on sync.

## Architecture
- **New Django App**: `healthconnect` – Contains models, views, tasks, urls, utils (API client).
- **Dependencies**: Add `requests` (or `httpx`) to requirements.txt for API calls. Use Celery for periodic syncs (already in project).
- **Models** (in healthconnect/models.py):
  - Extend UserProfile (core/models.py): Add fields for connection: `hc_username` (CharField), `hc_password` (encrypted, use django-fernet-fields or hash), `hc_token` (TextField), `hc_refresh` (TextField), `hc_expiry` (DateTimeField).
  - `HealthConnectData` (abstract base or generic): `profile` (FK to UserProfile), `method` (CharField, e.g., 'steps'), `record_id` (CharField from _id), `start_time` (DateTime), `end_time` (DateTime, null=True), `data` (JSONField for raw data object), `app_source` (CharField), `fetched_at` (DateTime).
    - Use a single generic model for flexibility (all methods in one table); subclass if needed later for queries.
- **API Client** (healthconnect/utils.py): Class `HCGatewayClient` with methods: `login(username, password)` -> get token/refresh/expiry; `refresh_token(refresh)`; `fetch(method, query=None)` -> POST to /fetch/{method} with bearer auth; `revoke()` -> POST to /revoke; `fetch_all_methods()` -> loop over all methods, fetch recent/historical.
- **Views/Tasks**:
  - Views: Connect (POST credentials -> login, store tokens), Sync (fetch recent), Disconnect (revoke, clear fields).
  - Celery Task: `sync_healthconnect_data` – For each connected profile, refresh token if expired, fetch last 24h for all methods, store records.
- **Integration with Existing**: Update `integrations_section` component to include HC status/checks, similar to Garmin/Liftosaur.

## Data Flow
1. User clicks "CONNECT" in integrations UI -> Modal for HCGateway username/password.
2. POST to connect view -> Client.login() -> Store tokens/expiry in Profile -> Fetch historical data (all methods, no query filter initially; handle pagination if large).
3. Store each record in HealthConnectData (dedupe by record_id/method/profile).
4. On "SYNC" button or daily Celery: Fetch recent data (query: {"start": {"$gte": yesterday ISO}}).
5. "DISCONNECT": Client.revoke() -> Clear Profile fields.
6. Data accessible via admin or future views (e.g., /health-data/ for user).

```mermaid
flowchart TD
    A[User Clicks CONNECT] --> B[Modal: Username/Password]
    B --> C[POST /healthconnect/connect/]
    C --> D[Client.login() -> Tokens]
    D --> E[Store in UserProfile]
    E --> F[Fetch All Methods Historical]
    F --> G[Store Raw Data in HealthConnectData]
    H[Daily Celery or SYNC Button] --> I[Refresh Token if Expired]
    I --> J[Fetch Recent 24h All Methods]
    J --> K[Store/Update Records]
    L[DISCONNECT] --> M[Client.revoke()]
    M --> N[Clear Profile Fields]
```

## Implementation Steps
1. Create healthconnect app: `python manage.py startapp healthconnect`.
2. Add to INSTALLED_APPS in settings.py.
3. Define models, migrate (add to Profile via migration).
4. Implement API client.
5. Add views/urls for connect/sync/disconnect.
6. Celery task in healthconnect/tasks.py, add to celerybeat-schedule.
7. Update integrations_section: Add hc_connected check (expiry > now), modal template, JS handlers (similar to Garmin).
8. UI: Replace APK download with connect logic; add SYNC/DISCONNECT buttons if connected.
9. Testing: Mock API or use local Docker; verify data storage.

## Potential Challenges & Mitigations
- Large Historical Data: Fetch in batches (e.g., by date range); start with last 90 days.
- Token Management: Auto-refresh in client; fallback to re-login if fails.
- Data Volume: JSONField ok for now; index on profile/method/start_time; aggregates later.
- Security: Encrypt password (use django-encrypted-fields); never log credentials.
- Errors: Handle API failures (e.g., invalid creds) with user messages.

This plan keeps scope focused on ingestion. Once approved, we can refine and implement in code mode.

Line count: 85 (including diagram).