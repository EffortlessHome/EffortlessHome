# EffortlessHome Direct App Notifications Integration

**Date**: February 1, 2026  
**Version**: 2.0 (Redesigned)  
**Status**: ✅ Complete

## Overview

The EffortlessHome notifications system has been completely redesigned to provide direct integration between Home Assistant and the EffortlessHome Flutter app. Notifications are now:

1. **Sent directly to the app** - Not through mobile app notify services
2. **Stored in app** - Appear in the alerts/notifications section
3. **Shown as native notifications** - When the device supports it
4. **Real-time** - Instant delivery to registered app instances
5. **Device-aware** - Supports different platforms (Android, iOS, Windows, Web, etc.)

## Architecture

### Components

```
Home Assistant Automation
         ↓
effortlesshome.send_notification Service
         ↓
AppNotificationManager (Python)
         ↓
    ┌────┴────┐
    ↓         ↓
 Firebase   Webhook
  (FCM)      (Push)
    ↓         ↓
Flutter App (AppNotificationService)
    ↓
┌───┴──────┬──────────┐
↓          ↓          ↓
Cache   Display   Native Notification
```

### Python Side (Home Assistant)

**File**: `custom_components/effortlesshome/notify_service.py`

- **AppNotificationManager**: Manages notifications and app instances
- **Webhook Handler**: Receives registration/requests from app
- **Services**:
  - `effortlesshome.send_notification` - Send notification
  - `effortlesshome.register_app_instance` - App registration

### Flutter Side

**Files**:
- `lib/services/app_notification_service.dart` - Notification client
- `lib/providers/app_state.dart` - Integration with app state

**Features**:
- Auto-registers with Home Assistant on connect
- Listens for incoming notifications
- Stores notifications locally
- Shows native notifications
- Manages notification lifecycle

## Usage

### Send Notifications from Home Assistant

#### From Automations

```yaml
automation:
  - alias: "Motion Alert to App"
    trigger:
      platform: state
      entity_id: binary_sensor.motion_sensor
      to: "on"
    action:
      service: effortlesshome.send_notification
      data:
        title: "Motion Detected"
        message: "Motion detected in the living room"
        category: security
        image_url: /api/camera_proxy/camera.front_door
```

#### From Scripts

```yaml
script:
  notify_door_status:
    sequence:
      - service: effortlesshome.send_notification
        data:
          title: "🚪 Door Status"
          message: "Front door was {{ trigger.to_state.state }}"
          category: access
```

#### From Python

```python
async def handle_event(hass: HomeAssistant, event):
    """Send notification on event."""
    await hass.services.async_call(
        "effortlesshome",
        "send_notification",
        {
            "title": "Event Triggered",
            "message": f"Event: {event.data}",
            "category": "system",
        }
    )
```

### Service Reference

#### effortlesshome.send_notification

```yaml
service: effortlesshome.send_notification
data:
  title: string              # Required: Notification title
  message: string            # Required: Notification message
  category: string           # Optional: security, system, automation, access
  target: string             # Optional: Target person (for future use)
  data: object              # Optional: Custom data
  image_url: string         # Optional: Image URL
```

**Example**:
```yaml
service: effortlesshome.send_notification
data:
  title: "⚠️ High Temperature"
  message: "Temperature is {{ states('sensor.temperature') }}°C"
  category: system
  image_url: /local/icons/temperature.png
```

## How It Works

### 1. App Registration

When the app connects to Home Assistant:

1. Generates unique app instance ID
2. Calls webhook: `POST /api/webhook/effortlesshome_app_notify`
3. Sends device info (platform, device name, etc.)
4. Receives confirmation
5. Stored in Home Assistant memory

**Python**:
```python
await notification_manager.register_app_instance(
    app_id="app_1234567890",
    device_info={"platform": "android", "device_name": "Pixel 6"},
    fcm_token="..."  # Optional Firebase token
)
```

