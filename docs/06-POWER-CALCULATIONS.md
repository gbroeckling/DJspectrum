# Power Calculations and Electrical Safety

## P1.86 Panel Power Specifications

| Spec | Per Panel | Source |
|------|-----------|--------|
| Pixel pitch | 1.86mm | Manufacturer |
| Module size | 320mm x 160mm (0.0512 m2) | Manufacturer |
| Resolution | 172 x 86 = 14,792 pixels | Manufacturer |
| Input voltage | 5V DC | Manufacturer |
| Average power density | 250 W/m2 | Industry standard for indoor P1.86 |
| Maximum power density | 580 W/m2 | Industry standard (all white 100%) |

---

## Calculations

### Single Panel

```
Average power = 250 W/m2 x 0.0512 m2 = 12.8 W
Maximum power = 580 W/m2 x 0.0512 m2 = 29.7 W

Average current at 5V = 12.8W / 5V = 2.56 A
Maximum current at 5V = 29.7W / 5V = 5.94 A
```

### Two Panels (Your Setup)

```
Average power = 12.8W x 2 = 25.6 W
Maximum power = 29.7W x 2 = 59.4 W

Average current at 5V = 25.6W / 5V = 5.12 A
Maximum current at 5V = 59.4W / 5V = 11.88 A
```

### Colorlight 5A-75B

```
Power consumption = ~2W
Current at 5V = 0.4A
```

### Total System (2 panels + Colorlight)

```
Average total = 25.6W + 2W = 27.6W  (5.52A at 5V)
Maximum total = 59.4W + 2W = 61.4W  (12.28A at 5V)
```

---

## Power Supply Sizing

### The Rule: PSU should be rated at 120-150% of maximum load

```
Maximum load:     12.28A
At 120%:          14.74A
At 150%:          18.42A

Recommended PSU:  5V 20A (100W) — covers 150% with headroom
```

### Recommended PSU: Meanwell LRS-100-5

| Spec | Value |
|------|-------|
| Output voltage | 5V DC (adjustable 4.5-5.5V) |
| Output current | 20A max |
| Output power | 100W max |
| Input voltage | 85-264V AC (universal) |
| Efficiency | 86% typical |
| Operating temp | -30 to +70 C |
| Protections | Short circuit, overload, over-voltage |
| Size | 159 x 97 x 30mm |
| Weight | 280g |

### Alternative PSUs

| PSU | Rating | Price | Notes |
|-----|--------|-------|-------|
| Meanwell LRS-100-5 | 5V 20A 100W | ~$18 CAD | Best choice — reliable, compact |
| Meanwell LRS-150-5 | 5V 26A 130W | ~$22 CAD | More headroom if adding panels later |
| Generic 5V 20A | 5V 20A 100W | ~$10 CAD | Works but less reliable, more ripple |
| ATX PC PSU (repurposed) | 5V 20A+ | Free | Use the 5V rail, overkill but works |

---

## Typical vs. Maximum Power

In practice, your panels will rarely hit maximum power:

| Display Content | Approximate Load | Why |
|---|---|---|
| All black (display off) | ~0.5W | Only driver ICs idle power |
| Clock (white text, black bg) | ~3-5W | <5% of pixels lit |
| Scrolling text | ~5-8W | ~10% of pixels lit |
| Sensor dashboard | ~8-12W | ~20% of pixels lit |
| Color gradient | ~15-20W | Mixed colors, ~50% average |
| All white, full brightness | ~59W | 100% — never happens in practice |
| All red, full brightness | ~20W | Single color channel only |

**Your average real-world draw will be 5-15W** for typical HA dashboard use.

---

## Wire Gauge Selection

### Voltage Drop Calculation

At 5V, even small voltage drops matter. Panels need 4.5-5.5V to function.

```
Voltage drop = Current x Resistance
Resistance = (Wire length in feet x 2) / (Circular mils per AWG / 1000)

For 18 AWG, 1 foot round trip, 6A:
Resistance = 0.006385 ohms/foot x 2 feet = 0.01277 ohms
Voltage drop = 6A x 0.01277 = 0.077V  (acceptable)

For 18 AWG, 3 feet round trip, 6A:
Voltage drop = 6A x 0.03831 = 0.23V  (marginal)
```

### Wire Gauge Guide

| Wire Run | Current | Max Length | AWG | Notes |
|----------|---------|------------|-----|-------|
| PSU → Distribution point | 15A | 0.5m (2ft) | 14 AWG | Keep short! |
| Distribution → Panel | 6A | 0.5m (2ft) | 18 AWG | Adequate for short runs |
| Distribution → Panel | 6A | 1m (3ft) | 16 AWG | Use thicker for longer runs |
| Distribution → Colorlight | 0.5A | 1m (3ft) | 22 AWG | Minimal current |

**Keep all power wires as short as possible.** Mount the PSU close to the panels.

---

## Thermal Considerations

### Panel Heat

| Condition | Heat Output | Temperature Rise |
|-----------|-------------|-----------------|
| Typical use (10-20%) | 5-12W total | Barely warm |
| Sustained 50% | 15-20W total | Warm to touch |
| Full white 100% | ~59W total | Hot — needs ventilation |

### Cooling

- At typical dashboard use: **no cooling needed**
- If running bright content for extended periods: ensure 2cm gap behind panels for airflow
- Never mount in a sealed enclosure without ventilation
- The Colorlight 5A-75B runs cool at all times (<1W)
- Raspberry Pi may need a heatsink or small fan (comes with most Pi cases)

---

## Electrical Safety Checklist

Before first power-on, verify:

- [ ] All connections are tight (tug-test every wire)
- [ ] No bare copper exposed (heat-shrink all connections)
- [ ] PSU earth/ground is connected to AC ground wire
- [ ] 5V polarity is correct (test with multimeter)
- [ ] No shorts between +5V and GND rails (test with multimeter in continuity mode)
- [ ] Wire gauges are appropriate for current
- [ ] PSU is rated for at least 120% of maximum load
- [ ] Adequate ventilation around PSU and panels
- [ ] AC wiring is done by qualified person if unsure
- [ ] Panels are powered individually from the bus (not through each other)

---

## What Happens If...

| Scenario | Consequence | Prevention |
|----------|-------------|------------|
| Reversed 5V polarity | Instant destruction of panel driver ICs | Check with multimeter before connecting |
| Over-voltage (>5.5V) | Panel damage, possible fire | Don't adjust PSU pot above 5.2V |
| Under-voltage (<4.5V) | Dim display, flickering, garbled image | Use adequate wire gauge, short runs |
| Short circuit | PSU shuts down (protection), possible wire damage | Insulate all connections, check before power-on |
| Overloaded PSU | PSU overheats, shuts down, possible failure | Use 100W PSU for 60W max load |
| Panel power through ribbon cable | Ribbon cable melts, data corruption | Always wire power separately |
