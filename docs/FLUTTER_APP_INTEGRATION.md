# Flutter App Integration with Home Assistant mobile_app

Complete guide for integrating your EffortlessHome Flutter app with Home Assistant's mobile_app integration.

## Overview

Your Flutter app will:
1. Register with Home Assistant as a mobile device
2. Send FCM push token for notifications
3. Receive push notifications via Firebase
4. Send location updates, sensor data, etc.
5. Automatically appear as device tracker and notify service

## Prerequisites

```yaml
dependencies:
  firebase_messaging: ^14.7.0
  firebase_core: ^2.24.0
  http: ^1.2.0
  shared_preferences: ^2.2.0
```

## Complete Implementation

### 1. Firebase Setup

Configure Firebase in your Flutter app:

```dart
// main.dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

// Top-level function for background messages
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  print("Background message: ${message.messageId}");
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp();
  
  // Register background handler
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  
  runApp(MyApp());
}
```

### 2. Home Assistant Service

Create a service to handle all HA communication:

```dart
// lib/services/home_assistant_service.dart
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:device_info_plus/device_info_plus.dart';
import 'package:package_info_plus/package_info_plus.dart';

class HomeAssistantService {
  final String baseUrl;
  final String accessToken;
  
  String? _webhookId;
  
  HomeAssistantService({
    required this.baseUrl,
    required this.accessToken,
  });

  /// Register device with Home Assistant mobile_app integration
  Future<bool> registerDevice() async {
    try {
      // Get device info
      final deviceInfo = await _getDeviceInfo();
      final packageInfo = await PackageInfo.fromPlatform();
      
      // Get FCM token
      final fcmToken = await FirebaseMessaging.instance.getToken();
      
      if (fcmToken == null) {
        print('❌ Failed to get FCM token');
        return false;
      }

      final response = await http.post(
        Uri.parse('$baseUrl/api/mobile_app/registrations'),
        headers: {
          'Authorization': 'Bearer $accessToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'device_name': deviceInfo['device_name'],
          'app_id': 'io.effortlesshome.app',
          'app_name': 'EffortlessHome',
          'app_version': packageInfo.version,
          'device_id': deviceInfo['device_id'],
          'manufacturer': deviceInfo['manufacturer'],
          'model': deviceInfo['model'],
          'os_name': deviceInfo['os_name'],
          'os_version': deviceInfo['os_version'],
          'supports_encryption': false,
          'app_data': {
            'push_token': fcmToken,
            'push_url': 'https://fcm.googleapis.com',
          },
        }),
      );

      if (response.statusCode == 201) {
        final data = jsonDecode(response.body);
        _webhookId = data['webhook_id'];
        
        // Save webhook ID
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('ha_webhook_id', _webhookId!);
        
        print('✅ Registered with Home Assistant');
        print('Webhook ID: $_webhookId');
        print('Device: ${deviceInfo['device_name']}');
        
        return true;
      } else {
        print('❌ Registration failed: ${response.statusCode}');
        print('Response: ${response.body}');
        return false;
      }
    } catch (e) {
      print('❌ Registration error: $e');
      return false;
    }
  }

  /// Update push token when it changes
  Future<void> updatePushToken(String newToken) async {
    try {
      final webhookId = await _getWebhookId();
      if (webhookId == null) {
        print('⚠️ No webhook ID, need to register first');
        return;
      }

      await http.post(
        Uri.parse('$baseUrl/api/webhook/$webhookId'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'type': 'update_registration',
          'data': {
            'push_token': newToken,
          },
        }),
      );
      
      print('✅ Updated push token');
    } catch (e) {
      print('❌ Failed to update push token: $e');
    }
  }

  /// Send location update
  Future<void> updateLocation({
    required double latitude,
    required double longitude,
    required double accuracy,
    int? battery,
    double? speed,
    double? altitude,
    double? course,
  }) async {
    try {
      final webhookId = await _getWebhookId();
      if (webhookId == null) return;

      await http.post(
        Uri.parse('$baseUrl/api/webhook/$webhookId'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'type': 'update_location',
          'data': {
            'gps': [latitude, longitude],
            'gps_accuracy': accuracy,
            'battery': battery,
            'speed': speed,
            'altitude': altitude,
            'course': course,
          },
        }),
      );
      
      print('✅ Updated location: $latitude, $longitude');
    } catch (e) {
      print('❌ Failed to update location: $e');
    }
  }

  /// Send sensor updates (battery, connectivity, etc.)
  Future<void> updateSensors(Map<String, dynamic> sensors) async {
    try {
      final webhookId = await _getWebhookId();
      if (webhookId == null) return;

      final sensorData = sensors.entries.map((entry) {
        return {
          'type': 'sensor',
          'unique_id': entry.key,
          'state': entry.value['state'],
          'attributes': entry.value['attributes'] ?? {},
        };
      }).toList();

      await http.post(
        Uri.parse('$baseUrl/api/webhook/$webhookId'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'type': 'update_sensor_states',
          'data': sensorData,
        }),
      );
      
      print('✅ Updated sensors');
    } catch (e) {
      print('❌ Failed to update sensors: $e');
    }
  }

  /// Get device information
  Future<Map<String, String>> _getDeviceInfo() async {
    final deviceInfo = DeviceInfoPlugin();
    final prefs = await SharedPreferences.getInstance();
    
    // Get or create persistent device ID
    String? deviceId = prefs.getString('device_id');
    if (deviceId == null) {
      deviceId = DateTime.now().millisecondsSinceEpoch.toString();
      await prefs.setString('device_id', deviceId);
    }

    if (Platform.isAndroid) {
      final info = await deviceInfo.androidInfo;
      return {
        'device_id': deviceId,
        'device_name': '${info.brand}_${info.model}'.toLowerCase().replaceAll(' ', '_'),
        'manufacturer': info.manufacturer,
        'model': info.model,
        'os_name': 'Android',
        'os_version': info.version.release,
      };
    } else if (Platform.isIOS) {
      final info = await deviceInfo.iosInfo;
      return {
        'device_id': deviceId,
        'device_name': '${info.name}'.toLowerCase().replaceAll(' ', '_'),
        'manufacturer': 'Apple',
        'model': info.model,
        'os_name': 'iOS',
        'os_version': info.systemVersion,
      };
    }
    
    return {
      'device_id': deviceId,
      'device_name': 'unknown_device',
      'manufacturer': 'Unknown',
      'model': 'Unknown',
      'os_name': 'Unknown',
      'os_version': 'Unknown',
    };
  }

  /// Get saved webhook ID
  Future<String?> _getWebhookId() async {
    if (_webhookId != null) return _webhookId;
    
    final prefs = await SharedPreferences.getInstance();
    _webhookId = prefs.getString('ha_webhook_id');
    return _webhookId;
  }
}
```

