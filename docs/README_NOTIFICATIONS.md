# EffortlessHome Notifications Documentation Index

Welcome! This directory contains comprehensive documentation for the EffortlessHome notifications implementation.

## 📚 Documentation Files

### For Users

1. **[Quick Start Guide](notifications_quick_start.md)** ⭐ **START HERE**
   - Quick 5-minute introduction
   - Copy-paste ready examples
   - Common use cases
   - Testing instructions

2. **[Complete Service Documentation](notifications_service.md)**
   - Detailed service reference
   - All parameters explained
   - 5+ full automation examples
   - Troubleshooting guide

### For Developers

3. **[Developer Integration Guide](notifications_developer_guide.md)**
   - Architecture overview
   - Python code examples
   - Custom component integration
   - Extension examples
   - Best practices

### Reference

4. **[Implementation Summary](NOTIFICATIONS_IMPLEMENTATION.md)**
   - What was implemented
   - Files created/modified
   - Features list
   - Future enhancements

## 🚀 Quick Links

### I want to...

- **Send a simple notification** → [Quick Start](notifications_quick_start.md#quick-examples)
- **Set up motion alerts** → [Motion Detection Example](notifications_service.md#motion-detection-alert)
- **Create a blueprint** → [Developer Guide - Blueprints](notifications_developer_guide.md#with-blueprints)
- **Integrate in my custom component** → [Developer Guide - Integration](notifications_developer_guide.md#with-custom-components)
- **Understand the architecture** → [Developer Guide - Architecture](notifications_developer_guide.md#architecture)
- **Troubleshoot an issue** → [Troubleshooting](notifications_service.md#troubleshooting)

## 🔧 Implementation Details

### Service Name
```
effortlesshome.notify
```

### Core Files
- `custom_components/effortlesshome/notify_service.py` - Service implementation
- `custom_components/effortlesshome/__init__.py` - Integration
- `custom_components/effortlesshome/services.yaml` - Service definition

### Key Features
- ✅ Send to person entities
- ✅ Send to notify services
- ✅ Multiple targets
- ✅ Notification data (images, tags, groups)
- ✅ Template support
- ✅ Error handling

## 📋 Service Overview

### Service Call

```yaml
service: effortlesshome.notify
data:
  message: "Notification body"
  title: "Optional title"
  target: "person.john_doe"  # or list of targets
  data:
    image: "/local/image.jpg"
    tag: "alert_id"
    group: "category"
```

### Supported Targets

- Person entities: `person.john_doe`
- Notify services: `notify.mobile_app_iphone`
- Device IDs: `device_abc123def456`

## 🎯 Common Examples

### Basic Notification
```yaml
service: effortlesshome.notify
data:
  message: "Hello!"
  title: "Hi"
  target: person.john_doe
```

### Motion Alert
```yaml
service: effortlesshome.notify
data:
  title: "Motion Detected"
  message: "Motion detected in the living room"
  target: person.john_doe
  data:
    tag: "motion_living_room"
```

### Multi-User Alert
```yaml
service: effortlesshome.notify
data:
  title: "Alert"
  message: "Important notification"
  target:
    - person.john_doe
    - person.jane_doe
```

## 🧪 Testing

### Via Developer Tools
1. Go to **Developer Tools** → **Services**
2. Select `effortlesshome.notify`
3. Enter test data
4. Click **PERFORM ACTION**

### Via Automation
```yaml
automation:
  - alias: Test
    trigger:
      platform: time
      at: "12:00:00"
    action:
      service: effortlesshome.notify
      data:
        message: "Test"
        target: person.john_doe
```

## 📖 Documentation Structure

```
notifications_quick_start.md
├─ Quick examples
├─ How to use in automations
├─ Common use cases
├─ Testing
└─ API reference

notifications_service.md
├─ Service overview
├─ Detailed field reference
├─ Automation examples
├─ Script examples
├─ Technical details
└─ Troubleshooting

notifications_developer_guide.md
├─ Architecture
├─ Core components
├─ Usage examples
├─ Advanced usage
├─ Integration points
├─ Best practices
└─ Troubleshooting

NOTIFICATIONS_IMPLEMENTATION.md
└─ Implementation summary
  ├─ What was built
  ├─ Files created
  ├─ Features
  └─ Future enhancements
```

## ❓ FAQ

**Q: How do I send a notification?**  
A: Use the `effortlesshome.notify` service with message and target.

**Q: What targets are supported?**  
A: Person entities, notify services, and device IDs.

**Q: Can I send to multiple people?**  
A: Yes, use a list for the target field.

**Q: How do I add images?**  
A: Use the `data.image` field with a URL.

**Q: Does it work with templates?**  
A: Yes, use Jinja2 templates in the message.

**Q: What if the notification fails?**  
A: Check logs, verify targets exist, try persistent_notification fallback.

## 📞 Support

For issues or questions:
1. Check the [Troubleshooting](notifications_service.md#troubleshooting) section
2. Review the [Developer Guide](notifications_developer_guide.md#troubleshooting)
3. Check Home Assistant logs for error messages
4. Verify service is registered in Developer Tools → Services

## 🔄 Integration Points

The notification service integrates with:
- Home Assistant Automations
- Home Assistant Scripts
- Home Assistant Service Calls
- Custom Components
- Developer Tools

## 📈 Future Enhancements

Planned features:
- Notification templates
- Notification history
- Advanced targeting (areas, groups)
- Rich notification UI with actions
- Notification scheduling
- Priority levels

---

**Created**: February 1, 2026  
**Status**: ✅ Complete  
**Version**: 1.0