**Flutter**:
```dart
await appNotificationService.registerAppInstance(
  deviceName: "My Phone",
  platform: "android",
);
```

### 2. Sending Notifications

When a notification is sent from Home Assistant:

1. Service called with title, message, category
2. Unique notification ID generated
3. Stored in manager's notification cache
4. Dispatched to all registered app instances
5. Delivered via Firebase FCM or webhook push

**Python Flow**:
```python
notification_id = await notification_manager.send_notification(
    title="Alert",
    message="Something happened",
    category="security"
)
# Automatically sent to all registered apps
```

### 3. Receiving in App

When the app receives a notification:

1. Webhook POST received with notification data
2. Parsed as AppNotification object
3. Added to notification cache
4. Emitted via notification stream
5. AppState listens and:
   - Adds to notifications list
   - Shows native notification
   - Refreshes UI

**Flutter Flow**:
```dart
_appNotificationService.onNotificationReceived.listen((notification) {
  // Add to state
  _notifications.insert(0, notification);
  notifyListeners();
  
  // Show native notification
  _notificationHandler.showNotification(
    title: notification.title,
    body: notification.message,
  );
});
```

### 4. Displaying in UI

Notifications appear in:

1. **Alerts/Notifications Screen** - Full list with categories
2. **Badge** - Unread count
3. **Native Notification** - OS notification drawer
4. **Status Indicator** - In header/AppBar

## Notification Categories

Supported categories for organizing notifications:

- **security** - Alarm, motion, door/window sensors
- **system** - App status, warnings, errors
- **automation** - Automation execution, triggers
- **access** - Door locks, entry points

```yaml
service: effortlesshome.send_notification
data:
  title: "Alarm Triggered"
  message: "Front door sensor activated"
  category: security  # Shows with security icon/color
```

## Features

### Notification Management

```dart
// Get cached notifications
final notifications = await appNotificationService.getNotifications(
  limit: 50,
  category: 'security',
);

// Clear specific notification
await appNotificationService.clearNotification(notificationId);

// Clear all notifications
await appNotificationService.clearAllNotifications();
```

### Auto-Refresh Integration

Notifications are automatically refreshed every 30 seconds when:
- App is in foreground
- Connected to Home Assistant
- Auto-refresh enabled (default)

### Native Notifications

Supported on:
- ✅ **Android** - Android notifications with custom sounds/vibration
- ✅ **iOS** - iOS local notifications with badges
- ✅ **Windows** - Windows toast notifications
- ✅ **macOS** - macOS notifications
- ✅ **Linux** - Linux notifications
- ✅ **Web** - Browser notifications (limited)

## Integration Examples

### Temperature Monitor

```yaml
automation:
  - alias: "High Temperature Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.home_temperature
      above: 28
    action:
      service: effortlesshome.send_notification
      data:
        title: "🌡️ High Temperature"
        message: "Temperature {{ states('sensor.home_temperature') }}°C"
        category: system
```

### Security Alert

```yaml
automation:
  - alias: "Security Alert"
    trigger:
      platform: state
      entity_id:
        - binary_sensor.front_door
        - binary_sensor.back_door
      to: "on"
    action:
      service: effortlesshome.send_notification
      data:
        title: "🔐 Door Alert"
        message: "{{ trigger.to_state.attributes.friendly_name }} opened"
        category: security
        image_url: /api/camera_proxy/camera.front_door
```

### Automation Notification

```yaml
automation:
  - alias: "Lights On Notification"
    trigger:
      platform: state
      entity_id: light.living_room
      to: "on"
    action:
      - service: effortlesshome.send_notification
        data:
          title: "💡 Lights On"
          message: "Living room lights turned on"
          category: automation
```

### Smart Home Status

```yaml
automation:
  - alias: "Home Status Alert"
    trigger:
      platform: state
      entity_id: alarm_control_panel.home
      to: "armed_away"
    action:
      service: effortlesshome.send_notification
      data:
        title: "🏠 Home Status"
        message: "Home security system armed away"
        category: system
```

