# EffortlessHome Notifications - Developer Integration Guide

## Overview

This guide explains how to integrate EffortlessHome notifications into custom automations, scripts, and integrations for sending notifications to users' mobile devices and other targets.

## Architecture

The EffortlessHome notification system consists of:

1. **Notify Service** (`notify_service.py`): Core service handling notifications
2. **Service Registration** (`__init__.py`): Registers the service with Home Assistant
3. **Service Call Handler**: Processes notification requests from automations/scripts

## Core Components

### NotificationService Class

The `EffortlessHomeNotificationService` class provides the main notification functionality:

```python
class EffortlessHomeNotificationService(BaseNotificationService):
    """EffortlessHome notification service."""
    
    async def async_send_message(
        self,
        message: str,
        title: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Send a message to EffortlessHome devices."""
```

### Service Methods

#### `async_send_message()`

Main entry point for sending notifications:

```python
await service.async_send_message(
    message="Hello",
    title="Title",
    target="person.john_doe",
    data={"image": "/local/image.jpg"}
)
```

#### `_send_to_target()`

Routes notification to the correct target type (person, device, or notify service).

#### `_send_to_person()`

Sends to a person entity by finding their associated mobile app notify services.

#### `_send_to_device()`

Sends to a specific EffortlessHome registered device (future enhancement).

#### `_send_to_notify_service()`

Delegates to an existing Home Assistant notify service.

## Usage Examples

### From Python Code

```python
from homeassistant.core import HomeAssistant

async def my_function(hass: HomeAssistant):
    """Send a notification programmatically."""
    await hass.services.async_call(
        "effortlesshome",
        "notify",
        {
            "message": "Hello from code",
            "title": "Test",
            "target": "person.john_doe",
            "data": {
                "image": "/local/image.jpg",
                "tag": "test_notification"
            }
        }
    )
```

### From YAML Automation

```yaml
automation:
  - alias: "Send Notification"
    trigger:
      platform: state
      entity_id: switch.motion_sensor
      to: "on"
    action:
      service: effortlesshome.notify
      data:
        message: "Motion detected"
        title: "Alert"
        target: person.john_doe
```

### From Script

```yaml
script:
  notify_users:
    description: "Send notification to multiple users"
    fields:
      message:
        description: "Message to send"
        example: "Hello"
    sequence:
      - service: effortlesshome.notify
        data:
          message: "{{ message }}"
          title: "Notification"
          target:
            - person.john_doe
            - person.jane_doe
```

## Advanced Usage

### Dynamic Target Selection

```python
async def notify_on_condition(hass: HomeAssistant):
    """Send to different targets based on conditions."""
    # Determine target based on time of day
    from datetime import datetime
    hour = datetime.now().hour
    
    if 6 <= hour < 22:
        target = "person.john_doe"  # Daytime
    else:
        target = None  # Nighttime - don't notify
    
    if target:
        await hass.services.async_call(
            "effortlesshome",
            "notify",
            {
                "message": "Important alert",
                "title": "Alert",
                "target": target,
            }
        )
```

### Template-Based Messages

```yaml
action:
  service: effortlesshome.notify
  data:
    title: "{{ state_attr(trigger.entity_id, 'friendly_name') }} Alert"
    message: >
      {% if states(trigger.entity_id) == 'on' %}
        Device turned ON at {{ now().strftime('%H:%M') }}
      {% else %}
        Device turned OFF at {{ now().strftime('%H:%M') }}
      {% endif %}
    target: person.john_doe
```

### Conditional Notifications

```yaml
action:
  - choose:
      - conditions:
          - condition: numeric_state
            entity_id: sensor.temperature
            above: 30
        sequence:
          - service: effortlesshome.notify
            data:
              title: "🔥 Hot Alert"
              message: "Temperature is {{ states('sensor.temperature') }}°C"
              target: person.john_doe
              data:
                tag: "hot_alert"
                
      - conditions:
          - condition: numeric_state
            entity_id: sensor.temperature
            below: 5
        sequence:
          - service: effortlesshome.notify
            data:
              title: "❄️ Cold Alert"
              message: "Temperature is {{ states('sensor.temperature') }}°C"
              target: person.john_doe
              data:
                tag: "cold_alert"
```

## Integration Points

### With Custom Components

To integrate EffortlessHome notifications in your custom component:

```python
from homeassistant.core import HomeAssistant, ServiceCall

async def setup(hass: HomeAssistant, config):
    """Set up your integration."""
    
    async def my_service_handler(call: ServiceCall):
        """Handle your service call."""
        # Process something...
        
        # Send notification
        await hass.services.async_call(
            "effortlesshome",
            "notify",
            {
                "message": "Your custom integration ran",
                "title": "Status",
                "target": "person.john_doe"
            }
        )
    
    hass.services.async_register(
        "my_domain",
        "my_service",
        my_service_handler
    )
```

