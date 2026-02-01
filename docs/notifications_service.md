# EffortlessHome Notifications Service

The EffortlessHome integration provides a custom notifications service that allows you to send notifications from automations, scripts, and other services to users' mobile devices and notify entities.

## Overview

The `effortlesshome.notify` service integrates with Home Assistant's notify infrastructure and supports:

- Sending notifications to person entities (via their mobile app devices)
- Sending notifications to specific devices registered in EffortlessHome
- Forwarding notifications to any Home Assistant notify service
- Support for notification data like images, tags, and groups
- Template support for dynamic message content

## Service Usage

### Basic Service Call

```yaml
service: effortlesshome.notify
data:
  message: "This is a test notification"
  title: "Test Alert"
  target: person.john_doe
```

### Advanced Service Call with Data

```yaml
service: effortlesshome.notify
data:
  message: "Motion detected in the living room"
  title: "Security Alert"
  target:
    - person.john_doe
    - notify.mobile_app_kitchen_tablet
  data:
    image: "/local/motion_snapshot.jpg"
    tag: "motion_alert"
    group: "security"
```

## Service Fields

### Required Fields

- **message**: The notification message body (string)
  - Example: `"System alert from EffortlessHome"`

### Optional Fields

- **title**: The notification title (string, default: "EffortlessHome Notification")
  - Example: `"Home Alert"`

- **target**: The notification target(s) (string or list of strings)
  - Person entity: `person.john_doe`
  - Device ID: `device_abc123def456`
  - Notify service: `notify.mobile_app_phone`
  - Multiple targets: `["person.john_doe", "notify.mobile_app_tablet"]`

- **data**: Additional notification metadata (object)
  - **image**: URL to an image to include with notification
    - Example: `"/local/snapshot.jpg"`
  - **tag**: Tag for grouping/replacing notifications
    - Example: `"motion_living_room"`
  - **group**: Notification group for organization
    - Example: `"security"` or `"weather"`

## Automation Examples

### Motion Detection Alert

```yaml
automation:
  - alias: Motion Detection Alert
    trigger:
      platform: state
      entity_id: binary_sensor.motion_sensor_living_room
      to: "on"
    action:
      service: effortlesshome.notify
      data:
        title: "Motion Detected"
        message: "Motion detected in the living room at {{ now().strftime('%H:%M') }}"
        target: person.john_doe
        data:
          tag: "motion_living_room"
          group: "security"
```

### Temperature Alert

```yaml
automation:
  - alias: High Temperature Alert
    trigger:
      platform: numeric_state
      entity_id: sensor.home_temperature
      above: 28
    action:
      service: effortlesshome.notify
      data:
        title: "⚠️ High Temperature"
        message: "Current temperature is {{ states('sensor.home_temperature') }}°C"
        target:
          - person.john_doe
          - person.jane_doe
```

### Security System Alert

```yaml
automation:
  - alias: Security Alert
    trigger:
      platform: state
      entity_id: alarm_control_panel.home_alarm
      to: "triggered"
    action:
      service: effortlesshome.notify
      data:
        title: "🚨 Security Alert"
        message: "Alarm triggered: {{ state_attr('alarm_control_panel.home_alarm', 'friendly_name') }}"
        target: person.john_doe
        data:
          tag: "security_alarm"
          group: "security"
          image: "{{ state_attr('camera.front_door', 'entity_picture') }}"
```

### Multi-Target Notification

```yaml
automation:
  - alias: Critical System Alert
    trigger:
      platform: template
      value_template: "{{ states('sensor.system_health') == 'critical' }}"
    action:
      service: effortlesshome.notify
      data:
        title: "🔴 Critical System Alert"
        message: "Critical issue detected: {{ states('sensor.system_health_message') }}"
        target:
          - person.john_doe
          - person.jane_doe
          - notify.persistent_notification
```

## Script Example

```yaml
script:
  notify_energy_usage:
    description: "Notify about high energy usage"
    fields:
      target:
        description: "Target person to notify"
        example: "person.john_doe"
    sequence:
      - service: effortlesshome.notify
        data:
          title: "⚡ High Energy Usage"
          message: "Current power usage: {{ states('sensor.power_usage') }}W"
          target: "{{ target }}"
          data:
            tag: "energy_alert"
            group: "utilities"
```

## Integration with Home Assistant Notify Platform

The EffortlessHome notify service can also work with Home Assistant's standard notify platform. You can:

1. Send to person entities that have mobile app notify services
2. Send to any configured notify service (e.g., `notify.mobile_app_*`, `notify.telegram`, etc.)
3. Use the service in automations that trigger other notifications

### Example: Chaining Notifications

```yaml
automation:
  - alias: Send Alert via Multiple Services
    trigger:
      platform: state
      entity_id: binary_sensor.front_door
      to: "on"
    action:
      # Send via EffortlessHome
      - service: effortlesshome.notify
        data:
          title: "Front Door Opened"
          message: "The front door was opened at {{ now().strftime('%H:%M:%S') }}"
          target: person.john_doe
      
      # Also send persistent notification to Home Assistant
      - service: persistent_notification.create
        data:
          title: "Front Door Alert"
          message: "The front door was opened"
          notification_id: "front_door_open"
```

## Troubleshooting

### Notification Not Received

1. **Check target format**: Ensure the target is a valid person entity, device ID, or notify service
2. **Verify person has mobile app**: The person entity must have associated mobile app notify services
3. **Check logs**: Look for error messages in Home Assistant logs
4. **Test with persistent notification**: Try sending to `notify.persistent_notification` to verify the service works

### Device Not Found

- Verify the device is properly registered in EffortlessHome
- Check the device ID format (should start with `device_`)
- Ensure the device is online and connected

### Service Not Found

- Confirm the EffortlessHome integration is loaded
- Check that the service name is exactly `effortlesshome.notify`
- Restart Home Assistant if the service was just added

## Technical Details

### Target Resolution

The service automatically detects the target type:

- **person.\***: Looks for associated mobile app notify services
- **notify.\***: Calls the notify service directly
- **device_\***: Routes through EffortlessHome device notification system

### Data Fields

Additional data fields are forwarded to the underlying notify service when applicable:

- **image**: URL to notification image
- **tag**: Unique identifier for replacing/grouping notifications
- **group**: Logical grouping of related notifications
- Any other custom fields supported by the target notify service

### Error Handling

The service gracefully handles:

- Missing targets (logs warning, continues processing)
- Invalid entity formats (skips invalid targets)
- Service failures (logs error, attempts next target if multiple)
- Missing device registry (falls back to alternative methods)

## Future Enhancements

Potential improvements to the EffortlessHome notification service:

- Direct device notification API integration
- Notification templates and presets
- Notification history and statistics
- Advanced targeting (areas, groups, labels)
- Rich notification UI with actions
- Notification scheduling and delays
- Priority levels and urgency indicators
