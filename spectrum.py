#!/usr/bin/env python3
"""
Audio Spectrum Analyzer Engine
================================
Faithful port of the ESP32-S3 ESPHome spectrum analyzer
(gbroeckling/Spectrum) to Raspberry Pi + PyAudio.

The ESP32 version uses:
  - INMP441 I2S mic → 512-sample FFT → 64 bars on 128x64
  - Per-bar slow AGC (4-minute tau), noise floor tracking
  - 10-minute windowed max, balance tilt, output shaping
  - Peak hold with slow gravity decay

This version:
  - USB/ALSA mic → PyAudio → numpy FFT → 172 bars on 344x86
  - Same per-bar AGC, noise, tilt, and shaping algorithms
  - Same peak dot behavior and bar attack/release

Architecture:
    Microphone → PyAudio → high-pass → Hamming window → FFT
    → log magnitude → balance tilt → noise subtraction
    → slow per-bar AGC → 20s/10min max normalization
    → output stretch/gamma → bar height → smooth attack/release
    → peak hold with gravity
"""

import logging
import math
import threading
import time
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

try:
    import pyaudio
    HAS_PYAUDIO = True
except ImportError:
    HAS_PYAUDIO = False
    logger.warning("PyAudio not installed — spectrum mode disabled. "
                   "Install with: sudo apt install python3-pyaudio")


