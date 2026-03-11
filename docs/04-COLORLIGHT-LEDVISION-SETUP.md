# Colorlight 5A-75B Configuration with LEDVision

## Overview

The Colorlight 5A-75B must be configured **once** to match your specific LED panel specs. This configuration is stored in the card's flash memory and persists across power cycles. After this one-time setup, the card is ready to receive pixel data from the Raspberry Pi.

**You need a Windows PC for this step.** (LEDVision is Windows-only.)

---

## What You Need

- Windows 10/11 PC with a **Gigabit Ethernet port**
- Colorlight 5A-75B connected and powered (5V)
- One P1.86 panel connected to J1 (for visual verification)
- Cat6 cable from PC to the 5A-75B's RJ45 INPUT port
- LEDVision software (free download)

---

## Step 1: Download and Install LEDVision

1. Go to: https://www.colorlight-led.com/download/
2. Download "LEDVision" (latest version, usually V3.x or V4.x)
3. Install with default options
4. Launch LEDVision

---

## Step 2: Network Configuration on Windows PC

Before LEDVision can see the card, your PC's Ethernet must be on the same Layer 2 network:

1. Open **Settings → Network & Internet → Ethernet → Change adapter options**
2. Right-click your Ethernet adapter → **Properties**
3. Select **Internet Protocol Version 4 (TCP/IPv4)** → Properties
4. Set a static IP:
   ```
   IP address:     192.168.0.200
   Subnet mask:    255.255.255.0
   Gateway:        (leave blank)
   DNS:            (leave blank)
   ```
5. Click OK

**Verify Gigabit link:**
- Open Command Prompt: `wmic NIC where NetEnabled=true get Name,Speed`
- Your Ethernet adapter should show `1000000000` (1 Gbps)

---

## Step 3: Connect to the 5A-75B

1. In LEDVision, go to **Control → Screen Management** (or press F5)
2. Click **Scan Receivers** or **Detect**
3. The 5A-75B should appear in the list
4. If not found:
   - Check Ethernet cable and link LEDs
   - Verify 5A-75B power LED is on
   - Try a different Ethernet port on your PC
   - Disable Windows Firewall temporarily

---

## Step 4: Configure the Receiver Card

### 4.1 — Set Screen Parameters

In the Screen Management window:

| Parameter | Value | Why |
|-----------|-------|-----|
| Module Width | **172** | P1.86 panel pixel width |
| Module Height | **86** | P1.86 panel pixel height |
| Scan Type | **1/43** | Your panel's scan rate (86 rows / 2 = 43) |
| Data Polarity | **Positive** | Default for most panels |
| OE Polarity | **Negative** | Default for most panels |
| Driver IC | **ICN2038S** | Your panel's driver chip |

### 4.2 — Set Output Port Configuration

| Parameter | Value | Why |
|-----------|-------|-----|
| Output Port | **J1** | We connect panels to port J1 |
| Cascade Direction | **Left to Right** | Panel 1 → Panel 2 |
| Number of Panels | **2** | Two panels daisy-chained |
| Horizontal panels | **2** | Side-by-side layout |
| Vertical panels | **1** | Single row |

For stacked layout (172x172), change to:
- Horizontal panels: **1**
- Vertical panels: **2**

### 4.3 — Color and Brightness

| Parameter | Value |
|-----------|-------|
| Color Temperature | **6500K** (default daylight) |
| Brightness | **100%** (software will control this) |
| Gamma | **2.2** (standard) |
| Color Depth | **16-bit** |

---

## Step 5: Smart Module Setup (if available)

Some versions of LEDVision have "Smart Module" which auto-detects panel specs:

1. Go to **Control → Smart Module**
2. Connect ONE panel to J1
3. Click **Auto Detect**
4. LEDVision reads the panel's onboard chip and fills in all parameters
5. Verify the values match the table in Step 4
6. If auto-detect works, click **Apply**

---

## Step 6: Test the Configuration

1. In LEDVision, go to **Control → Send Test Pattern**
2. Select "Color Bars" or "Gradient"
3. Click Send
4. Both panels should display the test pattern correctly
5. Check for:
   - Correct colors (no R/G/B swaps)
   - Full resolution (no missing rows or columns)
   - Even brightness across both panels
   - No flickering or artifacts

### Common Visual Problems

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Wrong colors (red shows as blue) | RGB order wrong | Swap R/G/B in module settings |
| Half the panel is garbled | Wrong scan rate | Change scan from 1/43 to 1/32 or auto-detect |
| Flickering | Wrong OE polarity | Toggle OE Polarity |
| Very dim | Wrong data polarity | Toggle Data Polarity |
| Panel 2 mirrors Panel 1 | Cascade not set | Set cascade to 2 panels |
| One panel works, other is black | Bad ribbon cable | Swap ribbon cable, check seated fully |

---

## Step 7: Save to Receiver Flash

**This is the critical step — saves config permanently to the card:**

1. Click **Save to Receiver** (or "Write to Hardware")
2. Wait for confirmation message
3. The 5A-75B now remembers this config forever (even after power loss)

---

## Step 8: Verify Saved Config

1. Power-cycle the 5A-75B (unplug 5V, wait 5 seconds, replug)
2. In LEDVision, click **Read from Receiver**
3. All settings should match what you saved
4. The PWR LED should be green, panels should be black (no data = black)

---

## Step 9: Disconnect Windows PC

1. Close LEDVision
2. Unplug the Cat6 cable from your PC
3. Restore your PC's Ethernet to DHCP (Settings → Network → Ethernet → DHCP)
4. Connect the Cat6 cable to the Raspberry Pi instead

The 5A-75B is now configured and ready to receive pixel data from the Pi software.

---

## Quick Reference: Panel Specs to Enter

```
┌─────────────────────────────────────────────┐
│  P1.86 LED Panel Configuration Summary      │
│                                             │
│  Pixel Pitch:     1.86mm                    │
│  Module Size:     320mm x 160mm             │
│  Resolution:      172 x 86 pixels           │
│  Scan Rate:       1/43                      │
│  Driver IC:       ICN2038S                  │
│  Interface:       HUB75E (16-pin)           │
│  Input Voltage:   5V DC                     │
│  Max Current:     ~6A per panel             │
│  Refresh Rate:    3840Hz                    │
│  Color Depth:     16-bit (65,536 colors)    │
│                                             │
│  Two panels side-by-side:                   │
│  Total: 344 x 86 = 29,584 pixels           │
│                                             │
│  Two panels stacked:                        │
│  Total: 172 x 172 = 29,584 pixels          │
└─────────────────────────────────────────────┘
```

---

## Alternative: LEDVision Not Working?

If you cannot get LEDVision to connect:

1. Try **Colorlight LEDVISION Express** (simpler version)
2. Try the **Colorlight iLEDDisplay** mobile app (iOS/Android)
   - Requires a Colorlight sending card (S2) as intermediary
   - More expensive but easier for some users
3. Try an older version of LEDVision (V2.x works with V8.0 cards)
4. Ask the panel seller — many AliExpress sellers will pre-configure the 5A-75B if you send them your panel specs before shipping
