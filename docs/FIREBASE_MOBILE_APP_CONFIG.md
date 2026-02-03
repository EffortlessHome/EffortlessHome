# Firebase Mobile App Configuration

## Overview

EffortlessHome now automatically configures the built-in Home Assistant `mobile_app` integration using Firebase credentials loaded from the Oasira service. This eliminates the need to manually configure FCM (Firebase Cloud Messaging) credentials in your `configuration.yaml`.

## Automatic Configuration

When EffortlessHome starts up, it automatically:

1. **Fetches Firebase configuration** from your Oasira account
2. **Configures the mobile_app integration** with FCM credentials
3. **Sets up webhooks** for mobile app communication

No manual configuration is required!

## Manual Configuration (Optional)

If you prefer to manually configure or want to see the equivalent `configuration.yaml` entries, you can use the service:

### Using the Service

1. Go to **Developer Tools** → **Services**
2. Select service: `effortlesshome.get_firebase_config`
3. Click **Call Service**
4. A persistent notification will appear with your Firebase configuration

The notification will show you the equivalent `configuration.yaml` that would be needed for manual setup:

```yaml
mobile_app:
  # For FCM Legacy API
  fcm_sender_id: "YOUR_SENDER_ID"
  firebase:
    server_key: "YOUR_SERVER_KEY"
```

## What This Enables

With Firebase configured, your custom mobile app can:

- ✅ Receive push notifications from Home Assistant
- ✅ Update device location via the mobile_app integration
- ✅ Use all standard mobile_app features (sensors, notifications, etc.)
- ✅ Work seamlessly with EffortlessHome's notification system

## Technical Details

### How It Works

1. **Oasira API Call**: The integration calls `get_firebase_config()` on the Oasira API
2. **Firebase Credentials**: Returns FCM sender ID, server key, API key, and project ID
3. **Configuration**: Programmatically configures Home Assistant's mobile_app integration
4. **Webhook Setup**: Creates webhooks for mobile device communication

### Code Location

- **Mobile App Config Module**: `custom_components/effortlesshome/mobile_app_config.py`
- **Integration Setup**: `custom_components/effortlesshome/__init__.py`
- **Service Definition**: `custom_components/effortlesshome/services.yaml`

### API Methods Used

From `oasira.api_client`:
```python
async def get_firebase_config(self) -> Dict[str, Any]:
    """Get Firebase configuration from Oasira."""
```

Returns configuration with keys like:
- `messagingSenderId` / `fcm_sender_id` / `sender_id`
- `serverKey` / `server_key`
- `apiKey` / `api_key`
- `projectId` / `project_id`
- `appId` / `app_id`

## Troubleshooting

### Check if Configuration Loaded

Look for this in your Home Assistant logs:
```
[custom_components.effortlesshome] Mobile app integration configured from Oasira Firebase config
[custom_components.effortlesshome.mobile_app_config] ✅ Mobile app integration setup complete
```

### View Current Configuration

Call the service `effortlesshome.get_firebase_config` to see your current Firebase configuration.

### Common Issues

**Issue**: "Failed to configure mobile app integration from Oasira"
- **Solution**: Check that your Oasira account has Firebase configuration set up
- **Solution**: Verify your system_id and id_token are valid

**Issue**: No Firebase config fields
- **Solution**: The Oasira API may not have Firebase credentials for your account
- **Solution**: Contact support to have Firebase credentials added

## Benefits Over Manual Configuration

✅ **No manual editing** of configuration.yaml
✅ **Automatic updates** if Firebase credentials change
✅ **Centralized management** through Oasira
✅ **No credential exposure** in config files
✅ **Easier deployment** across multiple systems

## Related Components

- **Notify Firebase**: `notify_firebase.py` - Custom Firebase notification service
- **Mobile App Config**: `mobile_app_config.py` - Firebase configuration helper
- **Oasira API Client**: External package providing Firebase config API

## See Also

- [Home Assistant Mobile App Documentation](https://companion.home-assistant.io/)
- [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)
- [EffortlessHome Notifications Guide](./docs/notifications_quick_start.md)
