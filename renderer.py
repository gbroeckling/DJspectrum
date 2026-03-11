#!/usr/bin/env python3
"""
Display Rendering Engine
=========================
Renders text, clocks, sensor data, scrolling messages, and images
onto a pixel buffer for the Colorlight driver.

Uses Pillow (PIL) for all rendering operations.
"""

import time
import logging
import math
from datetime import datetime
from typing import Optional, Tuple, List, Dict, Any

import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert '#RRGGBB' to (R, G, B) tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


class DisplayRenderer:
    """
    Renders various content types onto a pixel buffer.

    All rendering produces a numpy array of shape (height, width, 3)
    dtype uint8 in RGB format, ready for the Colorlight driver.
    """

    def __init__(self, width: int = 344, height: int = 86, config: dict = None):
        self.width = width
        self.height = height
        self.config = config or {}

        # Load fonts
        font_config = self.config.get("fonts", {})
        default_path = font_config.get(
            "default", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        )
        mono_path = font_config.get(
            "mono", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
        )

        self._font_cache: Dict[str, ImageFont.FreeTypeFont] = {}
        self._default_font_path = default_path
        self._mono_font_path = mono_path

        # Scrolling state
        self._scroll_offset = 0
        self._scroll_text_width = 0

        # Animation state
        self._frame_count = 0

        logger.info(f"Renderer initialized: {width}x{height}")

    def _get_font(self, path: str, size: int) -> ImageFont.FreeTypeFont:
        """Get a cached font instance."""
        key = f"{path}:{size}"
        if key not in self._font_cache:
            try:
                self._font_cache[key] = ImageFont.truetype(path, size)
            except (OSError, IOError):
                logger.warning(f"Font not found: {path}, using default")
                self._font_cache[key] = ImageFont.load_default()
        return self._font_cache[key]

    def _new_image(self, bg_color: str = "#000000") -> Tuple[Image.Image, ImageDraw.Draw]:
        """Create a new blank image and draw context."""
        img = Image.new("RGB", (self.width, self.height), hex_to_rgb(bg_color))
        draw = ImageDraw.Draw(img)
        return img, draw

    def _image_to_array(self, img: Image.Image) -> np.ndarray:
        """Convert PIL Image to numpy RGB array."""
        return np.array(img, dtype=np.uint8)

    # ── Static Text ────────────────────────────────────────

    def render_text(
        self,
        text: str,
        font_size: int = 20,
        color: str = "#FFFFFF",
        bg_color: str = "#000000",
        align: str = "center",
        y_offset: int = 0,
    ) -> np.ndarray:
        """
        Render static text centered on the display.

        Args:
            text: Text string to display
            font_size: Font size in pixels
            color: Text color as '#RRGGBB'
            bg_color: Background color as '#RRGGBB'
            align: 'left', 'center', or 'right'
            y_offset: Vertical offset in pixels

        Returns:
            numpy array (height, width, 3) uint8
        """
        img, draw = self._new_image(bg_color)
        font = self._get_font(self._default_font_path, font_size)

        # Get text bounding box
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # Calculate position
        if align == "center":
            x = (self.width - text_w) // 2
        elif align == "right":
            x = self.width - text_w - 4
        else:
            x = 4

        y = (self.height - text_h) // 2 + y_offset

        draw.text((x, y), text, fill=hex_to_rgb(color), font=font)
        return self._image_to_array(img)

    # ── Multi-line Text ────────────────────────────────────

    def render_multiline(
        self,
        lines: List[str],
        font_size: int = 16,
        color: str = "#FFFFFF",
        bg_color: str = "#000000",
        line_spacing: int = 4,
    ) -> np.ndarray:
        """Render multiple lines of text, vertically centered."""
        img, draw = self._new_image(bg_color)
        font = self._get_font(self._default_font_path, font_size)

        # Calculate total text height
        line_heights = []
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            line_heights.append(bbox[3] - bbox[1])

        total_h = sum(line_heights) + line_spacing * (len(lines) - 1)
        y = (self.height - total_h) // 2

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            x = (self.width - text_w) // 2
            draw.text((x, y), line, fill=hex_to_rgb(color), font=font)
            y += line_heights[i] + line_spacing

        return self._image_to_array(img)

    # ── Clock ──────────────────────────────────────────────

    def render_clock(
        self,
        fmt: str = "%H:%M:%S",
        font_size: int = 32,
        color: str = "#FFFFFF",
        bg_color: str = "#000000",
        show_date: bool = True,
        date_font_size: int = 14,
        date_color: str = "#888888",
    ) -> np.ndarray:
        """Render current time (and optionally date)."""
        now = datetime.now()
        img, draw = self._new_image(bg_color)

        # Time
        time_str = now.strftime(fmt)
        time_font = self._get_font(self._mono_font_path, font_size)
        bbox = draw.textbbox((0, 0), time_str, font=time_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]

        if show_date:
            # Date below time
            date_str = now.strftime("%a %b %d, %Y")
            date_font = self._get_font(self._default_font_path, date_font_size)
            dbbox = draw.textbbox((0, 0), date_str, font=date_font)
            dw = dbbox[2] - dbbox[0]
            dh = dbbox[3] - dbbox[1]

            total_h = th + 6 + dh
            ty = (self.height - total_h) // 2
            tx = (self.width - tw) // 2
            dy = ty + th + 6
            dx = (self.width - dw) // 2

            draw.text((tx, ty), time_str, fill=hex_to_rgb(color), font=time_font)
            draw.text((dx, dy), date_str, fill=hex_to_rgb(date_color), font=date_font)
        else:
            ty = (self.height - th) // 2
            tx = (self.width - tw) // 2
            draw.text((tx, ty), time_str, fill=hex_to_rgb(color), font=time_font)

        return self._image_to_array(img)

    # ── Scrolling Text ─────────────────────────────────────

    def render_scroll(
        self,
        text: str,
        speed: int = 2,
        font_size: int = 24,
        color: str = "#FFFF00",
        bg_color: str = "#000000",
    ) -> np.ndarray:
        """
        Render one frame of scrolling text (call repeatedly for animation).

        Args:
            text: Text to scroll
            speed: Pixels to advance per frame
            font_size: Font size
            color: Text color
            bg_color: Background color

        Returns:
            numpy array (height, width, 3) for this frame
        """
        font = self._get_font(self._default_font_path, font_size)

        # Measure text width (on first call or if text changes)
        temp_img = Image.new("RGB", (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        self._scroll_text_width = bbox[2] - bbox[0]

        # Create wide canvas for the full text
        canvas_w = self._scroll_text_width + self.width * 2
        canvas = Image.new("RGB", (canvas_w, self.height), hex_to_rgb(bg_color))
        canvas_draw = ImageDraw.Draw(canvas)

        # Draw text starting at width (so it scrolls in from the right)
        text_y = (self.height - (bbox[3] - bbox[1])) // 2
        canvas_draw.text(
            (self.width, text_y), text,
            fill=hex_to_rgb(color), font=font
        )

        # Crop the visible window at the current scroll offset
        x_start = self._scroll_offset % canvas_w
        if x_start + self.width <= canvas_w:
            visible = canvas.crop((x_start, 0, x_start + self.width, self.height))
        else:
            # Wrap around
            left = canvas.crop((x_start, 0, canvas_w, self.height))
            right = canvas.crop((0, 0, self.width - left.width, self.height))
            visible = Image.new("RGB", (self.width, self.height), hex_to_rgb(bg_color))
            visible.paste(left, (0, 0))
            visible.paste(right, (left.width, 0))

        # Advance scroll position
        self._scroll_offset += speed
        if self._scroll_offset >= canvas_w:
            self._scroll_offset = 0

        return self._image_to_array(visible)

    def reset_scroll(self):
        """Reset scroll position to the beginning."""
        self._scroll_offset = 0

    # ── Sensor Dashboard ───────────────────────────────────

    def render_sensors(
        self,
        sensors: Dict[str, Any],
        font_size: int = 16,
        label_color: str = "#888888",
        value_color: str = "#00FFFF",
        bg_color: str = "#000000",
    ) -> np.ndarray:
        """
        Render sensor data in a dashboard layout.

        Args:
            sensors: Dict of {"Label": "Value"} pairs
                     e.g. {"Temp": "22.3°C", "Humidity": "45%", "CO2": "412ppm"}
            font_size: Font size for values
            label_color: Color for labels
            value_color: Color for values
            bg_color: Background color

        Returns:
            numpy array (height, width, 3)
        """
        img, draw = self._new_image(bg_color)
        font = self._get_font(self._default_font_path, font_size)
        small_font = self._get_font(self._default_font_path, max(10, font_size - 4))

        items = list(sensors.items())
        if not items:
            return self._image_to_array(img)

        # Calculate grid layout
        cols = min(len(items), 4)  # Max 4 columns
        rows = math.ceil(len(items) / cols)
        cell_w = self.width // cols
        cell_h = self.height // rows

        for idx, (label, value) in enumerate(items):
            col = idx % cols
            row = idx // cols
            cx = col * cell_w + cell_w // 2
            cy = row * cell_h

            # Draw label (small, above)
            lbbox = draw.textbbox((0, 0), str(label), font=small_font)
            lw = lbbox[2] - lbbox[0]
            draw.text(
                (cx - lw // 2, cy + 2),
                str(label),
                fill=hex_to_rgb(label_color),
                font=small_font,
            )

            # Draw value (large, below label)
            vbbox = draw.textbbox((0, 0), str(value), font=font)
            vw = vbbox[2] - vbbox[0]
            label_h = lbbox[3] - lbbox[1]
            draw.text(
                (cx - vw // 2, cy + label_h + 4),
                str(value),
                fill=hex_to_rgb(value_color),
                font=font,
            )

        return self._image_to_array(img)

    # ── Image Display ──────────────────────────────────────

    def render_image(self, image_path: str) -> np.ndarray:
        """
        Load and display an image file, scaled to fit the display.

        Args:
            image_path: Path to image file (PNG, JPG, BMP, GIF)

        Returns:
            numpy array (height, width, 3)
        """
        try:
            img = Image.open(image_path).convert("RGB")
            img = img.resize((self.width, self.height), Image.LANCZOS)
            return self._image_to_array(img)
        except Exception as e:
            logger.error(f"Failed to load image {image_path}: {e}")
            return self.render_text(f"IMG ERR", color="#FF0000")

    # ── Solid Color / Off ──────────────────────────────────

    def render_solid(self, color: str = "#000000") -> np.ndarray:
        """Render a solid color (use '#000000' for off)."""
        img, _ = self._new_image(color)
        return self._image_to_array(img)

    # ── Alert / Flash ──────────────────────────────────────

    def render_alert(
        self,
        text: str,
        color: str = "#FF0000",
        bg_color: str = "#000000",
        font_size: int = 28,
    ) -> np.ndarray:
        """
        Render an alert message with a flashing border effect.
        Call repeatedly for animation.
        """
        self._frame_count += 1
        flash = (self._frame_count // 8) % 2 == 0  # Toggle every 8 frames

        if flash:
            actual_bg = bg_color
            border_color = hex_to_rgb(color)
        else:
            actual_bg = "#000000"
            border_color = hex_to_rgb("#330000")

        img, draw = self._new_image(actual_bg)

        # Draw border
        for i in range(3):
            draw.rectangle(
                [i, i, self.width - 1 - i, self.height - 1 - i],
                outline=border_color,
            )

        # Draw text
        font = self._get_font(self._default_font_path, font_size)
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        x = (self.width - tw) // 2
        y = (self.height - th) // 2
        draw.text((x, y), text, fill=hex_to_rgb(color), font=font)

        return self._image_to_array(img)

    # ── Progress Bar ───────────────────────────────────────

    def render_progress(
        self,
        label: str,
        value: float,
        max_value: float = 100.0,
        color: str = "#00FF00",
        bg_color: str = "#000000",
        bar_color: str = "#003300",
        font_size: int = 18,
    ) -> np.ndarray:
        """Render a progress bar with label and percentage."""
        img, draw = self._new_image(bg_color)
        font = self._get_font(self._default_font_path, font_size)

        pct = min(1.0, max(0.0, value / max_value))
        pct_text = f"{label}: {pct * 100:.0f}%"

        # Draw label
        bbox = draw.textbbox((0, 0), pct_text, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text(
            ((self.width - tw) // 2, 4),
            pct_text,
            fill=hex_to_rgb(color),
            font=font,
        )

        # Draw bar background
        bar_y = th + 12
        bar_h = self.height - bar_y - 8
        bar_x = 8
        bar_w = self.width - 16
        draw.rectangle(
            [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
            fill=hex_to_rgb(bar_color),
        )

        # Draw bar fill
        fill_w = int(bar_w * pct)
        if fill_w > 0:
            draw.rectangle(
                [bar_x, bar_y, bar_x + fill_w, bar_y + bar_h],
                fill=hex_to_rgb(color),
            )

        return self._image_to_array(img)


# ── Quick visual test ──────────────────────────────────────
if __name__ == "__main__":
    renderer = DisplayRenderer(width=344, height=86)

    # Test each render mode and save as image
    tests = {
        "test_text.png": renderer.render_text("Hello LED Panel!", font_size=24),
        "test_clock.png": renderer.render_clock(),
        "test_sensors.png": renderer.render_sensors({
            "Temp": "22.3°C",
            "Humidity": "45%",
            "CO2": "412ppm",
            "Light": "340lx",
        }),
        "test_alert.png": renderer.render_alert("DOOR OPEN!", font_size=26),
        "test_progress.png": renderer.render_progress("CPU", 73.5),
    }

    for filename, pixels in tests.items():
        img = Image.fromarray(pixels)
        img.save(filename)
        print(f"Saved {filename} ({pixels.shape})")
