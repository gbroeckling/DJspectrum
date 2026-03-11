#!/usr/bin/env python3
"""
Home Assistant MQTT Bridge
===========================
Connects to Home Assistant via MQTT and translates HA commands
into display actions. Supports MQTT auto-discovery so the panel
appears as a native HA entity.

MQTT Topics:
  ledpanel/command         - JSON command to change display mode
  ledpanel/brightness/set  - Set brightness (0-255)
  ledpanel/state           - Current state (published by us)
  ledpanel/available       - Online/offline availability

Command JSON format:
  {"mode": "text", "text": "Hello!", "color": "#FF0000", "font_size": 20}
  {"mode": "clock"}
  {"mode": "scroll", "text": "Breaking news...", "speed": 3}
  {"mode": "sensors", "data": {"Temp": "22°C", "Humidity": "45%"}}
  {"mode": "alert", "text": "ALARM!", "color": "#FF0000"}
  {"mode": "image", "path": "/path/to/image.png"}
  {"mode": "progress", "label": "Download", "value": 65}
  {"mode": "off"}
"""

import json
import logging
import threading
from typing import Callable, Optional, Dict, Any

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


class HAMQTTBridge:
    """
    MQTT bridge between Home Assistant and the LED panel.

    Subscribes to command topics and calls back to the main app
    when display changes are requested. Publishes state and
    supports HA MQTT auto-discovery.
    """

    def __init__(
        self,
        broker: str = "192.168.1.100",
        port: int = 1883,
        username: str = "",
        password: str = "",
        topic_prefix: str = "ledpanel",
        discovery_prefix: str = "homeassistant",
        on_command: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_brightness: Optional[Callable[[int], None]] = None,
    ):
        self.broker = broker
        self.port = port
        self.topic_prefix = topic_prefix
        self.discovery_prefix = discovery_prefix
        self.on_command = on_command
        self.on_brightness = on_brightness

        # MQTT topics
        self.topic_command = f"{topic_prefix}/command"
        self.topic_brightness_set = f"{topic_prefix}/brightness/set"
        self.topic_brightness_state = f"{topic_prefix}/brightness/state"
        self.topic_state = f"{topic_prefix}/state"
        self.topic_available = f"{topic_prefix}/available"

        # MQTT client
        self.client = mqtt.Client(
            client_id=f"ledpanel_{topic_prefix}",
            protocol=mqtt.MQTTv311,
        )
        self.client.username_pw_set(username, password)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

        # Last will (offline when disconnected)
        self.client.will_set(self.topic_available, "offline", qos=1, retain=True)

        self._connected = False

    def connect(self):
        """Connect to MQTT broker (non-blocking)."""
        try:
            logger.info(f"Connecting to MQTT broker {self.broker}:{self.port}")
            self.client.connect_async(self.broker, self.port, keepalive=60)
            self.client.loop_start()
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            raise

    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.publish_state({"mode": "off"})
        self.client.publish(self.topic_available, "offline", qos=1, retain=True)
        self.client.loop_stop()
        self.client.disconnect()
        logger.info("MQTT disconnected")

    def _on_connect(self, client, userdata, flags, rc):
        """Called when connected to MQTT broker."""
        if rc == 0:
            logger.info("MQTT connected successfully")
            self._connected = True

            # Subscribe to command topics
            client.subscribe(self.topic_command, qos=1)
            client.subscribe(self.topic_brightness_set, qos=1)
            logger.info(f"Subscribed to {self.topic_command}")
            logger.info(f"Subscribed to {self.topic_brightness_set}")

            # Publish online status
            client.publish(self.topic_available, "online", qos=1, retain=True)

            # Publish HA MQTT auto-discovery configs
            self._publish_discovery()
        else:
            logger.error(f"MQTT connection failed with code {rc}")

    def _on_disconnect(self, client, userdata, rc):
        """Called when disconnected from MQTT broker."""
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect (rc={rc}), will reconnect")

    def _on_message(self, client, userdata, msg):
        """Called when a message is received on a subscribed topic."""
        topic = msg.topic
        payload = msg.payload.decode("utf-8", errors="replace")

        logger.debug(f"MQTT message: {topic} = {payload}")

        try:
            if topic == self.topic_command:
                command = json.loads(payload)
                logger.info(f"Command received: {command.get('mode', 'unknown')}")
                if self.on_command:
                    self.on_command(command)

            elif topic == self.topic_brightness_set:
                brightness = int(payload)
                brightness = max(0, min(255, brightness))
                logger.info(f"Brightness command: {brightness}")
                if self.on_brightness:
                    self.on_brightness(brightness)
                # Echo back the brightness state
                client.publish(
                    self.topic_brightness_state,
                    str(brightness),
                    qos=1,
                    retain=True,
                )

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON on {topic}: {e}")
        except ValueError as e:
            logger.error(f"Invalid value on {topic}: {e}")

    def publish_state(self, state: Dict[str, Any]):
        """Publish current display state to HA."""
        if self._connected:
            self.client.publish(
                self.topic_state,
                json.dumps(state),
                qos=1,
                retain=True,
            )

    def _publish_discovery(self):
        """Publish MQTT auto-discovery configs so HA creates entities automatically."""
        device_info = {
            "identifiers": [f"ledpanel_{self.topic_prefix}"],
            "name": "LED Matrix Panel",
            "model": "Colorlight 5A-75B + P1.86",
            "manufacturer": "DIY",
            "sw_version": "1.0.0",
        }

        # -- Light entity (for brightness + on/off) --
        light_config = {
            "name": "LED Panel",
            "unique_id": f"ledpanel_{self.topic_prefix}_light",
            "command_topic": self.topic_command,
            "brightness_command_topic": self.topic_brightness_set,
            "brightness_state_topic": self.topic_brightness_state,
            "state_topic": self.topic_state,
            "availability_topic": self.topic_available,
            "payload_on": '{"mode": "clock"}',
            "payload_off": '{"mode": "off"}',
            "brightness_scale": 255,
            "device": device_info,
            "icon": "mdi:led-strip-variant",
        }
        self.client.publish(
            f"{self.discovery_prefix}/light/{self.topic_prefix}/config",
            json.dumps(light_config),
            qos=1,
            retain=True,
        )

        # -- Text sensor (shows current mode) --
        sensor_config = {
            "name": "LED Panel Mode",
            "unique_id": f"ledpanel_{self.topic_prefix}_mode",
            "state_topic": self.topic_state,
            "value_template": "{{ value_json.mode }}",
            "availability_topic": self.topic_available,
            "device": device_info,
            "icon": "mdi:monitor",
            "entity_category": "diagnostic",
        }
        self.client.publish(
            f"{self.discovery_prefix}/sensor/{self.topic_prefix}_mode/config",
            json.dumps(sensor_config),
            qos=1,
            retain=True,
        )

        # -- Number entity (brightness slider) --
        number_config = {
            "name": "LED Panel Brightness",
            "unique_id": f"ledpanel_{self.topic_prefix}_brightness",
            "command_topic": self.topic_brightness_set,
            "state_topic": self.topic_brightness_state,
            "availability_topic": self.topic_available,
            "min": 0,
            "max": 255,
            "step": 1,
            "device": device_info,
            "icon": "mdi:brightness-6",
        }
        self.client.publish(
            f"{self.discovery_prefix}/number/{self.topic_prefix}_brightness/config",
            json.dumps(number_config),
            qos=1,
            retain=True,
        )

        logger.info("HA MQTT auto-discovery configs published")


# ── Quick test ─────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)

    def on_cmd(cmd):
        print(f"Command: {cmd}")

    def on_bright(val):
        print(f"Brightness: {val}")

    bridge = HAMQTTBridge(
        broker="192.168.1.100",
        port=1883,
        username="mqtt_user",
        password="mqtt_pass",
        on_command=on_cmd,
        on_brightness=on_bright,
    )
    bridge.connect()

    print("MQTT bridge running. Press Ctrl+C to stop.")
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        bridge.disconnect()
