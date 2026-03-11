#!/usr/bin/env python3
"""
LED Panel Controller - Main Application
=========================================
Ties together the Colorlight driver, display renderer, and
Home Assistant MQTT bridge into a single application.

Usage:
    sudo python3 main.py                    # Run with default config
    sudo python3 main.py --config my.yaml   # Custom config file
    sudo python3 main.py --test             # Run test pattern only

Architecture:
    MQTT commands from HA
           │
           ▼
    ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐
    │ MQTT Bridge │───►│   Renderer   │───►│ Colorlight 5A75B│──► Panels
    │ (mqtt_bridge│    │  (renderer)  │    │  (colorlight)   │
    └─────────────┘    └──────────────┘    └─────────────────┘
           │                                        ▲
           └── brightness ──────────────────────────┘
"""

import argparse
import logging
import signal
import sys
import time
import threading
from pathlib import Path
from typing import Dict, Any

import yaml

from colorlight import Colorlight5A75B
from renderer import DisplayRenderer
from mqtt_bridge import HAMQTTBridge

# ── Logging ────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ledpanel")


class LEDPanelApp:
    """Main application controller."""

    def __init__(self, config_path: str = "config.yaml"):
        # Load config
        self.config = self._load_config(config_path)
        display_cfg = self.config.get("display", {})
        cl_cfg = self.config.get("colorlight", {})
        mqtt_cfg = self.config.get("mqtt", {})

        # Calculate total display resolution
        panel_w = display_cfg.get("panel_width", 172)
        panel_h = display_cfg.get("panel_height", 86)
        chain = display_cfg.get("chain_length", 2)
        layout = display_cfg.get("layout", "horizontal")

        if layout == "horizontal":
            self.width = panel_w * chain
            self.height = panel_h
        else:  # vertical / stacked
            self.width = panel_w
            self.height = panel_h * chain

        logger.info(f"Display resolution: {self.width}x{self.height}")

        # Initialize components
        self.driver = Colorlight5A75B(
            interface=cl_cfg.get("interface", "eth0"),
            width=self.width,
            height=self.height,
            dst_mac=cl_cfg.get("dst_mac", "11:22:33:44:55:66"),
            src_mac=cl_cfg.get("src_mac", "22:22:33:44:55:66"),
            gamma=cl_cfg.get("gamma", 2.2),
        )

        self.renderer = DisplayRenderer(
            width=self.width,
            height=self.height,
            config=self.config,
        )

        self.mqtt = HAMQTTBridge(
            broker=mqtt_cfg.get("broker", "192.168.1.100"),
            port=mqtt_cfg.get("port", 1883),
            username=mqtt_cfg.get("username", ""),
            password=mqtt_cfg.get("password", ""),
            topic_prefix=mqtt_cfg.get("topic_prefix", "ledpanel"),
            discovery_prefix=mqtt_cfg.get("ha_discovery_prefix", "homeassistant"),
            on_command=self._handle_command,
            on_brightness=self._handle_brightness,
        )

        # State
        self._current_mode = "clock"  # Default mode
        self._current_params: Dict[str, Any] = {}
        self._running = False
        self._lock = threading.Lock()
        self._target_fps = cl_cfg.get("fps", 30)
        self._frame_time = 1.0 / self._target_fps

    def _load_config(self, path: str) -> dict:
        """Load YAML config file."""
        config_path = Path(path)
        if not config_path.exists():
            logger.warning(f"Config not found at {path}, using defaults")
            return {}
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        logger.info(f"Config loaded from {path}")
        return config

    def _handle_command(self, command: Dict[str, Any]):
        """Handle incoming MQTT command."""
        with self._lock:
            mode = command.get("mode", "text")
            self._current_mode = mode
            self._current_params = command
            self.renderer.reset_scroll()
            self.renderer._frame_count = 0

            logger.info(f"Mode changed to: {mode}")

            # Publish state back to HA
            self.mqtt.publish_state({"mode": mode, **command})

    def _handle_brightness(self, brightness: int):
        """Handle brightness change from MQTT."""
        try:
            self.driver.set_brightness(brightness)
            logger.info(f"Brightness set to {brightness}")
        except Exception as e:
            logger.error(f"Failed to set brightness: {e}")

    def _render_frame(self) -> Any:
        """Render one frame based on current mode."""
        with self._lock:
            mode = self._current_mode
            params = self._current_params.copy()

        try:
            if mode == "off":
                return self.renderer.render_solid("#000000")

            elif mode == "text":
                return self.renderer.render_text(
                    text=params.get("text", ""),
                    font_size=params.get("font_size", 20),
                    color=params.get("color", "#FFFFFF"),
                    bg_color=params.get("bg_color", "#000000"),
                    align=params.get("align", "center"),
                )

            elif mode == "multiline":
                return self.renderer.render_multiline(
                    lines=params.get("lines", [""]),
                    font_size=params.get("font_size", 16),
                    color=params.get("color", "#FFFFFF"),
                    bg_color=params.get("bg_color", "#000000"),
                )

            elif mode == "clock":
                return self.renderer.render_clock(
                    fmt=params.get("format", "%H:%M:%S"),
                    font_size=params.get("font_size", 32),
                    color=params.get("color", "#FFFFFF"),
                    bg_color=params.get("bg_color", "#000000"),
                    show_date=params.get("show_date", True),
                    date_font_size=params.get("date_font_size", 14),
                )

            elif mode == "scroll":
                return self.renderer.render_scroll(
                    text=params.get("text", ""),
                    speed=params.get("speed", 2),
                    font_size=params.get("font_size", 24),
                    color=params.get("color", "#FFFF00"),
                    bg_color=params.get("bg_color", "#000000"),
                )

            elif mode == "sensors":
                return self.renderer.render_sensors(
                    sensors=params.get("data", {}),
                    font_size=params.get("font_size", 16),
                    label_color=params.get("label_color", "#888888"),
                    value_color=params.get("value_color", "#00FFFF"),
                    bg_color=params.get("bg_color", "#000000"),
                )

            elif mode == "alert":
                return self.renderer.render_alert(
                    text=params.get("text", "ALERT"),
                    color=params.get("color", "#FF0000"),
                    bg_color=params.get("bg_color", "#000000"),
                    font_size=params.get("font_size", 28),
                )

            elif mode == "image":
                return self.renderer.render_image(
                    image_path=params.get("path", ""),
                )

            elif mode == "progress":
                return self.renderer.render_progress(
                    label=params.get("label", "Progress"),
                    value=params.get("value", 0),
                    max_value=params.get("max_value", 100),
                    color=params.get("color", "#00FF00"),
                    bg_color=params.get("bg_color", "#000000"),
                )

            else:
                return self.renderer.render_text(
                    f"Unknown: {mode}", color="#FF0000"
                )

        except Exception as e:
            logger.error(f"Render error in mode '{mode}': {e}")
            return self.renderer.render_text("RENDER ERR", color="#FF0000")

    def run(self):
        """Main application loop."""
        logger.info("Starting LED Panel Controller")

        # Open Colorlight driver
        self.driver.open()
        self.driver.set_brightness(
            self.config.get("colorlight", {}).get("brightness", 128)
        )

        # Connect MQTT
        try:
            self.mqtt.connect()
        except Exception as e:
            logger.warning(f"MQTT connection failed: {e} (display will still work)")

        # Set startup mode
        startup = self.config.get("modes", {}).get("startup", {})
        if startup:
            self._current_mode = startup.get("type", "text")
            self._current_params = startup

        self._running = True
        logger.info(f"Running at {self._target_fps} FPS")

        try:
            while self._running:
                t_start = time.monotonic()

                # Render and send frame
                frame = self._render_frame()
                self.driver.send_frame(frame)

                # Frame rate limiting
                elapsed = time.monotonic() - t_start
                sleep_time = self._frame_time - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()

    def run_test(self):
        """Run test pattern mode."""
        logger.info("Running test pattern (Ctrl+C to stop)")
        self.driver.open()
        self.driver.set_brightness(128)

        try:
            while True:
                self.driver.send_test_pattern()
                time.sleep(1.0 / 30)
        except KeyboardInterrupt:
            pass
        finally:
            self.driver.clear()
            self.driver.close()

    def stop(self):
        """Clean shutdown."""
        self._running = False
        logger.info("Shutting down...")

        try:
            self.mqtt.disconnect()
        except Exception:
            pass

        try:
            self.driver.clear()
            self.driver.close()
        except Exception:
            pass

        logger.info("Shutdown complete")


# ── Entry Point ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="LED Panel Controller - Colorlight 5A-75B"
    )
    parser.add_argument(
        "--config", "-c",
        default="config.yaml",
        help="Path to config file (default: config.yaml)",
    )
    parser.add_argument(
        "--test", "-t",
        action="store_true",
        help="Run test pattern only (no MQTT)",
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    app = LEDPanelApp(config_path=args.config)

    # Handle signals for clean shutdown
    def signal_handler(sig, frame):
        logger.info(f"Signal {sig} received")
        app.stop()
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    if args.test:
        app.run_test()
    else:
        app.run()


if __name__ == "__main__":
    main()
