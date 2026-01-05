# 🏠 EffortlessHome

[![HACS Badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)
[![Version](https://img.shields.io/badge/version-1.2.7-blue.svg)](https://github.com/effortlesshome/effortlesshome)

**EffortlessHome** is a next-generation Home Assistant integration designed to turn your house into a truly intelligent, automated ecosystem. By combining advanced AI, robust security, and dynamic area management, EffortlessHome simplifies your smart home experience.

---

## ✨ Key Features

### 🛡️ Advanced Security & Safety
A professional-grade alarm system integrated directly into Home Assistant:
- **Multi-Mode Arming**: Support for Home, Away, Night, Vacation, and Custom Bypass modes.
- **Medical Alert Integration**: Dedicated support for medical emergency monitoring.
- **Smart Triggering**: Intelligent sensor grouping and motion notification logic to reduce false alarms.

### 📍 Area-Aware Automation
EffortlessHome understands the context of your rooms:
- **Dynamic Presence**: Automatically manage lights, covers, and climate based on room occupancy.
- **Sleep Mode**: Intelligent area-specific sleep states for customized nighttime behavior.
- **Privacy First**: Built-in "Presence Lock" to maintain privacy when needed.


### 📊 Beautiful PWA Dashboard

### 📊 Beautiful Home Assistant Theme


### 📝 Blueprints For Automations
EffortlessHome provides **38+ pre-configured blueprints** to automate your home without writing a single line of YAML.

#### 🛡️ Security
- **Security Alarm Trigger**: Define which Door, Window, or Motion sensors trigger your security system.
- **Monitoring Alarm Trigger**: Separate logic for internal monitoring and safety alerts.
- **Security Alarm Notifications**: Get detailed alerts when the main security system is triggered.
- **Monitoring Alarm Notifications**: Receive notifications specifically for monitoring-level alerts.
- **Disarm on Door Unlock**: Automatically disarm the security alarm when an authorized door unlock is detected.
- **Add Event to Active Alarm**: Logs sensor events (like motion or door opens) to the active alarm timeline for better post-event auditing.

#### 🚑 Safety Alerts
- **Smoke Alarm**: Actions to take when a smoke detector is activated.
- **Carbon Monoxide Alarm**: Specific safety alerts and actions for CO detection.
- **Water/Leak Alarm**: Immediate notifications and actions when water leaks are detected.
- **Temperature Alarm**: Get notified when areas reach extreme high or low temperatures.
- **Humidity Alarm**: Monitor for humidity levels that could lead to mold or discomfort.

#### 🌅 Daily Routines & Presence
- **Goodmorning**: Transitions home to "Awake" mode, opens covers, and disarms security.
- **Goodnight**: Transitions home to "Sleep" mode, locks doors, and arms security.
- **Arrive Home**: Set actions for the first person arriving, such as auto-disarming and unlocking.
- **Leave Home**: Automatically arm security and turn off lights when the last person leaves.
- **Sunset/Sunrise**: Light and blind control synchronized with the solar cycle.
- **Wake Alarm Sunrise Lights**: Gradually fade in lights before your scheduled wake time.
- **Door Left Unlocked/Open**: Notify and lock up if no one is home but a door is left open or unlocked.

#### 🧠 Intelligence & Convenience
- **Camera Flash Snapshots**: Capture and notify with snapshots when motion is detected.
- **Camera Video Recording**: Capture video clips automatically during motion events.
- **Illuminance-Aware Motion Lights**: Motion-activated lighting that only triggers if the room is dark.
- **Doors/Windows & Climate Sync**: Automatically turn off climate control if windows or doors are left open.
- **Weather-Based Climate**: Adjust climate settings automatically based on outdoor conditions.
- **Motion Notification Snooze**: Quickly snooze motion alerts for specific areas from your phone.
- **Calendar Event Reminders**: Real-time announcements and notifications for upcoming calendar events.
- **Set In Bed Status**: Automatically update "In Bed" status based on weight or movement sensors.
- **Climate Control Notification Actions**: Handle "Turn Off" actions directly from climate notifications.

#### 🛠️ Device & System Maintenance
- **Auto-Update**: Advanced management for Home Assistant Core, OS, and Add-on updates.
- **Low Battery Monitoring**: Centralized battery checks and notifications for all your devices.
- **Offline Device Reports**: Periodic reports of Zigbee or Z-Wave devices that have gone offline.
- **Database Cleanup**: Automated maintenance to optimize the Home Assistant database.
- **Motion File Cleanup**: Automatically delete old snapshots and videos to save space.
- **System Startup Recovery**: Ensure your home returns to a known state after a system restart.

#### 🔌 Smart Appliance Conversions
- **Smart Appliance Start**: Detect and notify when a laundry cycle or generic appliance starts.
- **Smart Appliance End**: Get notified exactly when a generic appliance finishes its task.
- **Oven Cycle Start**: Specialized detection and alerts for oven preheating/starting.
- **Oven Cycle End**: Notifications for when your oven has finished its cycle.

### 🛌 Automated Sleep & Awake Modes

### Home & Away Modes

### Convenience Sensors & Entities
- Virtual Illuminance Sensor Based on Sun

### Convenience Config Tools
- Drag & Drop Area Management
- Drag & Drop Label Management

### And Much More To Come!!!!- 
- HA-native integration
- Built-in AI for Home Assistant
- EffortlessHome Hardware/Hub
- More blueprints for automations
- Google, Nest, Eufy, and more integrations (simplified)
- Influx and Grafana integration (simplified)

---
## 🚀 Getting Started

### 1. Account Setup
Before installing the integration, you need an EffortlessHome account.
- **Visit**: [my.effortlesshome.co](https://my.effortlesshome.co) to sign up and configure your system.

### 2. Installation

#### Via HACS (Recommended)
1. Open **HACS** in Home Assistant.
2. Search for `EffortlessHome`.
3. Click **Download** and restart Home Assistant.

#### Manual Installation
1. Copy the `custom_components/effortlesshome` directory to your Home Assistant `custom_components/` folder.
2. Restart Home Assistant.

### 3. Configuration
1. Navigate to **Settings > Devices & Services**.
2. Click **Add Integration** and search for **EffortlessHome**.
3. Sign in with your credentials or enter your IDs manually.

---

## 🛠️ Requirements
- Home Assistant 2024.1 or later.
- `recorder` component must be enabled.
- Active internet connection for AI features (cloud polling).

---

## 🤝 Community & Support
- **Report Issues**: [GitHub Issues](https://github.com/effortlesshome/effortlesshome/issues)
- **Documentation**: [Official Docs](https://github.com/effortlesshome/)
- **Website**: [effortlesshome.co](https://effortlesshome.co)