## Notification Flow Diagram

```
User Action (Door Open, etc.)
         ↓
Home Assistant Automation Triggered
         ↓
effortlesshome.send_notification Called
         ↓
AppNotificationManager Creates Notification
├─ Generates ID
├─ Sets timestamp
├─ Stores in cache
└─ Dispatches to Apps
         ↓
App Instance 1: Sends via FCM/Webhook
App Instance 2: Sends via FCM/Webhook
         ↓
Flutter App Receives
├─ Parses notification
├─ Stores in local cache
├─ Adds to notification list
├─ Emits stream event
└─ AppState updates
         ↓
UI Updates
├─ Adds to notifications screen
├─ Shows native notification
├─ Updates badge count
└─ Refreshes display
```

## Advanced Usage

### Custom Notification Data

```yaml
service: effortlesshome.send_notification
data:
  title: "Alert"
  message: "Something happened"
  category: system
  data:
    custom_field: "custom_value"
    action_url: "/dashboard"
```

### Multiple Targets (Future)

```yaml
service: effortlesshome.send_notification
data:
  title: "Family Alert"
  message: "Important message"
  target:
    - person.john
    - person.jane
```

### Conditional Notifications

```yaml
automation:
  - alias: "Conditional Alert"
    trigger:
      platform: template
      value_template: "{{ states('sensor.battery') | int < 10 }}"
    action:
      service: effortlesshome.send_notification
      data:
        title: "🔋 Low Battery"
        message: "Battery level: {{ states('sensor.battery') }}%"
        category: system
```

## Troubleshooting

### Notifications Not Appearing

1. **Check App Registration**
   - Ensure app is connected to Home Assistant
   - Check logs for registration confirmation
   - Verify webhook is registered

2. **Check Notification Service**
   - Verify service is registered: Developer Tools → Services
   - Look for `effortlesshome.send_notification`
   - Check Home Assistant logs for errors

3. **Check Device Support**
   - Ensure device supports native notifications
   - Check notification permissions
   - Verify device is online

### Notification Delays

- **Cause**: Network latency or FCM delays
- **Solution**: Use direct webhook for faster delivery
- **Note**: Typical delay is < 1 second

### Missing Images

- **Cause**: Invalid image URLs or CORS issues
- **Solution**: Use absolute URLs or /api/camera_proxy/
- **Note**: Images are optional

## Future Enhancements

Planned improvements:

- [ ] Notification actions (dismiss, snooze, reply)
- [ ] Notification channels (Android)
- [ ] Notification sounds/vibrations
- [ ] Scheduled notifications
- [ ] Notification templates
- [ ] Multi-user notifications
- [ ] Notification groups by area/topic
- [ ] Web UI for notification management
- [ ] Notification history export
- [ ] Analytics and delivery reports

## Configuration

### Home Assistant

No special configuration needed. Service is automatically available after integration loads.

### Flutter App

Notifications are configured automatically when app connects:
- Auto-registers as app instance
- Listens for incoming notifications
- Shows in alerts section by default

## Performance Considerations

- **Notification Caching**: Notifications stored in memory (up to ~1000)
- **Auto-Refresh**: 30-second interval, paused when app backgrounded
- **Native Notifications**: One per notification
- **Memory Impact**: Minimal (~1KB per notification)

## Security

- **Authentication**: Uses Home Assistant auth token
- **Encryption**: HTTPS for all network calls
- **App Registration**: Each app gets unique instance ID
- **Data Isolation**: Notifications only sent to registered apps
- **Token Handling**: Tokens stored securely in Flutter app

## Related Documentation

- [Home Assistant Automation](https://www.home-assistant.io/docs/automation/)
- [Service Calls](https://www.home-assistant.io/docs/scripts/service-calls/)
- [Templating](https://www.home-assistant.io/docs/configuration/templating/)
- [Flutter Local Notifications](https://pub.dev/packages/flutter_local_notifications)