### 3. Notification Handler

Handle incoming notifications:

```dart
// lib/services/notification_service.dart
import 'package:firebase_messaging/firebase_messaging.dart';

class NotificationService {
  final FirebaseMessaging _messaging = FirebaseMessaging.instance;

  Future<void> initialize() async {
    // Request permissions (iOS)
    await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    // Get initial token
    final token = await _messaging.getToken();
    print('FCM Token: $token');

    // Listen for token refresh
    FirebaseMessaging.instance.onTokenRefresh.listen((newToken) {
      print('FCM Token refreshed: $newToken');
      // Update HA with new token
      _updateToken(newToken);
    });

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // Handle background tap
    FirebaseMessaging.onMessageOpenedApp.listen(_handleBackgroundTap);

    // Check if app was opened from terminated state
    final initialMessage = await _messaging.getInitialMessage();
    if (initialMessage != null) {
      _handleBackgroundTap(initialMessage);
    }
  }

  void _handleForegroundMessage(RemoteMessage message) {
    print('📱 Foreground notification received');
    print('Title: ${message.notification?.title}');
    print('Body: ${message.notification?.body}');
    print('Data: ${message.data}');

    // Show in-app notification or update UI
    _showLocalNotification(message);
  }

  void _handleBackgroundTap(RemoteMessage message) {
    print('📱 App opened from notification');
    print('Data: ${message.data}');

    // Navigate based on notification data
    if (message.data.containsKey('action')) {
      _handleNotificationAction(message.data);
    }
  }

  void _handleNotificationAction(Map<String, dynamic> data) {
    final action = data['action'];
    
    switch (action) {
      case 'open_camera':
        final cameraId = data['camera_id'];
        // Navigate to camera view
        break;
      case 'open_alarm':
        // Navigate to alarm panel
        break;
      default:
        // Default action
        break;
    }
  }

  void _showLocalNotification(RemoteMessage message) {
    // Use flutter_local_notifications or similar
    // to show notification while app is in foreground
  }

  void _updateToken(String newToken) async {
    // Get HA service and update token
    // final haService = getIt<HomeAssistantService>();
    // await haService.updatePushToken(newToken);
  }
}
```

