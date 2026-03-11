#pragma once
// DJspectrum — ESP32-S3 + dual HUB75 128x64  (256 x 64)
// Spectrum analyser + text / clock / scroll / sensors / alert / progress modes

#include <cmath>
#include <cstring>
#include <array>
#include <algorithm>
#include "driver/i2s.h"
#include "arduinoFFT.h"

namespace spectrum {

// ── display geometry ──────────────────────────────────────────────────────────
static constexpr int W = 256;
static constexpr int H = 64;

// ── FFT ───────────────────────────────────────────────────────────────────────
static constexpr int SAMPLES     = 512;
static constexpr int SAMPLE_RATE = 44100;
static constexpr int N_BARS      = 128;          // 128 bars across 256 px

static double   vReal[SAMPLES];
static double   vImag[SAMPLES];
static int32_t  i2s_buf[SAMPLES];
static ArduinoFFT<double> FFT(vReal, vImag, SAMPLES, SAMPLE_RATE);

// ── I2S microphone ───────────────────────────────────────────────────────────
static bool i2s_ready = false;

inline void i2s_init_mic(gpio_num_t ws, gpio_num_t sd, gpio_num_t sck) {
  i2s_config_t cfg = {};
  cfg.mode            = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  cfg.sample_rate     = SAMPLE_RATE;
  cfg.bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT;
  cfg.channel_format  = I2S_CHANNEL_FMT_ONLY_LEFT;
  cfg.communication_format = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count   = 4;
  cfg.dma_buf_len     = SAMPLES;
  cfg.use_apll        = false;

  i2s_driver_install(I2S_NUM_0, &cfg, 0, nullptr);
  i2s_pin_config_t pins = {};
  pins.bck_io_num   = sck;
  pins.ws_io_num    = ws;
  pins.data_in_num  = sd;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  i2s_set_pin(I2S_NUM_0, &pins);
  i2s_ready = true;
}

// ── AGC helpers ──────────────────────────────────────────────────────────────
static float agc_gain  = 1.0f;
static float noise_floor = 80.0f;

// ── FFT → bars ───────────────────────────────────────────────────────────────
inline void fft_update(std::array<uint8_t, N_BARS>& bars,
                       std::array<uint8_t, N_BARS>& peaks,
                       float& ref_level) {
  if (!i2s_ready) return;

  size_t bytes_read = 0;
  i2s_read(I2S_NUM_0, i2s_buf, sizeof(i2s_buf), &bytes_read, portMAX_DELAY);
  int n = bytes_read / 4;
  if (n < 64) return;

  // Populate FFT input with Hann window
  for (int i = 0; i < SAMPLES; i++) {
    double s = (i < n) ? (double)(i2s_buf[i] >> 8) : 0.0;
    double w = 0.5 * (1.0 - cos(2.0 * M_PI * i / (SAMPLES - 1)));
    vReal[i] = s * w;
    vImag[i] = 0.0;
  }

  FFT.windowing(FFT_WIN_TYP_HANN, FFT_FORWARD);
  FFT.compute(FFT_FORWARD);
  FFT.complexToMagnitude();

  // Map FFT bins → N_BARS using log-frequency mapping
  const int useful = SAMPLES / 2;
  float raw[N_BARS] = {};

  for (int b = 0; b < N_BARS; b++) {
    // Log spacing: each bar covers an exponentially larger range
    float lo = 1.0f + (float)b / N_BARS * (useful - 2);
    float hi = 1.0f + (float)(b + 1) / N_BARS * (useful - 2);
    // Exponential mapping for better low-frequency resolution
    float exp_lo = powf((float)useful, (float)b / N_BARS);
    float exp_hi = powf((float)useful, (float)(b + 1) / N_BARS);
    if (exp_lo < 1) exp_lo = 1;
    if (exp_hi < 1) exp_hi = 1;
    if (exp_hi > useful) exp_hi = useful;

    int i_lo = (int)exp_lo;
    int i_hi = (int)exp_hi;
    if (i_hi <= i_lo) i_hi = i_lo + 1;
    if (i_hi > useful) i_hi = useful;

    float sum = 0;
    int cnt = 0;
    for (int i = i_lo; i < i_hi; i++) {
      sum += (float)vReal[i];
      cnt++;
    }
    raw[b] = (cnt > 0) ? sum / cnt : 0;
  }

  // AGC: track peak and adjust gain
  float peak_val = 0;
  for (int b = 0; b < N_BARS; b++)
    if (raw[b] > peak_val) peak_val = raw[b];

  // Adaptive noise floor
  noise_floor = noise_floor * 0.995f + peak_val * 0.005f;
  float target_peak = std::max(noise_floor * 3.0f, 500.0f);

  if (peak_val > 0.01f) {
    float desired_gain = target_peak / peak_val;
    float alpha = (desired_gain > agc_gain) ? 0.02f : 0.08f;
    agc_gain = agc_gain * (1.0f - alpha) + desired_gain * alpha;
  }
  agc_gain = std::max(0.5f, std::min(agc_gain, 200.0f));

  // Apply gain, compute bar heights
  for (int b = 0; b < N_BARS; b++) {
    float v = raw[b] * agc_gain;
    float db = (v > 1.0f) ? 20.0f * log10f(v) : 0.0f;
    float norm = db / 60.0f;  // 60 dB range
    if (norm < 0) norm = 0;
    if (norm > 1) norm = 1;
    int h = (int)(norm * H);

    // Smooth fall
    int cur = bars[b];
    if (h >= cur) {
      bars[b] = h;
    } else {
      int drop = std::max(1, cur / 12);
      bars[b] = std::max(0, cur - drop);
    }

    // Peak hold & gravity
    if (h >= peaks[b]) {
      peaks[b] = h;
    } else if (peaks[b] > 0) {
      peaks[b] = std::max(0, (int)peaks[b] - 1);
    }
  }
}

// ── boot animation ───────────────────────────────────────────────────────────
static uint32_t boot_phase = 0;

inline void boot_animation_update(std::array<uint8_t, N_BARS>& bars,
                                  std::array<uint8_t, N_BARS>& peaks) {
  boot_phase++;
  for (int i = 0; i < N_BARS; i++) {
    float wave = sinf((float)i * 0.15f + (float)boot_phase * 0.12f);
    float wave2 = sinf((float)i * 0.08f - (float)boot_phase * 0.07f);
    float v = (wave * 0.5f + 0.5f) * (wave2 * 0.3f + 0.7f);
    bars[i] = (uint8_t)(v * H);
    peaks[i] = std::min((int)bars[i] + 3, (int)H);
  }
}

// ── color helpers ────────────────────────────────────────────────────────────
struct RGB { uint8_t r, g, b; };

inline uint8_t lerp8(uint8_t a, uint8_t b, float u) {
  if (u < 0) u = 0; if (u > 1) u = 1;
  return (uint8_t)(a + (b - a) * u + 0.5f);
}

inline RGB base_color_for_bar(int i, int total) {
  float t = (total <= 1) ? 0.0f : (float)i / (float)(total - 1);
  float p = t * 5.0f;
  int seg = (int)p;
  float u = p - seg;
  if (seg < 0) { seg = 0; u = 0; }
  if (seg > 4) { seg = 4; u = 1; }

  const uint8_t R[6] = {255,255,255,  0,  0,  0};
  const uint8_t G[6] = {  0,128,255,255,255,  0};
  const uint8_t B[6] = {  0,  0,  0,  0,255,255};

  return {lerp8(R[seg],R[seg+1],u),
          lerp8(G[seg],G[seg+1],u),
          lerp8(B[seg],B[seg+1],u)};
}

// ── spectrum renderer (called from display lambda) ───────────────────────────
inline void draw_spectrum(esphome::display::Display &it,
                          std::array<uint8_t, N_BARS>& bars,
                          std::array<uint8_t, N_BARS>& peaks,
                          bool is_boot) {
  const int w = it.get_width();
  const int h = it.get_height();
  const int bar_w = std::max(1, w / N_BARS);               // 2 px per bar
  const int draw_w = is_boot ? bar_w : std::max(1, bar_w - 1);

  for (int i = 0; i < N_BARS; i++) {
    int bh = bars[i];
    int pk = peaks[i];
    if (bh < 0) bh = 0; if (bh > h) bh = h;
    if (pk < 0) pk = 0; if (pk > h) pk = h;

    const int x = i * bar_w;
    if (x >= w) break;
    int ww = draw_w;
    if (x + ww > w) ww = w - x;
    if (ww <= 0) continue;

    RGB base = base_color_for_bar(i, N_BARS);

    if (bh > 0) {
      float strength = (float)bh / (float)h;
      int fade = std::min(bh, 6 + (int)((float)bh * 64.0f / (float)h));
      float min_scale = (0.20f - 0.12f * strength) / 8.0f;
      if (min_scale < 0.015f) min_scale = 0.015f;

      for (int yy = 0; yy < bh; yy++) {
        int y = h - 1 - yy;
        float s = 1.0f;
        if (yy < fade) {
          float uf = (fade <= 1) ? 1.0f : (float)yy / (float)(fade - 1);
          s = min_scale + (1.0f - min_scale) * uf;
        }
        if (s < 0.09f) continue;

        float ubar = (bh <= 1) ? 1.0f : (float)yy / (float)(bh - 1);
        float pmix = (ubar - 0.70f) / 0.30f;
        if (pmix < 0) pmix = 0; if (pmix > 1) pmix = 1;
        pmix = pmix * pmix * strength;

        uint8_t r0 = (uint8_t)(base.r * s);
        uint8_t g0 = (uint8_t)(base.g * s);
        uint8_t b0 = (uint8_t)(base.b * s);

        uint8_t pr = (uint8_t)(255.0f * s);
        uint8_t pg = 0;
        uint8_t pb = (uint8_t)(255.0f * s);

        uint8_t r = lerp8(r0, pr, pmix);
        uint8_t g = lerp8(g0, pg, pmix);
        uint8_t b = lerp8(b0, pb, pmix);

        it.filled_rectangle(x, y, ww, 1, esphome::Color(r, g, b));
      }
    }

    if (pk > 0) {
      int py = h - pk - 1;
      if (py < 0) py = 0;
      it.filled_rectangle(x, py, ww, 1, esphome::Color(255, 255, 255));
    }
  }
}

// ── text rendering helpers ───────────────────────────────────────────────────
// ESPHome font rendering is handled via Font* objects passed from YAML.
// These helpers draw centered/scrolled text and other modes.

static int  scroll_offset  = 0;
static int  scroll_width   = 0;
static bool scroll_inited  = false;
static uint32_t alert_frame = 0;

inline void draw_text_centered(esphome::display::Display &it,
                               esphome::font::Font *font,
                               const char *text,
                               esphome::Color color) {
  int tw, th, bx, by;
  it.get_text_bounds(0, 0, text, font, esphome::display::TextAlign::TOP_LEFT,
                     &bx, &by, &tw, &th);
  int x = (it.get_width() - tw) / 2;
  int y = (it.get_height() - th) / 2;
  it.print(x, y, font, color, esphome::display::TextAlign::TOP_LEFT, text);
}

inline void draw_scroll(esphome::display::Display &it,
                        esphome::font::Font *font,
                        const char *text,
                        esphome::Color color,
                        int speed) {
  int tw, th, bx, by;
  it.get_text_bounds(0, 0, text, font, esphome::display::TextAlign::TOP_LEFT,
                     &bx, &by, &tw, &th);
  scroll_width = tw + it.get_width();
  int y = (it.get_height() - th) / 2;
  int x = it.get_width() - scroll_offset;
  it.print(x, y, font, color, esphome::display::TextAlign::TOP_LEFT, text);
  scroll_offset += speed;
  if (scroll_offset > scroll_width) scroll_offset = 0;
}

inline void draw_alert(esphome::display::Display &it,
                       esphome::font::Font *font,
                       const char *text,
                       esphome::Color color) {
  alert_frame++;
  int w = it.get_width();
  int h = it.get_height();
  bool flash = ((alert_frame / 8) % 2) == 0;
  esphome::Color border = flash ? color : esphome::Color(0, 0, 0);
  // Draw border (3px)
  it.filled_rectangle(0, 0, w, 3, border);
  it.filled_rectangle(0, h - 3, w, 3, border);
  it.filled_rectangle(0, 0, 3, h, border);
  it.filled_rectangle(w - 3, 0, 3, h, border);
  // Centered text
  draw_text_centered(it, font, text, color);
}

inline void draw_progress(esphome::display::Display &it,
                          esphome::font::Font *font,
                          const char *label,
                          float value, float max_val,
                          esphome::Color bar_color,
                          esphome::Color text_color) {
  int w = it.get_width();
  int h = it.get_height();
  float pct = (max_val > 0) ? (value / max_val) : 0;
  if (pct < 0) pct = 0; if (pct > 1) pct = 1;

  // Label at top
  it.print(4, 2, font, text_color, esphome::display::TextAlign::TOP_LEFT, label);

  // Bar area
  int bar_y = h / 2 - 6;
  int bar_h = 12;
  int bar_margin = 8;
  int bar_max_w = w - bar_margin * 2;
  it.rectangle(bar_margin, bar_y, bar_max_w, bar_h, text_color);
  int fill_w = (int)(pct * (bar_max_w - 2));
  if (fill_w > 0) {
    it.filled_rectangle(bar_margin + 1, bar_y + 1, fill_w, bar_h - 2, bar_color);
  }

  // Percentage text below
  char pct_buf[16];
  snprintf(pct_buf, sizeof(pct_buf), "%.0f%%", pct * 100.0f);
  int tw, th, bx, by;
  it.get_text_bounds(0, 0, pct_buf, font, esphome::display::TextAlign::TOP_LEFT,
                     &bx, &by, &tw, &th);
  it.print((w - tw) / 2, bar_y + bar_h + 4, font, text_color,
           esphome::display::TextAlign::TOP_LEFT, pct_buf);
}

inline void draw_sensors(esphome::display::Display &it,
                         esphome::font::Font *font,
                         esphome::font::Font *font_sm,
                         const char* labels[], const char* values[],
                         int count,
                         esphome::Color label_color,
                         esphome::Color value_color) {
  int w = it.get_width();
  int h = it.get_height();
  // Auto-grid: up to 4 columns
  int cols = std::min(count, 4);
  int rows = (count + cols - 1) / cols;
  int cell_w = w / cols;
  int cell_h = h / rows;

  for (int i = 0; i < count; i++) {
    int col = i % cols;
    int row = i / cols;
    int cx = col * cell_w + cell_w / 2;
    int cy = row * cell_h;

    // Label
    int tw, th, bx, by;
    it.get_text_bounds(0, 0, labels[i], font_sm, esphome::display::TextAlign::TOP_LEFT,
                       &bx, &by, &tw, &th);
    it.print(cx - tw / 2, cy + 2, font_sm, label_color,
             esphome::display::TextAlign::TOP_LEFT, labels[i]);

    // Value
    it.get_text_bounds(0, 0, values[i], font, esphome::display::TextAlign::TOP_LEFT,
                       &bx, &by, &tw, &th);
    it.print(cx - tw / 2, cy + cell_h / 2, font, value_color,
             esphome::display::TextAlign::TOP_LEFT, values[i]);
  }
}

// ── clock renderer ───────────────────────────────────────────────────────────
inline void draw_clock(esphome::display::Display &it,
                       esphome::font::Font *font_big,
                       esphome::font::Font *font_sm,
                       esphome::Color color,
                       bool show_date) {
  auto now = id(ha_time).now();
  if (!now.is_valid()) {
    draw_text_centered(it, font_big, "No Time", color);
    return;
  }
  char time_buf[16];
  snprintf(time_buf, sizeof(time_buf), "%02d:%02d:%02d",
           now.hour, now.minute, now.second);

  int w = it.get_width();
  int h = it.get_height();

  if (show_date) {
    // Time top half, date bottom half
    int tw, th, bx, by;
    it.get_text_bounds(0, 0, time_buf, font_big, esphome::display::TextAlign::TOP_LEFT,
                       &bx, &by, &tw, &th);
    it.print((w - tw) / 2, h / 4 - th / 2, font_big, color,
             esphome::display::TextAlign::TOP_LEFT, time_buf);

    char date_buf[32];
    snprintf(date_buf, sizeof(date_buf), "%04d-%02d-%02d",
             now.year, now.month, now.day_of_month);
    it.get_text_bounds(0, 0, date_buf, font_sm, esphome::display::TextAlign::TOP_LEFT,
                       &bx, &by, &tw, &th);
    it.print((w - tw) / 2, 3 * h / 4 - th / 2, font_sm, color,
             esphome::display::TextAlign::TOP_LEFT, date_buf);
  } else {
    draw_text_centered(it, font_big, time_buf, color);
  }
}

}  // namespace spectrum
