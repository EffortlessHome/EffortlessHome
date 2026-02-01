# EffortlessHome Notifications - Quick Start Guide

## Overview

EffortlessHome provides a custom notifications service that integrates with Home Assistant's notify infrastructure, allowing you to send notifications from automations to users' devices.

## Quick Examples

### Send a Simple Notification

```yaml
service: effortlesshome.notify
data:
  message: "Hello from EffortlessHome!"
  title: "Test Notification"
  target: person.john_doe
```

### Send to Multiple People

```yaml
service: effortlesshome.notify
data:
  message: "Alert: Motion detected"
  title: "Security Alert"
  target:
    - person.john_doe
    - person.jane_doe
```

### Send with Image

```yaml
service: effortlesshome.notify
data:
  message: "Front door activity detected"
  title: "🔔 Front Door"
  target: person.john_doe
  data:
    image: "/local/camera_snapshot.jpg"
    tag: "front_door"
```

## How to Use in Automations

Edit your `automations.yaml` and add an action:

```yaml
- alias: "Door Open Alert"
  trigger:
    platform: state
    entity_id: binary_sensor.front_door
    to: "on"
  action:
    service: effortlesshome.notify
    data:
      title: "🚪 Door Alert"
      message: "Front door was opened"
      target: person.john_doe
```

## Supported Targets

1. **Person entities**: `person.john_doe`
   - Sends to all mobile app notify services for that person
   
2. **Notify services**: `notify.mobile_app_iphone`
   - Sends directly to the notify service
   
3. **Device IDs**: `device_abc123def456`
   - Sends to EffortlessHome registered devices

## Common Use Cases

### High Temperature Alert

```yaml
automation:
  - alias: "High Temp Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.home_temperature
      above: 28
    action:
      service: effortlesshome.notify
      data:
        title: "🌡️ High Temperature"
        message: "Temperature is {{ states('sensor.home_temperature') }}°C"
        target: person.john_doe
```

### Water Leak Detection

```yaml
automation:
  - alias: "Water Leak Alert"
    trigger:
      platform: state
      entity_id: binary_sensor.water_leak_sensor
      to: "on"
    action:
      service: effortlesshome.notify
      data:
        title: "💧 Water Leak"
        message: "Water leak detected in {{ state_attr('binary_sensor.water_leak_sensor', 'location') }}"
        target: person.john_doe
```

### Low Battery Alert

```yaml
automation:
  - alias: "Low Battery Alert"
    trigger:
      platform: numeric_state
      entity_id: sensor.device_battery
      below: 10
    action:
      service: effortlesshome.notify
      data:
        title: "🔋 Low Battery"
        message: "Battery level: {{ states('sensor.device_battery') }}%"
        target: person.john_doe
```

## Template Support

Use Jinja2 templates in messages:

```yaml
service: effortlesshome.notify
data:
  title: "Alert"
  message: >
    {{ state_attr('climate.living_room', 'friendly_name') }} is set to 
    {{ states('climate.living_room') }}
  target: person.john_doe
```

## Testing

You can test the service directly:

1. Go to **Developer Tools** → **Services**
2. Select service: `effortlesshome.notify`
3. Fill in the data:
   ```yaml
   message: "Test notification"
   title: "Test"
   target: person.john_doe
   ```
4. Click **PERFORM ACTION**

## Troubleshooting

**Notification not received?**
- Verify target person has mobile app notify service (e.g., `notify.mobile_app_iphone`)
- Check Home Assistant logs for errors
- Try sending to `notify.persistent_notification` first to test basic functionality

**Service not found?**
- Make sure EffortlessHome integration is loaded
- Restart Home Assistant after adding the integration
- Check if the service shows in Developer Tools → Services

**Invalid target?**
- Use entity IDs for person: `person.name`
- Use full notify service names: `notify.mobile_app_device`
- Check spelling and case sensitivity

## API Reference

### Service: `effortlesshome.notify`

| Field | Type | Required | Example |
|-------|------|----------|---------|
| `message` | string | ✅ Yes | `"Motion detected"` |
| `title` | string | ❌ No | `"Alert"` |
| `target` | string/list | ❌ No | `person.john_doe` or `["person.john", "notify.mobile_app"]` |
| `data` | object | ❌ No | `{image: "/local/image.jpg"}` |

### Data Fields

Within the optional `data` object, you can specify:

- `image`: Image URL to include with notification
- `tag`: Notification tag for grouping/replacing
- `group`: Notification group for organization

## Next Steps

- Review the full documentation: [Notifications Service](notifications_service.md)
- Create automations using the examples above
- Test with different notification scenarios
- Set up notification groups for multiple users
