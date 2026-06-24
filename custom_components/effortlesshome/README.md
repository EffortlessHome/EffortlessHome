# EffortlessHome

[![GitHub Release][releases-shield]][releases]
[![License][license-shield]](LICENSE)

![Project Maintenance][maintenance-shield]
[![BuyMeCoffee][buymecoffeebadge]][buymecoffee]

[![Discord][discord-shield]][discord]
[![Community Forum][forum-shield]][forum]

EffortlessHome is a comprehensive Home Assistant integration that provides advanced home automation features including security monitoring, presence detection, and smart home coordination.

## Features

- **Custom Dashboard and Apps**: Easy to use, UX optimized dashboard apps for iOS, Android, Mac, Windows, TVOS, Android/Google TV
- **Security Monitoring**: Comprehensive alarm system with support for multiple alarm types (security, monitoring, medical alert)
- **Presence Detection**: Advanced person tracking with local and remote device trackers
- **Area Management**: Automatic area-based automation and entity organization
- **Motion Sensor Groups**: Intelligent grouping of motion sensors for security and automation
- **Notification System**: Push notifications via Firebase Cloud Messaging
- **Virtual Power Sensors**: Create virtual power monitoring for devices
- **Sleep Mode**: Area-based sleep mode automation
- **Smart Appliance Integration**: Monitor and automate smart appliances
- **Calendar Integration**: Google Calendar integration for automation triggers
- **Weather-based Automation**: Climate control based on weather forecasts

## Installation

### HACS Installation (Recommended)

1. Open HACS in your Home Assistant instance
2. Add this GitHub repo as a custom source: `https://github.com/effortlesshome/effortlesshome`
3. Search for "EffortlessHome"
4. Click Install
5. Restart Home Assistant

### Manual Installation

1. Copy the `effortlesshome` directory to your `custom_components` folder
2. Restart Home Assistant
3. Add the integration via Configuration > Integrations > Add Integration > EffortlessHome

## Configuration

### Initial Setup

1. After installation, go to Configuration > Integrations
2. Click the "+" button and search for "EffortlessHome"
3. Enter your EffortlessHome account credentials
4. Select the system you want to configure (if you have multiple systems)

### Required Information

- **Email**: Your EffortlessHome account email
- **Password**: Your EffortlessHome account password

### Optional Configuration

After initial setup, you can configure additional options:

- **Debug Mode**: Enable debug logging for troubleshooting

## Services

The integration provides several services:

| Service | Description |
|---------|-------------|
| `effortlesshome.clean_motion_files` | Clean old motion snapshot files |
| `effortlesshome.cancel_alarm` | Cancel an active alarm |
| `effortlesshome.get_alarm_status` | Get current alarm status |
| `effortlesshome.confirm_pending_alarm` | Confirm a pending alarm |
| `effortlesshome.create_event` | Create an event for active alarm |
| `effortlesshome.deploy_latest_config` | Deploy latest configuration files |
| `effortlesshome.get_firebase_config` | Get Firebase configuration |
| `effortlesshome.add_label_to_entity` | Add a label to an entity |
| `effortlesshome.update_entity` | Update entity area assignment |

## Entities

The integration creates various entities including:

### Binary Sensors
- Security Motion Group
- Window Group
- Door Group
- Smoke Group
- Carbon Monoxide Group
- Moisture Group
- Monitoring Alarm
- Sleeping Sensor
- Someone Home Sensor
- Smart Appliance Sensors

### Sensors
- Alarm ID Sensor
- Alarm Status Sensor
- Alarm Last Event Sensor
- Average Temperature Sensor
- Average Humidity Sensor
- Virtual Illuminance Sensor
- High Temperature Tomorrow Sensor
- Configuration Sensors
- Person Sensors

### Switches
- Sleep Mode Switch
- Motion Notifications Switch
- Monitoring Alarm Switch
- Disable Motion Lighting Switch
- Smart Appliance Conversion Switches
- Presence Simulation Switch

## Blueprints

The integration includes numerous automation blueprints for common scenarios:

- Arrival/Departure automation
- Good Morning/Good Night routines
- Security alarm triggers and notifications
- Motion-activated lighting
- Climate control automation
- Low battery notifications
- And many more...

## Requirements

### Dependencies

This integration requires the following Python packages (automatically installed):

- `oasira>=0.2.12`
- `gcal-sync>=6.2.0`
- `google-auth>=2.28.0`
- `google-api-python-client>=2.126.0`
- `gTTS>=2.5.0`

### Home Assistant Dependencies

The integration requires the following Home Assistant components:

- `http`
- `panel_custom`
- `recorder`
- `light`
- `button`
- `group`
- `binary_sensor`
- `sensor`
- `conversation`


## Labels

The integration uses the following labels for entity organization:

- `Favorite`: Mark favorite entities
- `NotForSecurityMonitoring`: Exclude entities from security monitoring

## Support

- **GitHub Issues**: [Report bugs and feature requests](https://github.com/EffortlessHome/EffortlessHome/issues)


## Contributing

We welcome contributions! Please see our [contributing guidelines](CONTRIBUTING.md) for more information.

## License

This project is licensed under the Apache License Version 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Home Assistant community
- All contributors and testers
- EffortlessHome users

---

**Note**: This integration requires an EffortlessHome account. Sign up at [https://my.effortlesshome.co](https://my.effortlesshome.co)


[forum]: https://community.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/EffortlessHome/EffortlessHome.svg?style=for-the-badge
[maintenance-shield]: https://img.shields.io/maintenance/yes/2024.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/EffortlessHome/EffortlessHome.svg?style=for-the-badge
[releases]: https://github.com/EffortlessHome/EffortlessHome/releases