# Wiring Diagrams — LED Panel Controller

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          COMPLETE SYSTEM LAYOUT                             │
│                                                                             │
│  ┌────────────┐    Cat6 GbE    ┌──────────────┐   HUB75    ┌───────────┐  │
│  │Raspberry Pi├═══════════════►│ Colorlight   ├═══════════►│  Panel 1  │  │
│  │  4 or 5    │   (data only)  │   5A-75B     │  ribbon    │  P1.86    │  │
│  └─────┬──────┘                │  (V8.0)      │            │ 172x86px  │  │
│        │                       └──────┬───────┘            └────┬──┬───┘  │
│    USB-C 5V/3A                        │                  HUB75  │  │      │
│    (separate                     ┌────┴────┐            ribbon  │  │      │
│     adapter)                     │  5V IN  │                    │  │      │
│                                  │  GND IN │           ┌────────┘  │      │
│                                  └────┬────┘           │     5V+   │      │
│                                       │                │     GND   │      │
│                              ┌────────┴────────┐       │           │      │
│                              │   5V 20A PSU    │       │           │      │
│                              │ (Meanwell       │───────┤           │      │
│                              │  LRS-100-5)     │       │   ┌──────┴───┐  │
│                              │                 │       │   │  Panel 2  │  │
│                              │  AC IN ◄── 110/ │       │   │  P1.86    │  │
│                              │          240V   │       │   │ 172x86px  │  │
│                              │                 │───────┼───┤           │  │
│                              └─────────────────┘  5V+  │   └──────────┘  │
│                                                   GND  │                  │
│                                                        │                  │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## Diagram 1: Power Supply Wiring

```
                    ┌─────────────────────────────────────────┐
                    │         MEANWELL LRS-100-5              │
                    │         (or equivalent 5V 20A)          │
                    │                                         │
   AC MAINS         │  ┌─────┐  ┌─────┐  ┌─────┐            │
   110/240V ───────►│  │  L  │  │  N  │  │ GND │            │
                    │  │(live)│  │(neu)│  │(earth)           │
                    │  └──┬──┘  └──┬──┘  └──┬──┘            │
                    │     │        │        │  earth/chassis  │
                    │                                         │
                    │  DC OUTPUT SIDE:                        │
                    │                                         │
                    │  ┌──────┐  ┌──────┐                    │
                    │  │ +V   │  │ -V   │                    │
                    │  │ (5V) │  │ (GND)│                    │
                    │  └──┬───┘  └──┬───┘                    │
                    └─────┼─────────┼────────────────────────┘
                          │         │
             ┌────────────┴─────────┴────────────┐
             │        DISTRIBUTION POINT          │
             │    (Wago connectors or bus bar)     │
             │                                    │
             │  +5V rail              GND rail     │
             │    │                     │          │
             │    ├──► Colorlight 5V+   ├──► Colorlight GND
             │    │                     │          │
             │    ├──► Panel 1 VCC      ├──► Panel 1 GND
             │    │                     │          │
             │    └──► Panel 2 VCC      └──► Panel 2 GND
             │                                    │
             └────────────────────────────────────┘


WIRE GAUGE TABLE:
┌──────────────────────┬───────────┬──────────┬────────────┐
│ Connection           │ Max Amps  │ Min Wire │ Recommended│
├──────────────────────┼───────────┼──────────┼────────────┤
│ PSU → Distribution   │ 20A       │ 14 AWG   │ 12 AWG     │
│ Distribution → Panel │ 6A each   │ 18 AWG   │ 16 AWG     │
│ Distribution → 5A75B │ 1A        │ 22 AWG   │ 20 AWG     │
└──────────────────────┴───────────┴──────────┴────────────┘
```

---

## Diagram 2: Colorlight 5A-75B Connections

```
┌─────────────────────────────────────────────────────────────┐
│                   COLORLIGHT 5A-75B (V8.0)                  │
│                   (Top-down view)                            │
│                                                             │
│   ┌─────────┐    ┌─────────┐                                │
│   │ RJ45    │    │ RJ45    │                                │
│   │ INPUT   │    │ OUTPUT  │  ◄── Not used (for daisy-      │
│   │         │    │         │      chaining multiple cards)   │
│   └────┬────┘    └─────────┘                                │
│        │                                                    │
│   From Raspberry Pi                                         │
│   (Gigabit Ethernet)                                        │
│                                                             │
│   ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐ ┌──┐                │
│   │J1│ │J2│ │J3│ │J4│ │J5│ │J6│ │J7│ │J8│  HUB75 outputs  │
│   └┬─┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘ └──┘                │
│    │                                                        │
│    │ ◄── Connect your panels to J1                          │
│    │     (J2-J8 unused for 2-panel setup)                   │
│                                                             │
│   ┌────────┐  ┌────────┐                                    │
│   │  5V+   │  │  GND   │  ◄── Screw terminals              │
│   │  IN    │  │  IN    │      from 5V PSU                   │
│   └────────┘  └────────┘                                    │
│                                                             │
│   LED indicators:                                           │
│   [PWR] = Green when powered                                │
│   [NET] = Blinking when receiving Ethernet data             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Diagram 3: HUB75 Panel Daisy Chain

```
FROM COLORLIGHT J1
       │
       │  16-pin IDC ribbon cable (~30cm, comes with panels)
       │
       ▼
