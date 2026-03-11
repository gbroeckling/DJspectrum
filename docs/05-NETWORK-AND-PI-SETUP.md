# Network and Raspberry Pi Setup Guide

## Raspberry Pi OS Installation

### Step 1: Download Raspberry Pi Imager
- Download from: https://www.raspberrypi.com/software/
- Available for Windows, macOS, Linux

### Step 2: Flash the SD Card
1. Insert MicroSD card into your PC
2. Open Raspberry Pi Imager
3. Select:
   - **Device:** Raspberry Pi 4 (or Pi 5)
   - **OS:** Raspberry Pi OS Lite (64-bit) — no desktop needed
   - **Storage:** Your MicroSD card
4. Click the **gear icon** (or Edit Settings) to pre-configure:

   | Setting | Value |
   |---------|-------|
   | Hostname | `ledpanel-pi` |
   | Username | `pi` |
   | Password | (choose a strong password) |
   | Enable SSH | Yes (password authentication) |
   | WiFi SSID | Your home WiFi name |
   | WiFi Password | Your WiFi password |
   | WiFi Country | CA (Canada) |
   | Locale | America/Vancouver (or your timezone) |

5. Click **Write** and wait for completion

### Step 3: First Boot
1. Insert SD card into Raspberry Pi
2. Connect Ethernet cable to router/switch (NOT to Colorlight yet)
3. Connect USB-C power
4. Wait 60-90 seconds for first boot
5. Find the Pi on your network:
   ```
   ping ledpanel-pi.local
   ```
   Or check your router's DHCP client list for the Pi's IP

### Step 4: SSH In and Update
```bash
ssh pi@ledpanel-pi.local

# Update everything
sudo apt update && sudo apt full-upgrade -y

# Install essentials
sudo apt install -y python3-venv python3-dev git ethtool net-tools

# Reboot to apply kernel updates
sudo reboot
```

---

## Network Configuration

### Option A: Single Ethernet with Switch (Recommended)

```
Internet ──► Router ──► Gigabit Switch ──┬──► Pi (eth0, DHCP)
                                         ├──► Colorlight 5A-75B
                                         ├──► HA Host
                                         └──► Other devices
```

**This is the simplest setup.** The Pi gets an IP via DHCP, communicates with HA over the network, and sends raw Ethernet frames to the Colorlight on the same switch.

The Colorlight does NOT use IP — it uses raw Layer 2 Ethernet frames. It doesn't need a DHCP address or any IP configuration. It just needs to be on the same physical Ethernet segment as the Pi.

**Requirements:**
- Switch MUST be Gigabit (1000Mbps)
- All cables must be Cat5e or Cat6

### Option B: Dual Network (Ethernet + WiFi)

```
WiFi ──► Pi (wlan0) ──► Home network / HA
Ethernet ──► Pi (eth0) ──► Colorlight 5A-75B (direct cable)
```

Use this if you want a dedicated direct cable to the Colorlight without a switch.

**Configure a static IP on the Pi's Ethernet:**
```bash
sudo nano /etc/dhcpcd.conf
```
Add at the bottom:
```
interface eth0
static ip_address=192.168.100.1/24
```
Then restart networking:
```bash
sudo systemctl restart dhcpcd
```

The Colorlight doesn't care about IP, but the Pi's eth0 needs a link-up state. The static IP ensures the interface stays active.

### Option C: Pi as HA Host + Panel Controller

If your Home Assistant runs on the same Pi:
```
Ethernet ──► Pi ──┬──► HA (localhost:8123)
                  └──► Colorlight raw frames (same eth0)
```
Everything runs on one Pi. MQTT broker is at localhost.

In `config.yaml`, set:
```yaml
mqtt:
  broker: "127.0.0.1"
```

---

## Verify Gigabit Ethernet Link

After connecting the Pi to the Colorlight (directly or via switch):

```bash
# Check link speed — MUST show 1000Mb/s
ethtool eth0 | grep Speed
# Expected: Speed: 1000Mb/s

# If it shows 100Mb/s:
# - Bad cable (replace with Cat6)
# - Bad switch port (try another port)
# - The 5A-75B may not be powered (power it first)

# Check the interface is UP
ip link show eth0
# Should show: state UP
```

---

## Set a Static IP for the Pi (Optional but Recommended)

A static IP makes it easier to SSH in and ensures HA always knows where the Pi is.

### Method 1: Router DHCP Reservation (Easiest)
1. Log into your router admin page
2. Find the Pi in the DHCP client list
3. Reserve its current IP (e.g., 192.168.1.150)
4. The Pi always gets the same IP without any config changes

### Method 2: Static IP on the Pi
```bash
sudo nano /etc/dhcpcd.conf
```
Add:
```
interface eth0
static ip_address=192.168.1.150/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```
Then:
```bash
sudo systemctl restart dhcpcd
```

---

## MQTT Broker Setup on Home Assistant

The LED panel communicates with HA through MQTT. You need an MQTT broker running.

### If using Mosquitto Add-on (Most Common):
1. In HA: **Settings → Add-ons → Add-on Store**
2. Search for "Mosquitto broker"
3. Click Install, then Start
4. Go to **Settings → Devices & Services → MQTT**
5. Configure with:
   - Broker: `localhost` (or the HA host IP)
   - Port: `1883`
   - Username: (create one in HA Users)
   - Password: (choose one)

### Create an MQTT User:
1. **Settings → People → Users**
2. Click **Add User**
3. Username: `mqtt_user`
4. Password: `mqtt_pass` (change this!)
5. Toggle off "Administrator"

### Test MQTT from the Pi:
```bash
# Install mosquitto clients
sudo apt install -y mosquitto-clients

# Subscribe (in one terminal):
mosquitto_sub -h 192.168.1.100 -u mqtt_user -P mqtt_pass -t "ledpanel/#"

# Publish (in another terminal):
mosquitto_pub -h 192.168.1.100 -u mqtt_user -P mqtt_pass \
  -t "ledpanel/command" \
  -m '{"mode": "text", "text": "Hello!", "color": "#00FF00"}'

# If the subscribe terminal shows the message, MQTT is working
```

---

## Firewall Rules (if applicable)

The Pi needs two network paths:

| Destination | Port | Protocol | Purpose |
|---|---|---|---|
| HA/MQTT Broker | 1883 | TCP | MQTT messages |
| Colorlight 5A-75B | N/A | Raw Ethernet (L2) | Pixel data — no IP, no port, no firewall involvement |

The Colorlight communication is Layer 2 (below IP), so firewalls don't affect it. Only MQTT needs TCP port 1883 open.

If using UFW on the Pi:
```bash
sudo ufw allow 1883/tcp   # MQTT
sudo ufw allow 22/tcp     # SSH
```

---

## Software Deployment

See the assembly guide (03-ASSEMBLY-GUIDE.md) Phase 7, or simply:

```bash
cd ~/ledpanel
sudo bash install.sh
sudo nano /opt/ledpanel/config.yaml   # verify settings
sudo systemctl start ledpanel
sudo systemctl status ledpanel
journalctl -u ledpanel -f             # watch live logs
```

---

## Remote Access to the Pi

### SSH from Windows:
```
ssh pi@192.168.1.150
```
Or use PuTTY with the Pi's IP address.

### Copy files to Pi:
```
scp file.txt pi@192.168.1.150:~/
```

### View service logs:
```bash
journalctl -u ledpanel -f           # Live tail
journalctl -u ledpanel --since today # Today's logs
journalctl -u ledpanel -n 100       # Last 100 lines
```

### Restart the panel software:
```bash
sudo systemctl restart ledpanel
```
