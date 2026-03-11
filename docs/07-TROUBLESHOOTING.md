# Troubleshooting Guide

## Quick Diagnostic Flowchart

```
Panel is black (no display)?
├── Is PSU on? Check PSU green LED
│   └── No → Check AC power, fuse, switch
├── Is Colorlight powered? Check PWR LED (green)
│   └── No → Check 5V wiring to 5A-75B, check polarity
├── Is Colorlight receiving data? Check NET LED (blinking)
│   └── No → Check Ethernet cable, check Pi software is running
├── Are panels powered? Feel panel back (slightly warm = powered)
│   └── No → Check 5V wiring to each panel, check polarity
└── Is ribbon cable connected properly?
    └── Check HUB75 ribbon is fully seated, keyed correctly
```

---

## Hardware Problems

### Panel stays black (powered but no image)

| Check | How | Fix |
|-------|-----|-----|
| Colorlight NET LED | Should blink when Pi sends data | See "Software not running" section |
| Ribbon cable seated? | Push firmly until clicks, both ends | Reseat ribbon cable |
| Ribbon cable orientation | Keyed notch must align | Flip cable if not keyed |
| Correct output port | Must use J1 on Colorlight | Move ribbon to J1 |
| Panel scan rate configured? | LEDVision must match panel | Reconfigure in LEDVision (see guide 04) |

### Garbled image / wrong colors

| Symptom | Cause | Fix |
|---------|-------|-----|
| Red and blue swapped | RGB order mismatch | In LEDVision: swap R/B in module settings |
| Top half OK, bottom half garbled | Wrong scan rate | Set scan to 1/43 in LEDVision |
| Image shifted or offset | Wrong module size | Set module to 172x86 in LEDVision |
| Random pixels lighting up | Bad ribbon cable | Replace ribbon cable |
| Horizontal lines across display | Wrong driver IC setting | Set IC to ICN2038S in LEDVision |
| Image on Panel 1 OK, Panel 2 garbled | Cascade count wrong | Set chain to 2 panels in LEDVision |

### Panel flickers

| Cause | Fix |
|-------|-----|
| Insufficient power | Check voltage at panel (must be >4.5V). Use thicker wire. |
| Loose ribbon cable | Reseat firmly |
| Wrong OE polarity | Toggle in LEDVision |
| PSU voltage too high | Measure PSU output, adjust pot to exactly 5.0V |
| Long power wires | Shorten wires or use thicker gauge |

### Only one panel works

| Check | Fix |
|-------|-----|
| Panel 2 power | Verify 5V reaching Panel 2 (separate wires from bus) |
| Ribbon from Panel 1 OUT → Panel 2 IN | Check both ends seated |
| LEDVision chain count | Must be set to 2 panels |
| Try panels individually | Swap Panel 1 and 2 positions to isolate bad panel |

---

## Network Problems

### Colorlight not detected by LEDVision

| Check | Fix |
|-------|-----|
| PC Ethernet is Gigabit? | `wmic NIC get Speed` must show 1000000000 |
| Cable quality | Use Cat5e or Cat6. Try a different cable. |
| PC firewall | Temporarily disable Windows Firewall |
| Same network segment | Set PC static IP 192.168.0.200/24 |
| Colorlight powered? | PWR LED must be green |
| LEDVision version | Try an older version (V2.x or V3.x) |

### Pi can't reach Colorlight (no display from software)

| Check | How to test | Fix |
|-------|------------|-----|
| Ethernet link speed | `ethtool eth0 \| grep Speed` | Must show 1000Mb/s. Replace cable if 100Mb/s |
| Interface is UP | `ip link show eth0` | `sudo ip link set eth0 up` |
| Raw socket permission | Run with `sudo` | `sudo python3 main.py` |
| Correct interface name | `ip link show` to list all | Update config.yaml interface name |
| Pi Ethernet port working | `ethtool eth0` shows link detected: yes | Try different Ethernet port on switch |

### MQTT connection failed

| Symptom | Check | Fix |
|---------|-------|-----|
| "Connection refused" | Is Mosquitto running on HA? | Install/start Mosquitto add-on |
| "Authentication failed" | Wrong username or password | Verify MQTT credentials in HA |
| "Host unreachable" | Wrong broker IP | Ping the HA host from Pi: `ping 192.168.1.100` |
| "Connection timed out" | Firewall blocking port 1883 | Open port 1883 on HA host firewall |