┌─────────────────────────────────────┐
│         P1.86 PANEL #1              │
│         172 x 86 pixels             │
│         320mm x 160mm               │
│                                     │
│  ┌──────────┐       ┌──────────┐   │
│  │ HUB75    │       │ HUB75    │   │
│  │   IN     │       │   OUT    │   │
│  │ (input)  │       │ (output) │   │
│  └──────────┘       └─────┬────┘   │
│                            │        │
│  ┌────┐  ┌────┐           │        │
│  │VCC │  │GND │           │        │
│  │+5V │  │ 0V │           │        │
│  └──┬─┘  └──┬─┘           │        │
│     │       │              │        │
└─────┼───────┼──────────────┼────────┘
      │       │              │
  From PSU  From PSU         │ 16-pin IDC ribbon cable
  (+5V)     (GND)            │
                             ▼
┌────────────────────────────────────┐
│         P1.86 PANEL #2             │
│         172 x 86 pixels            │
│         320mm x 160mm              │
│                                    │
│  ┌──────────┐       ┌──────────┐  │
│  │ HUB75    │       │ HUB75    │  │
│  │   IN     │       │   OUT    │  │
│  │ (input)  │       │ (unused) │  │
│  └──────────┘       └──────────┘  │
│                                    │
│  ┌────┐  ┌────┐                   │
│  │VCC │  │GND │                   │
│  │+5V │  │ 0V │                   │
│  └──┬─┘  └──┬─┘                   │
│     │       │                      │
└─────┼───────┼──────────────────────┘
      │       │
  From PSU  From PSU
  (+5V)     (GND)


    !! IMPORTANT !!
    ────────────────────────────────────────────────
    Each panel gets its OWN power wires from the PSU.
    Do NOT try to power Panel 2 through Panel 1.
    The HUB75 ribbon cable carries DATA ONLY.
    ────────────────────────────────────────────────
```

---

## Diagram 4: HUB75 Connector Pinout Reference

```
    HUB75E (16-pin IDC) — Looking at the PANEL INPUT socket

         Pin 1                          Pin 2
        ┌──────┐                      ┌──────┐
        │  R1  │──── Red (top half)   │  G1  │──── Green (top half)
        └──────┘                      └──────┘
        ┌──────┐                      ┌──────┐
        │  B1  │──── Blue (top half)  │ GND  │──── Ground
        └──────┘                      └──────┘
        ┌──────┐                      ┌──────┐
        │  R2  │──── Red (bot half)   │  G2  │──── Green (bot half)
        └──────┘                      └──────┘
        ┌──────┐                      ┌──────┐
        │  B2  │──── Blue (bot half)  │  E   │──── Row addr E (for 1/32+)
        └──────┘                      └──────┘
        ┌──────┐                      ┌──────┐
        │  A   │──── Row address A    │  B   │──── Row address B
        └──────┘                      └──────┘
        ┌──────┐                      ┌──────┐
        │  C   │──── Row address C    │  D   │──── Row address D
        └──────┘                      └──────┘
        ┌──────┐                      ┌──────┐
        │ CLK  │──── Clock            │ LAT  │──── Latch
        └──────┘                      └──────┘
        ┌──────┐                      ┌──────┐
        │ OE   │──── Output Enable    │ GND  │──── Ground
        └──────┘                      └──────┘

    NOTE: You do NOT need to wire these pins manually.
    The ribbon cable handles everything. This is for
    reference only if you need to debug.
```

---

## Diagram 5: Physical Layout Options

```
OPTION A: SIDE-BY-SIDE (344 x 86 pixels — wide banner)
┌──────────────────────┬──────────────────────┐
│                      │                      │
│    Panel 1           │    Panel 2           │
│    172 x 86          │    172 x 86          │
│    320mm             │    320mm             │
│                      │                      │
│    160mm             │    160mm             │
│                      │                      │
└──────────────────────┴──────────────────────┘
         640mm total (25.2 inches)
         160mm tall (6.3 inches)


OPTION B: STACKED (172 x 172 pixels — square)
┌──────────────────────┐
│                      │
│    Panel 1           │
│    172 x 86          │
│    320mm x 160mm     │
│                      │
├──────────────────────┤
│                      │
│    Panel 2           │
│    172 x 86          │
│    320mm x 160mm     │
│                      │
└──────────────────────┘
   320mm wide (12.6 inches)
   320mm tall (12.6 inches)


