# LED Panel Controller

Drive commercial P1.86 LED matrix panels from Home Assistant using a Raspberry Pi and a Colorlight 5A-75B receiving card over Gigabit Ethernet.

## Hardware

| Component | Purpose |
|---|---|
| Raspberry Pi 4/5 | Sends pixel data over Gigabit Ethernet |
| Colorlight 5A-75B (V8) | Receiving card — drives HUB75 panels at any scan rate |
| 2x P1.86 320x160mm panels | 172x86 pixels each, 1/43 scan, ICN2038S driver |
| 5V 20A PSU | Powers both panels (each draws up to ~6A peak) |

**Total resolution:** 344x86 (side-by-side) or 172x172 (stacked)

## Wiring

```
Raspberry Pi 4 ──(Cat6 GbE)──> Colorlight 5A-75B ──(HUB75 ribbon)──> Panel 1 ──> Panel 2
                                      ▲                                  ▲           ▲
                                      │                                  │           │
                                 5V PSU ────────────────────────────────┴───────────┘
                                 (power each panel and the card separately)
```

Each panel needs its own 5V power wires from the PSU. The HUB75 ribbon only carries data.

## Software Architecture

```
Home Assistant ──(MQTT)──> mqtt_bridge.py ──> renderer.py ──> colorlight.py ──> Ethernet ──> 5A-75B
```

| File | Description |
|---|---|
| `colorlight.py` | Raw Ethernet protocol driver for Colorlight 5A-75B |
| `renderer.py` | Pillow-based display renderer (text, clock, sensors, scroll, alerts) |
| `mqtt_bridge.py` | MQTT client with HA auto-discovery |
| `main.py` | Main application — render loop + command handler |
| `config.yaml` | All settings (display, network, MQTT, modes) |
| `install.sh` | One-command Raspberry Pi installer |
| `ha_config/automations.yaml` | 8 example Home Assistant automations |

## Quick Start

### 1. One-time Colorlight setup (Windows PC)

- Install [Colorlight LEDVision](https://www.colorlight-led.com/)
- Connect 5A-75B to PC via Gigabit Ethernet
- Configure: Module 172x86, Scan 1/43, IC ICN2038S, Port J1, Chain 2
- Save to receiver flash

### 2. Deploy to Raspberry Pi

```bash
scp -r ledpanel/ pi@<pi-ip>:~/ledpanel
ssh pi@<pi-ip>
nano ~/ledpanel/config.yaml        # Set your MQTT broker IP, user, password
cd ~/ledpanel && sudo bash install.sh
sudo systemctl start ledpanel
```

### 3. Test

```bash
sudo /opt/ledpanel/venv/bin/python3 /opt/ledpanel/main.py --test
```

## MQTT Commands

Publish JSON to `ledpanel/command`:

```json
{"mode": "text", "text": "Hello!", "color": "#00FF00", "font_size": 28}
{"mode": "clock", "show_date": true}
{"mode": "scroll", "text": "Breaking news...", "speed": 2}
{"mode": "sensors", "data": {"Temp": "22°C", "Humidity": "45%"}}
{"mode": "alert", "text": "DOOR OPEN!", "color": "#FF0000"}
{"mode": "off"}
```

Set brightness (0-255): publish to `ledpanel/brightness/set`

## HA Auto-Discovery

The panel auto-registers these entities in Home Assistant:

- `light.led_panel` — on/off + brightness
- `sensor.led_panel_mode` — current display mode
- `number.led_panel_brightness` — brightness slider

## Display Modes

| Mode | Description |
|---|---|
| `text` | Static text with color, size, alignment |
| `multiline` | Multiple lines, auto-centered |
| `clock` | Live clock with optional date |
| `scroll` | Horizontally scrolling text |
| `sensors` | Dashboard grid of sensor values |
| `alert` | Flashing border alert message |
| `image` | Display an image file |
| `progress` | Progress bar with label |
| `off` | Display off (black) |

## License

MIT