**Test MQTT from Pi:**
```bash
# Install test client
sudo apt install -y mosquitto-clients

# Test connection
mosquitto_pub -h YOUR_HA_IP -u mqtt_user -P mqtt_pass \
  -t "test/topic" -m "hello"

# If no error = MQTT works
# If "Connection refused" = check broker
# If "not authorised" = check credentials
```

---

## Software Problems

### Service won't start

```bash
# Check service status
sudo systemctl status ledpanel

# Read the error logs
journalctl -u ledpanel -n 50 --no-pager
```

| Error Message | Fix |
|---------------|-----|
| "ModuleNotFoundError: No module named 'numpy'" | `sudo /opt/ledpanel/venv/bin/pip install -r /opt/ledpanel/requirements.txt` |
| "PermissionError: raw socket" | Service must run as root (check ledpanel.service) |
| "No such file or directory: config.yaml" | Verify config.yaml exists in /opt/ledpanel/ |
| "YAML parse error" | Check config.yaml syntax (indentation, colons, quotes) |
| "Cannot open socket on eth0" | Interface name wrong — run `ip link show` and update config |

### Test pattern works but MQTT commands don't

```bash
# Verify MQTT messages are arriving
mosquitto_sub -h YOUR_HA_IP -u mqtt_user -P mqtt_pass -t "ledpanel/#" -v

# In another terminal, send a command
mosquitto_pub -h YOUR_HA_IP -u mqtt_user -P mqtt_pass \
  -t "ledpanel/command" -m '{"mode":"text","text":"test"}'

# The sub terminal should show the message
```

| Issue | Fix |
|-------|-----|
| No messages received | Check MQTT broker, credentials, topic |
| Messages received but display doesn't change | Check journalctl for JSON parse errors |
| Wrong topic | Verify topic_prefix in config.yaml matches your publish topic |

### Display shows "RENDER ERR"

| Cause | Fix |
|-------|-----|
| Missing font file | Install: `sudo apt install fonts-dejavu-core` |
| Invalid color format | Use "#RRGGBB" format (with # and 6 hex digits) |
| Image file not found | Check the path in the image mode command |

---

## Home Assistant Problems

### LED Panel entity not appearing in HA

| Check | Fix |
|-------|-----|
| MQTT auto-discovery enabled in HA? | Settings → Devices → MQTT → check discovery is on |
| Panel service running? | `sudo systemctl status ledpanel` |
| Correct discovery prefix? | Config.yaml `ha_discovery_prefix` must match HA (usually "homeassistant") |
| Waited long enough? | Discovery can take up to 60 seconds |

**Force re-discovery:**
```bash
sudo systemctl restart ledpanel
```
The service re-publishes discovery messages on every connect.

### Automations not firing

| Issue | Fix |
|-------|-----|
| Entity IDs don't match | Check your actual entity IDs in HA Developer Tools → States |
| MQTT service not available | Verify MQTT integration is loaded in HA |
| Template errors | Test templates in Developer Tools → Template |

---

## Performance Problems

### Low frame rate / stuttering

| Cause | Fix |
|-------|-----|
| Pi CPU overloaded | Reduce FPS in config.yaml (try 15-20) |
| Network congestion | Use dedicated Ethernet for Colorlight |
| Debug logging enabled | Set logger level to WARN in config.yaml |
| Complex rendering (large fonts) | Reduce font_size or simplify content |

### High CPU usage on Pi

```bash
# Check CPU usage
top -p $(pgrep -f "main.py")
```

Normal: 5-15% at 30 FPS
High: >30% — reduce FPS or check for rendering issues

---

## Factory Reset

### Reset everything to defaults:

**Software:**
```bash
sudo systemctl stop ledpanel
sudo rm -rf /opt/ledpanel
cd ~/ledpanel
sudo bash install.sh
```

**Colorlight card:**
1. Reconnect to Windows PC
2. Open LEDVision
3. Control → Restore Factory Defaults
4. Reconfigure with guide 04

**Raspberry Pi (full reset):**
1. Re-flash SD card with Raspberry Pi Imager
2. Start from Step 1 of guide 05

---

## Getting Help

| Resource | URL |
|----------|-----|
| Colorlight community | FPP/Falcon Player forums |
| Raspberry Pi forums | forums.raspberrypi.com |
| Home Assistant community | community.home-assistant.io |
| MQTT debugging | Use MQTT Explorer (free desktop app) |
| Colorlight protocol details | github.com/haraldkubota/colorlight |
