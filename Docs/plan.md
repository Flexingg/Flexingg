# Sync Service Fix Plan

## Problem Analysis

The sync service is failing to sync data from Liftosaur and Health Connect, with only partial Garmin data being retrieved. Analysis of the Celery logs and code reveals several critical issues:

### Issues Identified

1. **Missing Success Logging**: Several API calls lack proper success log statements
   - Garmin activities fetch (line 179) - no success logging
   - Garmin steps fetch - no success logging
   - Other services have logs but they're not appearing in output

2. **Silent API Failures**: Only hydration data logs are visible, indicating other API calls are failing silently
   - Garmin activities, steps, and sleep endpoints likely failing
   - Health Connect authentication issues
   - Liftosaur auth data problems

3. **Poor Error Visibility**: Exception handling catches errors but logs them at insufficient levels for Celery log visibility

## Root Cause Analysis

### Garmin Issues
- **Activities**: No success log statement makes it impossible to tell if this API call succeeds or fails
- **Steps**: Day-by-day fetching occurs but no success confirmation per day or overall
- **Sleep**: Has success logs but they're not appearing, indicating potential authentication or API issues
- **Weights**: Shows "0 weight records" indicating the API call works but returns no data

### Health Connect Issues
- **Authentication**: `client.is_authenticated()` likely returning `False`
- **Data Fetching**: `client.fetch_historical()` likely failing silently

### Liftosaur Issues
- **Auth Data**: `user_id` or `session_token` likely missing or invalid
- **Download Function**: `liftosaur_download()` likely failing

## Fix Strategy

### Phase 1: Improve Logging and Error Visibility

#### 1.1 Add Comprehensive Success Logging
- Add clear info-level logs after each successful fetch (activities, steps, hydration, sleep, weights, liftosaur, healthconnect)
- Log counts and sample identifiers to help trace what was returned

#### 1.2 Improve Error Logging Visibility
- Log critical failures at ERROR level with exception traces
- Convert some warnings to errors when a full data set cannot be fetched

#### 1.3 Add Debug Logging for Authentication Status
- Log which ConnectedService entries exist and the high-level shape of auth_data
- Log token expiry and refresh attempts/results

### Phase 2: Fix Authentication and Configuration Issues

#### 2.1 Garmin Authentication Improvements
- Validate auth_data shape before use; log missing fields
- Ensure refresh_oauth2_only returns expected structure; persist refreshed tokens
- Add explicit checks and logs around configure_garmin_client() success/failure

#### 2.2 Health Connect Authentication Fixes
- Normalize expiry parsing and ensure timezone-awareness
- Log client authentication status before attempting fetch_historical()
- Add retry and refresh flows for token expiry

#### 2.3 Liftosaur Authentication Validation
- Validate presence of `user_id` and `session_token` and log informative warnings if missing
- Catch and log exceptions inside liftosaur_download(), and surface errors to Celery logs

### Phase 3: Testing and Validation

#### 3.1 Individual Service Testing
Create small test tasks or management commands to verify each service independently:
- `test_garmin_connection(user_id)`
- `test_healthconnect_connection(user_id)`
- `test_liftosaur_connection(user_id)`

These should:
- Report authentication status
- Attempt one minimal fetch and log results
- Return machine-readable status for CI/test harnesses

#### 3.2 Sync Monitoring
- Track metrics: per-service success/failure, records fetched per sync, error types
- Add structured logs (JSON) for easier parsing

#### 3.3 Log Analysis Tools
- Add scripts or use existing log aggregation to detect:
  - Persistent authentication failures
  - Missing or zero-length responses
  - Rate-limiting or API errors

## Implementation Steps

### Step 1: Immediate Logging Improvements
- [ ] Add success logging for all Garmin API calls
- [ ] Improve error logging visibility and include exception traces
- [ ] Add authentication status logging for all services
- [ ] Run a dev sync and validate logs in Celery output

### Step 2: Authentication Fixes
- [ ] Fix Garmin token refresh handling and persist refreshed tokens
- [ ] Normalize and validate Health Connect expiry/token handling and refresh logic
- [ ] Improve Liftosaur auth validation and error reporting
- [ ] Add retries with exponential backoff for transient network/API errors

### Step 3: Testing and Monitoring
- [ ] Implement per-service test tasks/commands
- [ ] Collect metrics for syncs and create dashboards/alerts
- [ ] Add automated log parsing to detect common failures

### Step 4: Performance and Robustness
- [ ] Optimize API call batching (where supported)
- [ ] Cache successful authentication context per-run to avoid redundant refreshes
- [ ] Add circuit breaker behavior for persistently failing services
- [ ] Ensure tasks are idempotent and safe to re-run

## Success Metrics

### Before Fix
- Only hydration data visible in logs
- No Health Connect or Liftosaur data
- Unclear which services are failing

### After Fix
- All API calls logged with success/failure status
- Clear authentication status for all services
- Visible error messages for failed operations
- Complete data fetching from all configured services

## Rollback Plan
If fixes cause regressions:
1. Revert recent changes to logging first (safe to revert)
2. Revert authentication logic changes if they cause breakage
3. Restore previous version of sync service while preserving any non-breaking monitoring improvements

## Timeline Estimate
- Phase 1 (logging): 2–3 hours
- Phase 2 (auth fixes): 4–6 hours
- Phase 3 (testing & monitoring): 3–4 hours
- Total: ~9–13 hours

## Next Actions
1. Implement Phase 1 logging improvements immediately in `Flexingg/core/sync_service.py`
2. Deploy and run a dev sync; collect Celery logs
3. Use logs to target Phase 2 fixes (token refresh, expiry, error handling)
4. Implement per-service test tasks and monitoring