### With Blueprints

Create a blueprint that uses EffortlessHome notifications:

```yaml
blueprint:
  name: Motion Alert with EffortlessHome Notification
  description: Send notification when motion is detected
  domain: automation
  input:
    motion_sensor:
      selector:
        entity:
          domain: binary_sensor
          device_class: motion
    notification_target:
      selector:
        entity:
          domain: person

trigger:
  platform: state
  entity_id: !input motion_sensor
  to: "on"

action:
  service: effortlesshome.notify
  data:
    title: "Motion Detected"
    message: "Motion detected at {{ now().strftime('%H:%M:%S') }}"
    target: !input notification_target
```

## Error Handling

The service includes error handling for:

1. **Missing targets**: Logs warning, continues
2. **Invalid entity formats**: Skips invalid targets, processes valid ones
3. **Service call failures**: Logs error, attempts next target if multiple
4. **Entity not found**: Logs warning, gracefully degrades

Example of robust notification:

```python
try:
    await hass.services.async_call(
        "effortlesshome",
        "notify",
        {
            "message": "Test",
            "title": "Alert",
            "target": "person.john_doe",
        },
        blocking=True,  # Wait for completion
    )
except Exception as e:
    _LOGGER.error("Failed to send notification: %s", e)
    # Fall back to persistent notification
    from homeassistant.components.persistent_notification import async_create
    await async_create(
        hass,
        "Critical alert (notification service failed)",
        title="Alert",
        notification_id="fallback_alert"
    )
```

## Data Fields Reference

### Standard Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `message` | string | Notification body | `"Hello world"` |
| `title` | string | Notification title | `"Alert"` |
| `target` | string/list | Recipient(s) | `"person.john"` |

### Data Field Contents

Within the `data` object:

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| `image` | string | Image URL | `"/local/snapshot.jpg"` |
| `tag` | string | Notification tag | `"motion_living_room"` |
| `group` | string | Notification group | `"security"` |

## Extending the Service

### Adding Device Notification Support

To add direct device notification support:

```python
async def _send_to_device(self, device_id: str, notification_data: Dict[str, Any]) -> None:
    """Send notification to a specific device via EffortlessHome API."""
    try:
        # Get device info from registry
        device_registry = self.hass.helpers.device_registry.async_get(self.hass)
        device = device_registry.async_get(device_id)
        
        if not device:
            _LOGGER.warning("Device not found: %s", device_id)
            return
        
        # Send via EffortlessHome API
        async with aiohttp.ClientSession() as session:
            # Implementation details...
            pass
            
    except Exception as e:
        _LOGGER.error("Error sending to device: %s", e)
```

### Adding Custom Data Processing

```python
async def _send_to_notify_service(
    self, notify_service: str, notification_data: Dict[str, Any]
) -> None:
    """Enhanced version with custom data processing."""
    service_data = {
        "entity_id": notify_service,
        "message": notification_data.get("message", ""),
        "title": notification_data.get("title", ""),
    }
    
    # Custom processing
    if notification_data.get("image"):
        # Process image - maybe resize, optimize, etc.
        image = await self._process_image(notification_data["image"])
        service_data["data"]["image"] = image
    
    await self.hass.services.async_call(
        "notify",
        "send_message",
        service_data,
        blocking=True,
    )
```

## Best Practices

1. **Always provide a fallback**: If EffortlessHome notification fails, use persistent notifications
2. **Use tags for critical notifications**: Allows replacing/grouping related alerts
3. **Include timestamps**: Help users understand when the event occurred
4. **Use templates**: Dynamic messages are more informative
5. **Avoid notification spam**: Implement debouncing for repeated alerts
6. **Test thoroughly**: Use Developer Tools to test before automating

## Troubleshooting

### Debug Logging

Enable debug logging for the notify service:

```yaml
logger:
  logs:
    homeassistant.components.effortlesshome.notify_service: debug
```

### Common Issues

**Service not found**
- Check service is registered: go to Developer Tools → Services
- Look for `effortlesshome.notify`
- Restart Home Assistant if recently added

**Target not found**
- Verify person entity exists: `person.john_doe`
- Check mobile app notify service: `notify.mobile_app_*`
- Look for errors in Home Assistant logs

**Message not received**
- Check device is online
- Verify person has mobile app installed
- Look for network connectivity issues

## Related Documentation

- [Home Assistant Notify Integration](https://www.home-assistant.io/integrations/notify/)
- [Automations Documentation](https://www.home-assistant.io/docs/automation/)
- [Service Calls](https://www.home-assistant.io/docs/scripts/service-calls/)
- [Templating](https://www.home-assistant.io/docs/configuration/templating/)
