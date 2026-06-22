"""constants."""

import datetime
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    DOMAIN as BINARY_SENSOR_DOMAIN,
)
from homeassistant.components.cover import DOMAIN as COVER_DOMAIN
from homeassistant.components.light import DOMAIN as LIGHT_DOMAIN
from homeassistant.components.sensor.const import DOMAIN as SENSOR_DOMAIN
from homeassistant.components.switch.const import DOMAIN as SWITCH_DOMAIN

NAME = "EffortlessHome"
DOMAIN = "effortlesshome"
VERSION = "2.0.13"
# Labels we want to ensure exist
LABELS = [
    "Favorite",
    "NotForSecurityMonitoring",
]

PRESENCE_LOCK_SWITCH_PREFIX = ""
PRESENCE_LOCK_SWITCH_ENTITY_PREFIX = "switch.area_presence_lock_"

SLEEP_MODE_SWITCH_PREFIX = "Sleep Mode "
SLEEP_MODE_SWITCH_ENTITY_PREFIX = "switch.area_sleep_mode_"

PRESENCE_BINARY_SENSOR_PREFIX = ""
PRESENCE_BINARY_SENSOR_ENTITY_PREFIX = "binary_sensor.area_presence_"

ILLUMINANCE_SENSOR_PREFIX = ""
ILLUMINANCE_SENSOR_ENTITY_PREFIX = "sensor.area_illuminance_"

TEMPERATURE_SENSOR_PREFIX = ""
TEMPERATURE_SENSOR_ENTITY_PREFIX = "sensor.area_temperature_"

HUMIDITY_SENSOR_PREFIX = ""
HUMIDITY_SENSOR_ENTITY_PREFIX = "sensor.area_humidity_"

COVER_GROUP_PREFIX = ""
COVER_GROUP_ENTITY_PREFIX = "cover.area_covers_"

LIGHT_GROUP_PREFIX = ""
LIGHT_GROUP_ENTITY_PREFIX = "light.area_"

INITIALIZATION_TIME = datetime.timedelta(seconds=60)
SENSOR_ARM_TIME = datetime.timedelta(seconds=5)

ALARM_TYPE_MED_ALERT = "medicalalert"
ALARM_TYPE_SECURITY = "security"
ALARM_TYPE_MONITORING = "monitoring"

COMMAND_ARM_NIGHT = "arm_night"
COMMAND_ARM_AWAY = "arm_away"
COMMAND_ARM_HOME = "arm_home"
COMMAND_ARM_CUSTOM_BYPASS = "arm_custom_bypass"
COMMAND_ARM_VACATION = "arm_vacation"
COMMAND_DISARM = "disarm"

COMMANDS = [
    COMMAND_DISARM,
    COMMAND_ARM_AWAY,
    COMMAND_ARM_NIGHT,
    COMMAND_ARM_HOME,
    COMMAND_ARM_CUSTOM_BYPASS,
    COMMAND_ARM_VACATION,
]

EVENT_DISARM = "disarm"
EVENT_LEAVE = "leave"
EVENT_ARM = "arm"
EVENT_ENTRY = "entry"
EVENT_TRIGGER = "trigger"
EVENT_FAILED_TO_ARM = "failed_to_arm"
EVENT_COMMAND_NOT_ALLOWED = "command_not_allowed"
EVENT_INVALID_CODE_PROVIDED = "invalid_code_provided"
EVENT_NO_CODE_PROVIDED = "no_code_provided"
EVENT_TRIGGER_TIME_EXPIRED = "trigger_time_expired"
EVENT_READY_TO_ARM_MODES_CHANGED = "ready_to_arm_modes_changed"

ISSUE_TYPE_INVALID_AREA = "invalid_area_config"

# Fetch entities from these domains:
RELEVANT_DOMAINS = [
    BINARY_SENSOR_DOMAIN,
    SENSOR_DOMAIN,
    SWITCH_DOMAIN,
    LIGHT_DOMAIN,
    COVER_DOMAIN,
]

# State to arm mode mapping for event.py
STATE_TO_ARM_MODE = {
    "arm_away": "away",
    "arm_home": "home",
    "arm_night": "night",
    "arm_vacation": "vacation",
    "arm_custom_bypass": "custom_bypass",
}

ATTR_LATITUDE = "latitude"
ATTR_LONGITUDE = "longitude"
CONF_EMAIL = "email"
CONF_TRACKING_ENABLED = "tracking_enabled"
CONF_NOTIFICATIONS_ENABLED = "notifications_enabled"
WEBHOOK_UPDATE_PUSH_TOKEN = "effortlesshome_push_token"
