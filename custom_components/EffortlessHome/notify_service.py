"""EffortlessHome Notification Service - Direct Flutter App Integration."""

import logging
import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import webhook
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import aiohttp

_LOGGER = logging.getLogger(__name__)

# Webhook paths for app notifications
WEBHOOK_NOTIFY = "effortlesshome_app_notify"


class AppNotificationManager:
    """Manages notifications for EffortlessHome Flutter app."""

    def __init__(self, hass: HomeAssistant):
        """Initialize the notification manager."""
        self.hass = hass
        self.notifications: Dict[str, Dict[str, Any]] = {}
        self._registered_devices: Dict[str, Dict[str, Any]] = {}

    async def send_notification(
        self,
        title: str,
        message: str,
        category: str = "automation",
        target: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
    ) -> str:
        """
        Send a notification to the Flutter app.
        
        Args:
            title: Notification title
            message: Notification message
            category: Category (security, system, automation, access)
            target: Target person/device (optional)
            data: Additional data
            image_url: URL to notification image
            
        Returns:
            Notification ID
        """
        notification_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()

        notification = {
            "notification_id": notification_id,
            "title": title,
            "message": message,
            "category": category,
            "timestamp": timestamp,
            "created_at": timestamp,
            "data": data or {},
            "image_url": image_url,
            "target": target,
        }

        # Store notification
        self.notifications[notification_id] = notification

        _LOGGER.debug(f"[AppNotificationManager] Created notification: {notification_id}")

        # Send to registered app instances
        await self._dispatch_to_apps(notification)

        return notification_id

    async def _dispatch_to_apps(self, notification: Dict[str, Any]) -> None:
        """Dispatch notification to all registered app instances."""
        try:
            # Get all registered app instances from hass.data
            app_instances = self.hass.data.get("effortlesshome_app_instances", {})

            if not app_instances:
                _LOGGER.debug("[AppNotificationManager] No app instances registered")
                return

            _LOGGER.info(
                f"[AppNotificationManager] Dispatching to {len(app_instances)} app instances"
            )

            # Send notification to each app instance via webhook/FCM
            for app_id, instance_data in app_instances.items():
                await self._send_to_app(app_id, instance_data, notification)

        except Exception as e:
            _LOGGER.error(f"[AppNotificationManager] Error dispatching to apps: {e}")

    async def _send_to_app(
        self, app_id: str, instance_data: Dict[str, Any], notification: Dict[str, Any]
    ) -> None:
        """Send notification to a specific app instance."""
        try:
            # Try Firebase Cloud Messaging (FCM) first
            fcm_token = instance_data.get("fcm_token")
            if fcm_token:
                await self._send_via_fcm(fcm_token, notification)
                return

            # Fallback: Try direct webhook push (if app has registered callback)
            webhook_url = instance_data.get("webhook_url")
            if webhook_url:
                await self._send_via_webhook(webhook_url, notification)
                return

            _LOGGER.warning(
                f"[AppNotificationManager] No valid delivery method for app {app_id}"
            )

        except Exception as e:
            _LOGGER.error(f"[AppNotificationManager] Error sending to app {app_id}: {e}")

    async def _send_via_fcm(self, fcm_token: str, notification: Dict[str, Any]) -> None:
        """Send notification via Firebase Cloud Messaging."""
        try:
            # Get Firebase credentials from integration config
            # This would integrate with your Firebase setup
            # For now, log the intent
            _LOGGER.info(
                f"[AppNotificationManager] Sending FCM notification to token: {fcm_token[:20]}..."
            )

            # TODO: Implement actual FCM sending
            # This requires Firebase Admin SDK integration

        except Exception as e:
            _LOGGER.error(f"[AppNotificationManager] FCM send failed: {e}")

    async def _send_via_webhook(
        self, webhook_url: str, notification: Dict[str, Any]
    ) -> None:
        """Send notification via webhook to app instance."""
        try:
            session = async_get_clientsession(self.hass)

            _LOGGER.debug(
                f"[AppNotificationManager] Sending notification via webhook: {webhook_url}"
            )

            async with session.post(
                webhook_url,
                json=notification,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                if response.status in (200, 201, 204):
                    _LOGGER.info(
                        f"[AppNotificationManager] Notification delivered successfully"
                    )
                else:
                    _LOGGER.warning(
                        f"[AppNotificationManager] Webhook returned status {response.status}"
                    )

        except Exception as e:
            _LOGGER.error(f"[AppNotificationManager] Webhook send failed: {e}")

    async def register_app_instance(
        self,
        app_id: str,
        device_info: Dict[str, Any],
        fcm_token: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ) -> None:
        """Register an app instance for receiving notifications."""
        instance_data = {
            "app_id": app_id,
            "device_info": device_info,
            "fcm_token": fcm_token,
            "webhook_url": webhook_url,
            "registered_at": datetime.now().isoformat(),
        }

        self._registered_devices[app_id] = instance_data
        self.hass.data.setdefault("effortlesshome_app_instances", {})[
            app_id
        ] = instance_data

        _LOGGER.info(f"[AppNotificationManager] Registered app instance: {app_id}")

    async def unregister_app_instance(self, app_id: str) -> None:
        """Unregister an app instance."""
        if app_id in self._registered_devices:
            del self._registered_devices[app_id]

        app_instances = self.hass.data.get("effortlesshome_app_instances", {})
        if app_id in app_instances:
            del app_instances[app_id]

        _LOGGER.info(f"[AppNotificationManager] Unregistered app instance: {app_id}")

    async def get_notifications(
        self, limit: int = 100, category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get stored notifications."""
        notifications = list(self.notifications.values())

        if category:
            notifications = [n for n in notifications if n.get("category") == category]

        # Sort by timestamp descending
        notifications.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        return notifications[:limit]

    async def clear_notification(self, notification_id: str) -> bool:
        """Clear a specific notification."""
        if notification_id in self.notifications:
            del self.notifications[notification_id]
            _LOGGER.info(f"[AppNotificationManager] Cleared notification: {notification_id}")
            return True
        return False

    async def clear_all_notifications(self) -> int:
        """Clear all notifications."""
        count = len(self.notifications)
        self.notifications.clear()
        _LOGGER.info(f"[AppNotificationManager] Cleared all {count} notifications")
        return count


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities=None,
) -> bool:
    """Set up EffortlessHome app notification service."""
    _LOGGER.info("[EffortlessHome] Setting up app notification service")

    # Initialize notification manager
    notification_manager = AppNotificationManager(hass)
    hass.data.setdefault("effortlesshome", {})["notification_manager"] = notification_manager

    # Register webhook for app notifications
    webhook.async_register(
        hass,
        "effortlesshome",
        "App Notification Service",
        WEBHOOK_NOTIFY,
        handle_app_notification_webhook,
    )

    _LOGGER.info("[EffortlessHome] App notification webhook registered")

    # Register service for sending notifications
    async def handle_send_notification(call):
        """Handle the effortlesshome.send_notification service call."""
        _LOGGER.debug(f"send_notification service called with data: {call.data}")

        title = call.data.get("title", "Notification")
        message = call.data.get("message")
        category = call.data.get("category", "automation")
        target = call.data.get("target")
        data = call.data.get("data", {})
        image_url = call.data.get("image_url")

        if not message:
            _LOGGER.warning("No message provided in send_notification call")
            return

        await notification_manager.send_notification(
            title=title,
            message=message,
            category=category,
            target=target,
            data=data,
            image_url=image_url,
        )

    # Register app management service
    async def handle_register_app_instance(call):
        """Handle app instance registration."""
        app_id = call.data.get("app_id")
        device_info = call.data.get("device_info", {})
        fcm_token = call.data.get("fcm_token")
        webhook_url = call.data.get("webhook_url")

        if not app_id:
            _LOGGER.warning("No app_id provided in register_app_instance call")
            return

        await notification_manager.register_app_instance(
            app_id=app_id,
            device_info=device_info,
            fcm_token=fcm_token,
            webhook_url=webhook_url,
        )

    # Register services
    hass.services.async_register(
        "effortlesshome",
        "send_notification",
        handle_send_notification,
    )

    hass.services.async_register(
        "effortlesshome",
        "register_app_instance",
        handle_register_app_instance,
    )

    _LOGGER.info("[EffortlessHome] Notification services registered")

    return True


async def handle_app_notification_webhook(hass: HomeAssistant, webhook_id: str, request):
    """Handle incoming app notification webhook."""
    try:
        data = await request.json()
        _LOGGER.debug(f"[Webhook] Received app notification: {data}")

        # This webhook receives registration updates from the app
        action = data.get("action")
        app_id = data.get("app_id")

        notification_manager = hass.data.get("effortlesshome", {}).get(
            "notification_manager"
        )

        if not notification_manager:
            _LOGGER.error("[Webhook] Notification manager not found")
            return None

        if action == "register":
            # App registering itself for notifications
            await notification_manager.register_app_instance(
                app_id=app_id,
                device_info=data.get("device_info", {}),
                fcm_token=data.get("fcm_token"),
                webhook_url=data.get("webhook_url"),
            )
            return {"status": "registered", "app_id": app_id}

        elif action == "unregister":
            # App unregistering
            await notification_manager.unregister_app_instance(app_id)
            return {"status": "unregistered", "app_id": app_id}

        elif action == "get_notifications":
            # App requesting notifications
            limit = data.get("limit", 100)
            category = data.get("category")
            notifications = await notification_manager.get_notifications(
                limit=limit, category=category
            )
            return {"notifications": notifications}

        elif action == "clear_notification":
            # Clear a specific notification
            notification_id = data.get("notification_id")
            success = await notification_manager.clear_notification(notification_id)
            return {"success": success, "notification_id": notification_id}

        elif action == "clear_all":
            # Clear all notifications
            count = await notification_manager.clear_all_notifications()
            return {"success": True, "cleared_count": count}

        else:
            _LOGGER.warning(f"[Webhook] Unknown action: {action}")
            return {"error": "unknown_action"}

    except Exception as e:
        _LOGGER.error(f"[Webhook] Error handling app notification: {e}")
        return {"error": str(e)}

