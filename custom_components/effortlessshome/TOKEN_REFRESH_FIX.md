# Firebase Token Refresh Fix

## Problem

The EffortlessHome integration was experiencing 401 authentication errors when Firebase tokens expired. This caused various API calls to fail, including:

- Alarm creation and management
- Firebase configuration retrieval
- Notification services
- Event creation
- Alert creation

## Root Cause

Firebase ID tokens have a limited lifespan (typically 1 hour) and need to be refreshed periodically. The integration was not automatically handling token expiration, causing API calls to fail with 401 errors when tokens expired.

## Solution

### 1. Enhanced Token Error Detection

Updated `_is_firebase_token_error()` function in `alarm_common.py` to detect more authentication error patterns:

```python
def _is_firebase_token_error(err: Exception) -> bool:
    """Check if the error is related to Firebase token expiration or invalidation."""
    msg = str(err).lower()
    status = getattr(err, "status", None) or getattr(err, "status_code", None)

    # Check for HTTP 401 status
    if status == 401:
        return True

    # Check for explicit Firebase token errors
    if "firebase token" in msg and ("expired" in msg or "invalid" in msg):
        return True

    # Check for generic 401 with token mention
    if "status 401" in msg and "token" in msg:
        return True

    # Check for common Firebase auth error patterns
    if any(pattern in msg for pattern in [
        "unauthorized",
        "invalid authentication",
        "token has expired",
        "invalid token",
        "authentication failed"
    ]):
        return True

    return False
```

### 2. Automatic Token Refresh Helper

Created `auth_helper.py` with robust token refresh functionality:

- **`with_token_refresh` decorator**: Automatically wraps API calls with token refresh logic
- **`safe_api_call` function**: Alternative approach for manual token refresh handling
- **Enhanced error detection**: More comprehensive patterns for detecting authentication failures
- **Automatic retry**: Failed API calls are automatically retried with refreshed tokens

### 3. Background Token Refresh

The integration already had a background token refresh task that runs every 50 minutes (tokens expire in 60 minutes), but the automatic retry mechanism ensures that even if the background refresh fails, individual API calls can still recover.

## Files Modified

1. **`alarm_common.py`**: Enhanced token error detection
2. **`auth_helper.py`**: New authentication helper with automatic refresh
3. **`person.py`**: Updated imports to use new auth helper
4. **`__init__.py`**: Updated imports to use new auth helper

## How It Works

1. **API Call**: When an API call is made using `OasiraAPIClient`
2. **Error Detection**: If a 401 error occurs, the system checks if it's a token-related error
3. **Token Refresh**: If it's a token error, the system automatically refreshes the Firebase ID token
4. **Retry**: The original API call is retried with the new token
5. **Success/Failure**: If successful, the call proceeds normally. If it fails again, the error is raised

## Benefits

- **Automatic Recovery**: No manual intervention required when tokens expire
- **Improved Reliability**: API calls are more resilient to authentication failures
- **Better User Experience**: Fewer failed operations due to expired tokens
- **Backward Compatibility**: Existing code continues to work without changes

## Testing

To test the fix:

1. **Monitor Logs**: Check for "Firebase token error detected, attempting refresh" messages
2. **Force Token Expiration**: Wait for tokens to expire naturally (after 1 hour)
3. **API Operations**: Perform operations that trigger API calls (create alarms, send notifications)
4. **Verify Recovery**: Confirm that operations succeed even after token expiration

## Monitoring

The system logs various events for monitoring:

- `✅ Firebase ID token refreshed successfully` - Background refresh success
- `Firebase token error detected, attempting refresh` - Automatic retry triggered
- `Token refreshed, retrying API call...` - Retry in progress
- `Failed to refresh Firebase token` - Refresh failure

## Future Improvements

- Consider implementing exponential backoff for failed refresh attempts
- Add metrics for token refresh success/failure rates
- Implement token refresh caching to avoid multiple simultaneous refreshes
- Consider using shorter refresh intervals for more proactive token management