### 4. App Initialization

Put it all together in your app:

```dart
// lib/main.dart
class _MyAppState extends State<MyApp> {
  late HomeAssistantService _haService;
  late NotificationService _notificationService;

  @override
  void initState() {
    super.initState();
    _initialize();
  }

  Future<void> _initialize() async {
    // Initialize Home Assistant service
    _haService = HomeAssistantService(
      baseUrl: 'https://your-ha-instance.com',
      accessToken: 'YOUR_LONG_LIVED_ACCESS_TOKEN',
    );

    // Initialize notifications
    _notificationService = NotificationService();
    await _notificationService.initialize();

    // Register with Home Assistant
    final registered = await _haService.registerDevice();
    
    if (registered) {
      // Setup periodic location updates
      _startLocationUpdates();
      
      // Setup battery monitoring
      _startBatteryUpdates();
    }
  }

  void _startLocationUpdates() {
    // Use location package to get periodic updates
    // Then call _haService.updateLocation()
  }

  void _startBatteryUpdates() {
    // Use battery_plus package
    // Then call _haService.updateSensors()
  }
}
```

## Testing

### 1. Test Registration

```dart
// Test button in your UI
ElevatedButton(
  onPressed: () async {
    final success = await _haService.registerDevice();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(success ? 'Registered!' : 'Failed')),
    );
  },
  child: Text('Register Device'),
)
```

### 2. Test Notification

From Home Assistant Developer Tools → Services:

```yaml
service: notify.mobile_app_[your_device_name]
data:
  message: "Test from Home Assistant"
  title: "Hello"
  data:
    action: "test"
```

### 3. Check Device Tracker

Go to Developer Tools → States and search for `device_tracker.[your_device_name]`

## Production Checklist

- [ ] Firebase project configured
- [ ] Long-lived access token generated in HA
- [ ] Device name is unique and lowercase with underscores
- [ ] Notification permissions requested and granted
- [ ] Device registered successfully (check HA logs)
- [ ] Device tracker appears in HA
- [ ] Notify service appears in HA Services
- [ ] Test notification received
- [ ] Token refresh handler implemented
- [ ] Location updates working
- [ ] Proper error handling implemented
- [ ] Tokens stored securely (not hardcoded)

## Common Issues

**"Registration failed: 401"**
- Check that access token is valid
- Ensure token has necessary permissions

**"No notify service created"**
- Check that `push_token` was included in registration
- Verify Firebase is properly configured in HA
- Check HA logs for errors

**"Notifications not received"**
- Verify FCM token is valid
- Check Firebase console for delivery status
- Ensure notification permissions granted
- Test with Firebase Console → Cloud Messaging

**"Device tracker not updating"**
- Call `updateLocation()` method
- Check that webhook ID is saved
- Verify location permissions granted

## Resources

- [Home Assistant mobile_app API](https://developers.home-assistant.io/docs/api/native-app-integration/)
- [Firebase Messaging Setup](https://firebase.google.com/docs/flutter/setup)
- [device_info_plus](https://pub.dev/packages/device_info_plus)
- [package_info_plus](https://pub.dev/packages/package_info_plus)