To change: edit config.yaml → display → layout: "horizontal" or "vertical"
```

---

## Diagram 6: Network Topology

```
┌────────────────────────────────────────────────────────────┐
│                    YOUR HOME NETWORK                        │
│                                                            │
│   ┌──────────┐                                             │
│   │  Router   │                                            │
│   │ (DHCP)   │                                             │
│   └────┬─────┘                                             │
│        │                                                   │
│   ┌────┴─────────────────────────────┐                     │
│   │        Network Switch            │                     │
│   │     (Gigabit required!)          │                     │
│   └─┬──────┬──────┬──────┬──────────┘                     │
│     │      │      │      │                                 │
│     │      │      │      │                                 │
│   ┌─┴──┐ ┌─┴──┐ ┌─┴────┐ ┌┴──────────┐                   │
│   │HA  │ │PC  │ │Rasp  │ │Colorlight │                   │
│   │Host│ │    │ │Pi 4  │ │ 5A-75B    │                   │
│   │    │ │    │ │      │ │           │                   │
│   │MQTT│ │    │ │sends │ │receives   │──► LED Panels     │
│   │    │ │    │ │pixels│ │pixels     │                   │
│   └────┘ └────┘ └──────┘ └───────────┘                   │
│                                                            │
│   IP examples:                                             │
│   HA Host:     192.168.1.100 (runs MQTT broker)            │
│   Pi:          192.168.1.150 (runs ledpanel software)      │
│   Colorlight:  No IP (Layer 2 raw Ethernet, no TCP/IP)     │
│                                                            │
└────────────────────────────────────────────────────────────┘


    ALTERNATIVE: Direct connection (no switch needed)
    ─────────────────────────────────────────────────

    ┌─────────┐                      ┌──────────────┐
    │ Pi 4    │                      │  Colorlight  │
    │         │                      │   5A-75B     │
    │  eth0 ══╪══ Cat6 direct ══════╪══ RJ45 IN    │──► Panels
    │  wlan0 ─┼─ WiFi to home net   │              │
    │         │                      │              │
    └─────────┘                      └──────────────┘

    Pi uses WiFi for HA/MQTT, wired Ethernet for panel data.
    Works but WiFi adds latency to HA commands. Switch is better.


    !! CRITICAL !!
    ──────────────────────────────────────────────────
    The Colorlight 5A-75B requires GIGABIT Ethernet.
    It will NOT work with 100Mbps switches or cables.
    Use Cat5e or Cat6 cables. Verify link speed:
       ethtool eth0 | grep Speed   →  must show 1000Mb/s
    ──────────────────────────────────────────────────
```

---

## Diagram 7: Complete Back-of-Panel Wiring

```
    BACK VIEW (looking at rear of mounted panels)

    ┌───────────────────────────────────────────────────────────────┐
    │                                                               │
    │   PANEL 2 (rear)                    PANEL 1 (rear)            │
    │   ┌─────────────────────┐          ┌─────────────────────┐   │
    │   │                     │          │                     │   │
    │   │  [VCC][GND]         │          │  [VCC][GND]         │   │
    │   │    │    │           │          │    │    │           │   │
    │   │    │    │   [IN]    │          │    │    │   [IN]    │   │
    │   │    │    │    ▲      │          │    │    │    ▲      │   │
    │   │    │    │    │      │          │    │    │    │      │   │
    │   │    │    │    │      │          │    │    │    │      │   │
    │   │    │    │  ribbon   │          │    │    │  ribbon   │   │
    │   │    │    │  from     │          │    │    │  from     │   │
    │   │    │    │  Panel 1  │          │    │    │  5A-75B   │   │
    │   │    │    │   OUT     │          │    │    │   J1      │   │
    │   │    │    │           │          │    │    │           │   │
    │   │    │    │  [OUT]    │          │    │    │  [OUT]────┼───┼──► ribbon
    │   │    │    │ (unused)  │          │    │    │  to P2 IN │   │
    │   │    │    │           │          │    │    │           │   │
    │   └────┼────┼───────────┘          └────┼────┼───────────┘   │
    │        │    │                           │    │               │
    │        │    │                           │    │               │
    │   ┌────┴────┴───────────────────────────┴────┴────┐         │
    │   │                                               │         │
    │   │          WAGO LEVER CONNECTORS                │         │
    │   │          (or terminal block)                  │         │
    │   │                                               │         │
    │   │   +5V bus ════════════════════════ ◄── PSU +V │         │
    │   │   GND bus ════════════════════════ ◄── PSU -V │         │
    │   │                                               │         │
    │   └───────────────────────────────────────────────┘         │
    │                                                               │
    │   Colorlight 5A-75B mounted nearby (double-sided tape / M3)  │
    │   ┌──────────────┐                                           │
    │   │  [RJ45 IN]◄──┼── Cat6 from Raspberry Pi                 │
    │   │  [5V+][GND]◄─┼── From 5V bus                            │
    │   │  [J1] ───────┼──► Ribbon to Panel 1 IN                  │
    │   └──────────────┘                                           │
    │                                                               │
    └───────────────────────────────────────────────────────────────┘
```
