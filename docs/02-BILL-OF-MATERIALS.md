# Bill of Materials (BOM)

## Core Components

| # | Component | Qty | Unit Price (CAD) | Total (CAD) | Source | Notes |
|---|-----------|-----|-------------------|-------------|--------|-------|
| 1 | P1.86 LED Panel Module 320x160mm (172x86px, 1/43 scan, ICN2038S, HUB75) | 2 | $41.38 | $82.76 | [AliExpress](https://www.aliexpress.com/item/1005009848265753.html) | Verify 1/43 scan and HUB75E connector |
| 2 | Colorlight 5A-75B V8.0 Receiving Card | 1 | $16.50 | $16.50 | [AliExpress](https://www.aliexpress.com/item/32844293219.html) | Must be V8.0 — older versions have bugs |
| 3 | Raspberry Pi 4 Model B (2GB minimum) | 1 | $50.00 | $50.00 | Local supplier / Amazon | 4GB or 8GB also fine. Pi 5 works too |
| 4 | Meanwell LRS-100-5 PSU (5V 20A, 100W) | 1 | $18.00 | $18.00 | [AliExpress](https://www.aliexpress.com/item/32995279823.html) or Amazon | Genuine Meanwell recommended |
| 5 | Raspberry Pi USB-C Power Supply (5V 3A) | 1 | $12.00 | $12.00 | Amazon / local | Official RPi PSU or any quality 5V/3A USB-C |
| 6 | MicroSD Card 16GB+ (Class 10 / A1) | 1 | $10.00 | $10.00 | Amazon | For Raspberry Pi OS |

**Core Subtotal: ~$189.26 CAD**

---

## Cables and Connectors

| # | Component | Qty | Unit Price (CAD) | Total (CAD) | Source | Notes |
|---|-----------|-----|-------------------|-------------|--------|-------|
| 7 | Cat6 Ethernet Cable (0.5m - 1m) | 1 | $5.00 | $5.00 | Amazon / local | Short run, Pi to 5A-75B. Cat5e minimum |
| 8 | 16-pin IDC HUB75 Ribbon Cable (30cm) | 2 | $0.00 | $0.00 | Included with panels | Usually 1 per panel. Buy spares if not |
| 9 | 18 AWG Silicone Wire — Red (1m) | 1 | $4.00 | $4.00 | Amazon / AliExpress | For 5V power distribution |
| 10 | 18 AWG Silicone Wire — Black (1m) | 1 | $4.00 | $4.00 | Amazon / AliExpress | For GND distribution |
| 11 | IEC C13 Power Cord (for PSU) | 1 | $5.00 | $5.00 | Amazon | AC mains to Meanwell PSU input |
| 12 | JST VH 3.96mm connectors (optional) | 4 | $0.50 | $2.00 | AliExpress | If panels use JST power connectors |

**Cables Subtotal: ~$20.00 CAD**

---

## Wiring and Distribution

| # | Component | Qty | Unit Price (CAD) | Total (CAD) | Source | Notes |
|---|-----------|-----|-------------------|-------------|--------|-------|
| 13 | Wago 221 Lever Connectors (5-port) | 2 | $2.00 | $4.00 | Amazon | One for +5V bus, one for GND bus |
| 14 | Ring Terminals / Fork Terminals (for PSU) | 4 | $0.25 | $1.00 | Amazon | Crimp onto wires for PSU screw terminals |
| 15 | Heat Shrink Tubing Assortment | 1 | $5.00 | $5.00 | Amazon | Insulate all crimp connections |
| 16 | Cable Ties (small, 100mm) | 1 pack | $3.00 | $3.00 | Amazon | Cable management |

**Wiring Subtotal: ~$13.00 CAD**

---

## Mounting and Enclosure (Optional)

| # | Component | Qty | Unit Price (CAD) | Total (CAD) | Source | Notes |
|---|-----------|-----|-------------------|-------------|--------|-------|
| 17 | Aluminum extrusion frame 20x20mm (1m) | 2 | $6.00 | $12.00 | AliExpress | Cut to 640mm and 160mm for side-by-side frame |
| 18 | M3 x 6mm screws + nuts | 20 | $0.10 | $2.00 | Amazon | Panel mounting holes are M3 |
| 19 | M3 standoffs 6mm (for Colorlight) | 4 | $0.15 | $0.60 | Amazon | Mount 5A-75B behind panels |
| 20 | 3M VHB double-sided tape | 1 roll | $8.00 | $8.00 | Amazon | Alternative to screws for mounting |
| 21 | 3D printed enclosure (optional) | 1 | $5.00 | $5.00 | Self-printed | For RPi + 5A-75B combo housing |

**Mounting Subtotal: ~$27.60 CAD**

---

## Tools Required (you likely own these)

| Tool | Purpose | Own it? |
|------|---------|---------|
| Phillips screwdriver (small) | PSU terminals, panel screws | [ ] |
| Wire strippers | Stripping 18 AWG | [ ] |
| Crimping tool (optional) | Fork/ring terminals | [ ] |
| Soldering iron (optional) | Only if panel power wires need soldering | [ ] |
| Multimeter | Verify 5V output before connecting panels | [ ] |
| Laptop/PC with Ethernet | One-time Colorlight config via LEDVision | [ ] |
| MicroSD card reader | Flash Raspberry Pi OS | [ ] |

---

## Project Cost Summary

| Category | Cost (CAD) |
|----------|------------|
| Core components | $189.26 |
| Cables and connectors | $20.00 |
| Wiring and distribution | $13.00 |
| Mounting (optional) | $27.60 |
| **TOTAL (with mounting)** | **$249.86** |
| **TOTAL (without mounting)** | **$222.26** |

---

## Recommended Suppliers

| Supplier | Best For | Shipping |
|----------|----------|----------|
| AliExpress | Panels, Colorlight card, Meanwell PSU | 2-4 weeks (free) |
| Amazon.ca | RPi, cables, Wago, tools, fast delivery | 1-2 days (Prime) |
| DigiKey / Mouser | Genuine Meanwell PSU if needed | 2-5 days |
| Seeed Studio | Raspberry Pi, dev boards | 1-2 weeks |

---

## Spare Parts (Recommended)

| Component | Qty | Why |
|-----------|-----|-----|
| 16-pin IDC ribbon cable | 2 extra | Fragile — pins bend easily |
| Colorlight 5A-75B | 1 extra | $12 insurance against dead card |
| 18 AWG wire (extra meter) | 1m each | For rework |
| Cat6 cable (spare) | 1 | Quick swap if cable fails |