class SpectrumAnalyzer:
    """
    Real-time audio spectrum analyzer — faithful port of ESP32 version.

    Usage:
        sa = SpectrumAnalyzer(n_bars=172, display_height=86)
        sa.start()
        while running:
            bars, peaks = sa.get_bars()
        sa.stop()
    """

    # ── Constants matching ESP32 spectrum_includes.h ────────────────────

    SAMPLE_RATE = 44100
    FFT_SAMPLES = 512
    FREQ_MIN = 30.0
    FREQ_MAX = 18000.0

    # Slow per-bar AGC (~4 min)
    BAR_TARGET_LEVEL = 0.50
    FRAME_INTERVAL = 0.040           # 25 FPS
    BAR_AVG_TAU = 240.0              # 4 minutes
    BAR_AVG_ALPHA = FRAME_INTERVAL / BAR_AVG_TAU

    # Tie AGCs: max/min <= 2.5
    GAIN_TIE_MAX_RATIO = 2.5

    # 20-second short-term max decay
    MAX20_DECAY = 0.9980

    # 10-minute windowed max (bucketed)
    WIN_BUCKET_S = 10.0              # 10s buckets
    WIN_BUCKETS = 60                 # 60 x 10s = 10 minutes
    WIN_MAX_MIN_FRACTION = 0.22

    # Noise floor tracking
    NOISE_FAST_ALPHA = 0.06
    NOISE_SLOW_ALPHA = 0.0015
    NOISE_MULT = 1.12
    ABS_GATE = 0.010

    # Output shaping
    OUT_STRETCH = 1.12
    OUT_GAMMA = 0.85
    OUT_CLIP = 1.25

    # Bar attack/release speeds
    BAR_ATTACK_MAX = 12
    BAR_RELEASE_MAX = 6

    # Peak decay interval
    PEAK_DECAY_INTERVAL = 0.240      # 240ms between peak drops

    def __init__(
        self,
        n_bars: int = 172,
        display_height: int = 86,
        device_index: Optional[int] = None,
    ):
        self.n_bars = n_bars
        self.display_height = display_height
        self.device_index = device_index

        # Bar output state
        self.bars = np.zeros(n_bars, dtype=np.int32)
        self.peaks = np.zeros(n_bars, dtype=np.int32)

        # Per-bar AGC state
        self._bar_gain = np.ones(n_bars, dtype=np.float64)
        self._bar_avg = np.full(n_bars, self.BAR_TARGET_LEVEL, dtype=np.float64)
        self._noise = np.zeros(n_bars, dtype=np.float64)
        self._max20 = np.full(n_bars, 0.12, dtype=np.float64)

        # 10-minute windowed max buckets
        self._win_buckets = np.zeros((n_bars, self.WIN_BUCKETS), dtype=np.float64)
        self._max10 = np.zeros(n_bars, dtype=np.float64)
        self._bucket_start = 0.0
        self._bucket_idx = 0

        # High-pass filter state
        self._hp_state = 0.0

        # Peak decay timing
        self._last_peak_decay = 0.0

        # Boot animation
        self._boot_phase = 0
        self._boot_mode = True
        self._boot_until = 0.0

        # Precompute Hamming window (matching ESP32's FFT_WIN_TYP_HAMMING)
        self._window = np.hamming(self.FFT_SAMPLES).astype(np.float64)

        # Precompute bin map: log-spaced, one bin per bar (matching ESP32)
        self._bin_map = self._build_bin_map()

        # Balance tilt: reduce lows, lift highs (matching ESP32)
        self._tilt = np.array([
            0.55 + 0.90 * (i / max(1, n_bars - 1))
            for i in range(n_bars)
        ], dtype=np.float64)

        # Threading
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._pa = None
        self._stream = None

    def _build_bin_map(self) -> np.ndarray:
        """Build log-frequency bin mapping (one FFT bin per bar, 30Hz-18kHz)."""
        max_bin = (self.FFT_SAMPLES // 2) - 1
        bins = np.zeros(self.n_bars, dtype=np.int32)

        for i in range(self.n_bars):
            t = i / max(1, self.n_bars - 1)
            f = self.FREQ_MIN * ((self.FREQ_MAX / self.FREQ_MIN) ** t)
            k = round(f * self.FFT_SAMPLES / self.SAMPLE_RATE)
            k = max(1, min(k, max_bin))

            remaining = (self.n_bars - 1) - i
            latest = max_bin - remaining
            k = min(k, latest)

            if i > 0 and k <= bins[i - 1]:
                k = bins[i - 1] + 1
            k = min(k, latest)

            bins[i] = k

        return bins

    # ── Audio device management ──────────────────────────────────────

    def start(self) -> bool:
        """Start audio capture thread."""
        if not HAS_PYAUDIO:
            logger.error("Cannot start spectrum: PyAudio not installed")
            return False
        if self._running:
            return True

        try:
            self._pa = pyaudio.PyAudio()
            dev_idx = self.device_index
            if dev_idx is None:
                dev_idx = self._find_input_device()

            self._stream = self._pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.SAMPLE_RATE,
                input=True,
                input_device_index=dev_idx,
                frames_per_buffer=self.FFT_SAMPLES,
            )

            self._running = True
            self._boot_mode = True
            self._boot_until = time.monotonic() + 6.0
            self._bucket_start = time.monotonic()
            self._last_peak_decay = time.monotonic()

            self._thread = threading.Thread(
                target=self._capture_loop, daemon=True, name="spectrum-audio"
            )
            self._thread.start()
            logger.info(f"Spectrum started: device={dev_idx}, "
                        f"{self.n_bars} bars, {self.display_height}px height")
            return True

        except Exception as e:
            logger.error(f"Failed to start audio: {e}")
            self._cleanup()
            return False

    def stop(self):
        """Stop audio capture."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._cleanup()
        logger.info("Spectrum stopped")

    def _cleanup(self):
        if self._stream:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
        if self._pa:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None

    def _find_input_device(self) -> Optional[int]:
        if not self._pa:
            return None
        info = self._pa.get_host_api_info_by_index(0)
        n = info.get("deviceCount", 0)
        for i in range(n):
            dev = self._pa.get_device_info_by_host_api_device_index(0, i)
            if dev.get("maxInputChannels", 0) > 0:
                name = dev.get("name", "").lower()
                if "usb" in name or "mic" in name:
                    logger.info(f"Audio device [{i}]: {dev['name']}")
                    return i
        default = self._pa.get_default_input_device_info()
        if default:
            logger.info(f"Default audio device: {default['name']}")
            return default.get("index")
        return None

    # ── Main processing loop ─────────────────────────────────────────

    def _capture_loop(self):
        """Audio capture + FFT + per-bar AGC (background thread)."""
        h = self.display_height

        while self._running:
            try:
                # Boot animation phase
                if self._boot_mode:
                    if time.monotonic() < self._boot_until:
                        self._boot_animation_tick()
                        time.sleep(self.FRAME_INTERVAL)
                        continue
                    else:
                        self._boot_mode = False

                # Read audio
                raw = self._stream.read(self.FFT_SAMPLES, exception_on_overflow=False)
                samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64)
                # Normalize to [-1, 1]
                samples /= 32768.0

                # High-pass filter (remove DC/rumble, matching ESP32)
                hp_out = np.empty_like(samples)
                hp = self._hp_state
                for i in range(len(samples)):
                    hp = hp * 0.995 + samples[i] * 0.005
                    hp_out[i] = samples[i] - hp
                self._hp_state = hp

                # Window + FFT
                windowed = hp_out[:self.FFT_SAMPLES] * self._window
                fft_mag = np.abs(np.fft.rfft(windowed))

                # Per-bar: extract one FFT bin, log magnitude, tilt
                raw_bar = np.zeros(self.n_bars, dtype=np.float64)
                for i in range(self.n_bars):
                    k = self._bin_map[i]
                    if k < len(fft_mag):
                        mag = fft_mag[k]
                        v = math.log10(1.0 + mag * 80.0)
                        if not math.isfinite(v) or v < 0:
                            v = 0.0
                        raw_bar[i] = v * self._tilt[i]

                now = time.monotonic()

                # Advance 10-minute window buckets
                self._win_advance(now)

                decay_peaks = (now - self._last_peak_decay) >= self.PEAK_DECAY_INTERVAL

                with self._lock:
                    for i in range(self.n_bars):
                        r = raw_bar[i]

                        # ── Noise floor tracking ──
                        n = self._noise[i]
                        if r < n:
                            n = (1.0 - self.NOISE_FAST_ALPHA) * n + self.NOISE_FAST_ALPHA * r
                        else:
                            n = (1.0 - self.NOISE_SLOW_ALPHA) * n + self.NOISE_SLOW_ALPHA * r
                        if not math.isfinite(n) or n < 0:
                            n = 0.0
                        self._noise[i] = n

                        # Subtract noise + gate
                        snr = r - (n * self.NOISE_MULT) - self.ABS_GATE
                        if not math.isfinite(snr) or snr < 0:
                            snr = 0.0

                        # Apply slow AGC gain
                        x = snr * self._bar_gain[i]

                        # ── 20s max tracking ──
                        m20 = self._max20[i] * self.MAX20_DECAY
                        if x > m20:
                            m20 = x
                        if m20 < 0.12:
                            m20 = 0.12
                        self._max20[i] = m20

                        # ── 10-min window max ──
                        bucket = self._win_buckets[i, self._bucket_idx]
                        if x > bucket:
                            self._win_buckets[i, self._bucket_idx] = x
                        if x > self._max10[i]:
                            self._max10[i] = x

                        denom_min = max(0.12, self._max10[i] * self.WIN_MAX_MIN_FRACTION)
                        denom = max(m20, denom_min)

                        norm = (x / denom) if denom > 1e-6 else 0.0

                        # Quiet gating
                        if snr < 0.020 and self._max10[i] < 0.20:
                            norm = 0.0

                        # Output shaping
                        norm *= self.OUT_STRETCH
                        norm = max(0.0, min(norm, self.OUT_CLIP))
                        norm = norm ** self.OUT_GAMMA
                        norm = max(0.0, min(norm, 1.0))

                        target = round(norm * h)
                        target = max(0, min(target, h))

                        # Bar attack/release
                        cur = int(self.bars[i])
                        if target > cur:
                            step = min(target - cur, self.BAR_ATTACK_MAX)
                            cur += step
                        elif target < cur:
                            step = min(cur - target, self.BAR_RELEASE_MAX)
                            cur -= step
                        cur = max(0, min(cur, h))
                        self.bars[i] = cur

                        # Peak dots
                        if cur >= self.peaks[i]:
                            self.peaks[i] = cur
                        elif decay_peaks and self.peaks[i] > 0 and self.peaks[i] > self.bars[i]:
                            self.peaks[i] -= 1

                        # ── Slow AGC update ──
                        out_level = cur / h if h > 0 else 0.0
                        self._bar_avg[i] += self.BAR_AVG_ALPHA * (out_level - self._bar_avg[i])
                        err = self.BAR_TARGET_LEVEL - self._bar_avg[i]
                        bias = 1.45 if err < 0 else 0.85
                        self._bar_gain[i] *= (1.0 + self.BAR_AVG_ALPHA * bias * err)
                        self._bar_gain[i] = max(0.20, min(self._bar_gain[i], 40.0))

                    # Tie AGCs: enforce max/min <= 2.5
                    gmax = max(np.max(self._bar_gain), 0.20)
                    gmin_allowed = gmax / self.GAIN_TIE_MAX_RATIO
                    self._bar_gain = np.maximum(self._bar_gain, gmin_allowed)

                if decay_peaks:
                    self._last_peak_decay = now

            except Exception as e:
                if self._running:
                    logger.debug(f"Audio error: {e}")
                    time.sleep(0.1)

    def _win_advance(self, now: float):
        """Advance 10-minute windowed max buckets."""
        if self._bucket_start == 0:
            self._bucket_start = now
            self._win_buckets[:] = 0
            self._max10[:] = 0
            return

        advanced = False
        while (now - self._bucket_start) >= self.WIN_BUCKET_S:
            self._bucket_start += self.WIN_BUCKET_S
            self._bucket_idx = (self._bucket_idx + 1) % self.WIN_BUCKETS
            self._win_buckets[:, self._bucket_idx] = 0
            advanced = True

        if advanced:
            self._max10 = np.max(self._win_buckets, axis=1)

    def _boot_animation_tick(self):
        """Boot animation — sinusoidal waves (matching ESP32)."""
        self._boot_phase += 1
        h = self.display_height
        with self._lock:
            for i in range(self.n_bars):
                w1 = 0.5 + 0.5 * math.sin(i * 0.35 + self._boot_phase * 0.20)
                w2 = 0.5 + 0.5 * math.sin(i * 0.11 - self._boot_phase * 0.16)
                mix = w1 * 0.72 + w2 * 0.28
                bh = int(6.0 + mix * (h - 12))
                bh = max(0, min(bh, h))
                self.bars[i] = bh
                pk = bh + 2 + int(2.0 * (0.5 + 0.5 * math.sin(
                    self._boot_phase * 0.33 + i * 0.19)))
                self.peaks[i] = min(pk, h)

    # ── Public interface ─────────────────────────────────────────────

    def get_bars(self):
        """Get current bar heights and peak positions (thread-safe)."""
        with self._lock:
            return self.bars.copy(), self.peaks.copy()

    @property
    def is_boot(self) -> bool:
        return self._boot_mode

    @property
    def is_running(self) -> bool:
        return self._running

    @staticmethod
    def list_devices():
        """List available audio input devices."""
        if not HAS_PYAUDIO:
            print("PyAudio not installed")
            return
        pa = pyaudio.PyAudio()
        info = pa.get_host_api_info_by_index(0)
        n = info.get("deviceCount", 0)
        print(f"\n{'#':>3}  {'Ch':>3}  {'Rate':>7}  Name")
        print("-" * 55)
        for i in range(n):
            dev = pa.get_device_info_by_host_api_device_index(0, i)
            ch = dev.get("maxInputChannels", 0)
            if ch > 0:
                rate = int(dev.get("defaultSampleRate", 0))
                print(f"{i:>3}  {ch:>3}  {rate:>7}  {dev.get('name', '?')}")
        pa.terminate()


if __name__ == "__main__":
    print("Available audio input devices:")
    SpectrumAnalyzer.list_devices()
