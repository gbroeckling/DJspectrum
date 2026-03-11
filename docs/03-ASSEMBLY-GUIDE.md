# Step-by-Step Assembly Guide

## Before You Start

**Read the entire guide before powering anything on.**

Estimated time: 1-2 hours (first time), 30 minutes (experienced)

### Safety Warnings

- The Meanwell PSU connects to AC mains (110/240V). If you are not comfortable wiring mains voltage, have an electrician do the AC side.
- Always disconnect AC power before touching PSU terminals.
- Double-check 5V polarity with a multimeter BEFORE connecting panels. Reversed polarity will destroy the LED driver ICs instantly.
- Never exceed 5.5V on the panel power inputs.

---

## Phase 1: Prepare the Power Supply

### Step 1.1 — Inspect the PSU
- Remove the Meanwell LRS-100-5 from packaging
- Identify the terminals:
  - **AC side** (left): L (Live), N (Neutral), GND (Earth)
  - **DC side** (right): +V (+5V), -V (GND), +V, -V (duplicated for convenience)
- There is a small voltage adjustment pot — leave it alone for now

### Step 1.2 — Wire the AC input
- Strip 8mm of insulation from your IEC power cord wires
- Connect to PSU screw terminals:
  - Brown wire → **L** (Live)
  - Blue wire → **N** (Neutral)
  - Green/Yellow wire → **GND** (Earth)
- Tighten screws firmly. Tug-test each wire.

### Step 1.3 — Prepare DC output wires
- Cut four lengths of 18 AWG wire:
  - 2x Red (30cm each) — for +5V
  - 2x Black (30cm each) — for GND
- Strip 8mm from one end of each wire
- Connect to PSU DC terminals:
  - Both Red wires → **+V** terminals
  - Both Black wires → **-V** terminals
- Tighten screws firmly

### Step 1.4 — Test the PSU (BEFORE connecting anything else)
- Plug in the AC cord
- Turn on the PSU (switch on side, if present)
- Use multimeter on DC mode: probe +V and -V terminals
- **Must read between 4.9V and 5.1V**
- If reading is off, use the small pot to adjust (tiny flathead screwdriver)
- Turn off and unplug when done

---

## Phase 2: Wire the Distribution Bus

### Step 2.1 — Set up Wago connectors
- Take one Wago 221 (5-port): this is your **+5V bus**
- Take another Wago 221 (5-port): this is your **GND bus**
- Insert one Red PSU wire into the +5V Wago
- Insert one Black PSU wire into the GND Wago

### Step 2.2 — Prepare panel power leads
- Cut four more lengths of 18 AWG wire (20-30cm each depending on layout):
  - 2x Red — for Panel 1 VCC and Panel 2 VCC
  - 2x Black — for Panel 1 GND and Panel 2 GND
- Strip both ends of each wire (8mm)
- Insert one end of each into the Wago bus:
  - Both Red wires → +5V Wago
  - Both Black wires → GND Wago

### Step 2.3 — Prepare Colorlight power leads
- Cut two short wires (15cm):
  - 1x Red, 1x Black
- Strip both ends
- Insert one end into the Wago buses
- The other ends will connect to the Colorlight 5A-75B screw terminals

---

## Phase 3: Connect the Colorlight 5A-75B

### Step 3.1 — Power the card
- Connect the Red wire from Wago → **5V+ screw terminal** on 5A-75B
- Connect the Black wire from Wago → **GND screw terminal** on 5A-75B
- Do NOT power on yet

### Step 3.2 — Connect Ethernet
- Plug one end of the Cat6 cable into the **RJ45 INPUT** port on the 5A-75B
- Leave the other end disconnected for now (will connect to Pi later)
- The second RJ45 port (OUTPUT) is for daisy-chaining multiple cards — leave it empty

---

## Phase 4: Connect the LED Panels

### Step 4.1 — Lay out panels
- Place both panels face-down on a clean, soft surface
- Arrange in your chosen layout:
  - Side-by-side: both panels in a row, HUB75 connectors accessible
  - Stacked: one on top of the other

### Step 4.2 — Power Panel 1
- Connect a Red wire from the Wago +5V bus → Panel 1 **VCC** connector
- Connect a Black wire from the Wago GND bus → Panel 1 **GND** connector
- Panel power connectors vary by manufacturer:
  - Some use JST VH 3.96mm connectors (plug in)
  - Some use screw terminals (strip and insert)
  - Some have bare wire pads (solder)

### Step 4.3 — Power Panel 2
- Same as Panel 1 — separate wires from the Wago bus
- Red → VCC, Black → GND

