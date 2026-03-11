#!/usr/bin/env python3
"""
Colorlight 5A-75B Raw Ethernet Protocol Driver
================================================
Sends pixel data to a Colorlight 5A-75B LED receiving card over
raw Layer 2 Ethernet frames. Protocol based on reverse-engineering
by the FPP/Falcon Player community and Harald Kubota.

Requires: Linux with raw socket support (sudo or CAP_NET_RAW)
Requires: Gigabit Ethernet connection to the 5A-75B

Protocol reference:
  - FPP: github.com/FalconChristmas/fpp (ColorLight-5a-75.cpp)
  - Harald Kubota: hkubota.wordpress.com/2022/01/31/winter-project-colorlight-5a-75b-protocol/
"""

import socket
import struct
import time
import logging
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class ColorlightError(Exception):
    """Colorlight driver error."""
    pass


class Colorlight5A75B:
    """
    Driver for Colorlight 5A-75B LED receiving card.

    Sends pixel data as raw Ethernet frames using the reverse-engineered
    Colorlight protocol. The 5A-75B handles all HUB75 scanning internally.

    Usage:
        driver = Colorlight5A75B(interface='eth0', width=344, height=86)
        driver.open()
        driver.set_brightness(128)
        driver.send_frame(rgb_array)  # numpy array shape (height, width, 3)
        driver.close()
    """

    # -- Protocol Constants --
    ETHERTYPE_DATA = 0x5500       # Pixel row data
    ETHERTYPE_BRIGHTNESS = 0x0A00 # Brightness control
    ETHERTYPE_CONFIG = 0x0107     # Display configuration

    # Maximum pixels per Ethernet frame (MTU 1500 - 14 eth header - 8 protocol header)
    MAX_PIXELS_PER_FRAME = 497    # floor((1500 - 14 - 8) / 3)

    def __init__(
        self,
        interface: str = "eth0",
        width: int = 344,
        height: int = 86,
        dst_mac: str = "11:22:33:44:55:66",
        src_mac: str = "22:22:33:44:55:66",
        gamma: float = 2.2,
    ):
        self.interface = interface
        self.width = width
        self.height = height
        self.dst_mac = bytes.fromhex(dst_mac.replace(":", ""))
        self.src_mac = bytes.fromhex(src_mac.replace(":", ""))
        self.gamma = gamma
        self.sock: Optional[socket.socket] = None
        self._brightness = 255

        # Pre-build gamma lookup table (0-255 -> 0-255 corrected)
        self._gamma_lut = np.array([
            int(pow(i / 255.0, gamma) * 255.0 + 0.5)
            for i in range(256)
        ], dtype=np.uint8)

        # Pre-build Ethernet headers for data frames
        self._data_eth_header = (
            self.dst_mac +
            self.src_mac +
            struct.pack(">H", self.ETHERTYPE_DATA)
        )

        # Pre-build brightness Ethernet header
        self._brightness_eth_header = (
            self.dst_mac +
            self.src_mac +
            struct.pack(">H", self.ETHERTYPE_BRIGHTNESS)
        )

        logger.info(
            f"Colorlight driver initialized: {width}x{height} on {interface}"
        )

    def open(self):
        """Open raw socket for sending Ethernet frames."""
        try:
            # AF_PACKET = raw Ethernet, SOCK_RAW = include headers
            self.sock = socket.socket(
                socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003)
            )
            self.sock.bind((self.interface, 0))
            logger.info(f"Raw socket opened on {self.interface}")
        except PermissionError:
            raise ColorlightError(
                "Raw socket requires root. Run with: sudo python3 main.py\n"
                "Or set capability: sudo setcap cap_net_raw+ep $(which python3)"
            )
        except OSError as e:
            raise ColorlightError(
                f"Cannot open socket on {self.interface}: {e}\n"
                f"Check: ip link show {self.interface}"
            )

    def close(self):
        """Close the raw socket."""
        if self.sock:
            self.sock.close()
            self.sock = None
            logger.info("Socket closed")

    def _send_raw(self, frame: bytes):
        """Send a raw Ethernet frame."""
        if not self.sock:
            raise ColorlightError("Socket not open. Call open() first.")
        try:
            self.sock.send(frame)
        except OSError as e:
            logger.error(f"Send failed: {e}")
            raise

    def set_brightness(self, brightness: int):
        """
        Set display brightness (0-255).

        Sends a brightness control frame to the 5A-75B.
        """
        brightness = max(0, min(255, brightness))
        self._brightness = brightness

        # Brightness frame payload (padded to minimum Ethernet size)
        # Offset 0: 0x00 0x00 0x00
        # Offset 3: brightness value
        # Rest: padding
        payload = bytearray(64)
        payload[0] = 0x00
        payload[1] = 0x00
        payload[2] = 0x00
        payload[3] = brightness & 0xFF
        payload[4] = 0x05
        payload[5] = 0xA0

        frame = self._brightness_eth_header + bytes(payload)
        self._send_raw(frame)
        logger.debug(f"Brightness set to {brightness}")

    def send_frame(self, pixels: np.ndarray):
        """
        Send a complete display frame to the 5A-75B.

        Args:
            pixels: numpy array of shape (height, width, 3) dtype uint8, RGB format
        """
        if pixels.shape != (self.height, self.width, 3):
            raise ColorlightError(
                f"Frame shape {pixels.shape} != expected "
                f"({self.height}, {self.width}, 3)"
            )

        # Apply gamma correction
        corrected = self._gamma_lut[pixels]

        # Send each row as one or more Ethernet frames
        for row in range(self.height):
            row_data = corrected[row]  # shape (width, 3)
            self._send_row(row, row_data)

    def _send_row(self, row: int, row_pixels: np.ndarray):
        """
        Send one row of pixel data, splitting into multiple frames if needed.

        Args:
            row: Row number (0-based)
            row_pixels: numpy array shape (width, 3) dtype uint8
        """
        width = row_pixels.shape[0]
        col_offset = 0

        while col_offset < width:
            # Calculate how many pixels fit in this frame
            remaining = width - col_offset
            count = min(remaining, self.MAX_PIXELS_PER_FRAME)

            # Extract pixel slice and convert to bytes
            pixel_slice = row_pixels[col_offset:col_offset + count]
            rgb_bytes = pixel_slice.tobytes()

            # Build protocol header (8 bytes)
            # Bytes 0-1: row number (uint16 big-endian)
            # Bytes 2-3: column offset (uint16 big-endian)
            # Bytes 4-5: pixel count (uint16 big-endian)
            # Byte 6: 0x08 (flags)
            # Byte 7: 0x88 (flags)
            header = struct.pack(">HHH", row, col_offset, count)
            header += b'\x08\x88'

            # Build complete Ethernet frame
            frame = self._data_eth_header + header + rgb_bytes

            # Pad to minimum Ethernet frame size (60 bytes + 4 CRC = 64)
            if len(frame) < 60:
                frame += b'\x00' * (60 - len(frame))

            self._send_raw(frame)
            col_offset += count

    def send_test_pattern(self):
        """Send a color gradient test pattern to verify connectivity."""
        pixels = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        for x in range(self.width):
            r = int((x / self.width) * 255)
            for y in range(self.height):
                g = int((y / self.height) * 255)
                b = 128
                pixels[y, x] = [r, g, b]

        self.send_frame(pixels)
        logger.info("Test pattern sent")

    def clear(self):
        """Clear the display (all black)."""
        pixels = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        self.send_frame(pixels)
        logger.debug("Display cleared")

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *args):
        self.clear()
        self.close()


# ── Quick self-test ────────────────────────────────────────
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)

    iface = sys.argv[1] if len(sys.argv) > 1 else "eth0"
    print(f"Sending test pattern on {iface}...")
    print("Press Ctrl+C to stop\n")

    with Colorlight5A75B(interface=iface, width=344, height=86) as cl:
        cl.set_brightness(128)
        try:
            while True:
                cl.send_test_pattern()
                time.sleep(1.0 / 30)  # ~30 FPS
        except KeyboardInterrupt:
            print("\nStopped.")
