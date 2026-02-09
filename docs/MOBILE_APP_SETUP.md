# EffortlessHome Flutter App Push Notifications Setup

EffortlessHome uses Home Assistant's **mobile_app integration** for push notifications. Your custom Flutter app registers with Home Assistant just like the official Companion App, creating automatic notify services and device trackers.

## How It Works

1. Your Flutter app **registers with mobile_app integration** 
2. Home Assistant creates `notify.mobile_app_[device_name]` service automatically
3. Home Assistant creates device tracker for location tracking
4. EffortlessHome's `notify.effortlesshome` service discovers and uses these services
5. **No configuration.yaml changes needed!**

## Flutter App Implementation

### 1. Install Required Packages

```yaml
dependencies:
  firebase_messaging: ^14.0.0
  http: ^1.0.0
```

### 2. Register Device with mobile_app Integration

When your app starts, register with Home Assistant:

```dart
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

Future<void> registerWithHomeAssistant(
  String haUrl,
  String accessToken,
) async {
  // Get FCM token
  final fcmToken = await FirebaseMessaging.instance.getToken();
  
  // Register device with mobile_app integration
  final response = await http.post(
    Uri.parse('$haUrl/api/mobile_app/registrations'),
    headers: {
      'Authorization': 'Bearer $accessToken',
      'Content-Type': 'application/json',
    },
    body: jsonEncode({
      'device_name': 'johns_iphone', // Unique, lowercase, underscores
      'app_id': 'io.effortlesshome.app',
      'app_name': 'EffortlessHome',
      'app_version': '1.0.0',
      'device_id': 'unique-device-id', // Persistent device identifier
      'manufacturer': 'Apple',
      'model': 'iPhone 14',
      'os_name': 'iOS',
      'os_version': '17.0',
      'supports_encryption': false,
      'app_data': {
        'push_token': fcmToken,
      },
    }),
  );

  if (response.statusCode == 201) {
    final data = jsonDecode(response.body);
    final webhookId = data['webhook_id'];
    
    // Save webhook_id for future updates
    await saveWebhookId(webhookId);
    
    print('✅ Registered with Home Assistant');
    print('Webhook ID: $webhookId');
  } else {
    print('❌ Registration failed: ${response.body}');
  }
}
```

### 3. Update Push Token When It Changes

```dart
Future<void> updatePushToken(
  String haUrl,
  String webhookId,
  String newToken,
) async {
  await http.post(
    Uri.parse('$haUrl/api/webhook/$webhookId'),
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({
      'type': 'update_registration',
      'data': {
        'push_token': newToken,
      },
    }),
  );
}

// Listen for token changes
FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
  updatePushToken(haUrl, webhookId, newToken);
});
```

### 4. Handle Incoming Notifications

```dart
// Foreground notifications
FirebaseMessaging.onMessage.listen((RemoteMessage message) {
  print('Notification: ${message.notification?.title}');
  print('Data: ${message.data}');
  
  // Show notification UI
  showNotification(
    title: message.notification?.title ?? 'EffortlessHome',
    body: message.notification?.body ?? '',
    data: message.data,
  );
});

// Background/terminated notifications
FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
  print('App opened from notification');
  handleNotificationAction(message.data);
});
```

### 5. Link Device to Person Entity

After registration, link the device tracker to a person:

1. Go to **Settings** → **People** in Home Assistant
2. Select the person
3. Add the device tracker (e.g., `device_tracker.johns_iphone`)

## Using Notifications

### Send to Person

```yaml
service: notify.effortlesshome
data:
  target:
    - person.john_doe
  message: "Motion detected at front door"
  title: "Security Alert"
  data:
    action: "open_camera"
    camera_id: "camera.front_door"
```

### Send to Specific Device

```yaml
service: notify.mobile_app_johns_iphone
data:
  message: "Test notification"
  title: "Hello"
  data:
    action: "URI"
    uri: "/lovelace/cameras"
```

## Troubleshooting

### Notifications Not Received

**Possible causes**:

1. **Device not registered**: Check that your Flutter app successfully registered with mobile_app
   - Look for `device_tracker.[device_name]` in Developer Tools → States
   - Look for `notify.mobile_app_[device_name]` in Developer Tools → Services

2. **Device not linked to person**: Go to Settings → People and link the device tracker to the person

3. **FCM token not sent**: Ensure `push_token` is included in the registration payload

4. **Firebase not configured**: Check Home Assistant logs for Firebase-related errors

5. **Notification permissions**: Verify the Flutter app has notification permissions granted

### Check Registered Devices

View all mobile_app registrations:

```yaml
service: mobile_app.list_devices
```

Or check for device tracker entities in **Developer Tools** → **States**:
- Filter by `device_tracker.`
- Look for devices with `platform: mobile_app`

### Check Notify Services

After registration, you should see:
- `notify.mobile_app_johns_iphone` (or your device name) in **Developer Tools** → **Services**

If missing:
1. Check Home Assistant logs for registration errors
2. Verify your Flutter app sent the correct registration payload
3. Restart Home Assistant to force service discovery

### Debug Registration

Check if device is registered by calling the webhook directly:

```dart
// Send test update
await http.post(
  Uri.parse('$haUrl/api/webhook/$webhookId'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'type': 'update_registration',
    'data': {
      'push_token': 'test-token',
    },
  }),
);
```

Check Home Assistant logs for webhook activity.

### Re-register Device

If needed, you can re-register by:
1. Generating a new unique `device_id`
2. Calling the registration endpoint again with new credentials

## Architecture

```
EffortlessHome Flutter App
    ↓ (registers via mobile_app API)
Home Assistant mobile_app Integration
    ↓ (creates notify service & device tracker)
notify.mobile_app_johns_iphone
    ↓ (linked to person entity)
notify.effortlesshome
    ↓ (discovers mobile_app services)
Firebase Cloud Messaging
    ↓ (delivers notification)
EffortlessHome Flutter App
```

## Advanced Features

### Custom Notification Actions

```yaml
service: notify.mobile_app_johns_iphone
data:
  message: "Motion detected"
  title: "Front Door"
  data:
    # Action buttons
    actions:
      - action: "VIEW_CAMERA"
        title: "View Camera"
      - action: "DISMISS"
        title: "Dismiss"
    # Custom data for your app
    camera_id: "camera.front_door"
    zone: "front_yard"
```

### Location Updates

Your Flutter app can send location updates:

```dart
await http.post(
  Uri.parse('$haUrl/api/webhook/$webhookId'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'type': 'update_location',
    'data': {
      'gps': [latitude, longitude],
      'gps_accuracy': accuracy,
      'battery': batteryLevel,
      'speed': speed,
      'altitude': altitude,
      'course': course,
    },
  }),
);
```

### Sensor Updates

Report battery, connectivity, etc.:

```dart
await http.post(
  Uri.parse('$haUrl/api/webhook/$webhookId'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({
    'type': 'update_sensor_states',
    'data': [
      {
        'type': 'sensor',
        'unique_id': 'battery_level',
        'state': 85,
        'attributes': {
          'unit_of_measurement': '%',
          'device_class': 'battery',
        },
      },
    ],
  }),
);
```

## Support

If you continue to experience issues:

1. **Check Home Assistant logs**: Settings → System → Logs
2. **Search for**: "mobile_app", "registration", or your device name
3. **Verify registration payload**: Ensure all required fields are present
4. **Test with Postman/curl**: Register manually to isolate Flutter app issues
5. **Check Firebase console**: Verify FCM tokens are valid

## Additional Resources

- [Home Assistant mobile_app Integration](https://www.home-assistant.io/integrations/mobile_app/)
- [Native App Integration Docs](https://developers.home-assistant.io/docs/api/native-app-integration/)
- [Firebase Cloud Messaging](https://firebase.google.com/docs/cloud-messaging)
- [Flutter Firebase Messaging Plugin](https://pub.dev/packages/firebase_messaging)