### Step 4.4 — Data chain: Colorlight → Panel 1
- Take a 16-pin IDC ribbon cable
- Connect one end to **J1** on the Colorlight 5A-75B
- Connect the other end to the **HUB75 IN** connector on Panel 1
- The ribbon has a keyed notch — it only fits one way

### Step 4.5 — Data chain: Panel 1 → Panel 2
- Take a second ribbon cable
- Connect one end to **HUB75 OUT** on Panel 1
- Connect the other end to **HUB75 IN** on Panel 2
- Panel 2's **HUB75 OUT** remains empty

---

## Phase 5: Prepare the Raspberry Pi

### Step 5.1 — Flash the SD card
- Download Raspberry Pi OS Lite (64-bit) from raspberrypi.com
- Flash to MicroSD using Raspberry Pi Imager
- In Imager settings, configure:
  - Hostname: `ledpanel-pi`
  - Username: `pi`, password: (choose one)
  - Enable SSH
  - Configure WiFi (for initial setup — optional if using switch)

### Step 5.2 — Boot and update
- Insert SD card into Pi
- Connect Pi to your network via Ethernet (to your router/switch)
- Connect USB-C power to Pi
- Wait 60 seconds for boot, then SSH in:
  ```
  ssh pi@ledpanel-pi.local
  ```
- Update the system:
  ```
  sudo apt update && sudo apt upgrade -y
  ```

### Step 5.3 — Connect Pi to Colorlight
- Plug the other end of the Cat6 cable into the **Pi's Ethernet port**
- If using a network switch: connect Pi, Colorlight, AND HA host all to the same Gigabit switch
- If direct: connect Pi Ethernet directly to Colorlight, use WiFi for HA network

---

## Phase 6: Power-On Sequence

**Follow this exact order to avoid damage:**

```
    POWER-ON ORDER:
    ───────────────
    1. Turn on 5V PSU          → panels and Colorlight get power
    2. Wait 3 seconds          → let everything stabilize
    3. Power on Raspberry Pi   → USB-C adapter

    POWER-OFF ORDER (reverse):
    ──────────────────────────
    1. SSH in: sudo shutdown now
    2. Wait for Pi green LED to stop blinking
    3. Unplug Pi USB-C
    4. Turn off 5V PSU
```

### Step 6.1 — Visual verification
After powering on:

| What to check | Expected | Problem if not |
|---|---|---|
| PSU green LED | On | Check AC input |
| Colorlight PWR LED | Green, solid | Check 5V wiring polarity |
| Colorlight NET LED | Off (no data yet) | — |
| Panel LEDs | All off (black) | Normal — no data yet |
| Pi red LED | Solid red | Check USB-C power |
| Pi green LED | Blinking | OS is booting |

---

## Phase 7: Software Deployment

### Step 7.1 — Copy project files to Pi
From your Windows PC:
```
scp -r C:\Users\Garry\ledpanel pi@ledpanel-pi.local:~/ledpanel
```

### Step 7.2 — Edit configuration
```
ssh pi@ledpanel-pi.local
nano ~/ledpanel/config.yaml
```
Update these values:
- `colorlight.interface` — usually `eth0` or `end0` (installer detects this)
- `mqtt.broker` — your Home Assistant IP address
- `mqtt.username` — your MQTT username
- `mqtt.password` — your MQTT password

### Step 7.3 — Run the installer
```
cd ~/ledpanel
sudo bash install.sh
```

### Step 7.4 — Test the display
```
sudo /opt/ledpanel/venv/bin/python3 /opt/ledpanel/main.py --test
```
You should see a color gradient test pattern on both panels.

### Step 7.5 — Start the service
```
sudo systemctl start ledpanel
sudo systemctl status ledpanel
```

If status shows "active (running)" — you're done!

---

## Phase 8: Mounting (Optional)

### Option A: Wall mount with aluminum frame
1. Cut 20x20mm aluminum extrusion to size
2. Assemble rectangular frame with corner brackets
3. Mount panels to frame with M3 screws through panel mounting holes
4. Mount 5A-75B behind panels with M3 standoffs
5. Mount PSU behind or below the frame
6. Route all cables behind the frame
7. Mount frame to wall with appropriate hardware

### Option B: Desk stand
1. 3D print an angled stand (plenty of designs on Thingiverse)
2. Secure panels with M3 screws or VHB tape
3. Hide electronics behind the stand

### Option C: Quick and dirty
1. VHB tape panels to desired surface
2. Tape Colorlight card behind panels
3. Set PSU on shelf below
4. Cable-tie everything neat
