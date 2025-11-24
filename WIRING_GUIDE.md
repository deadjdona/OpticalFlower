# Complete Wiring Guide

## Overview

This guide provides comprehensive wiring diagrams for all supported configurations. Choose the setup that matches your hardware and use case.

---

## Pin Reference - Raspberry Pi Zero / 2W

```
Physical Pin Layout (40-pin GPIO Header)
                                        
    3V3  [ 1] [ 2]  5V     ← Power In (from BEC)
I2C SDA  [ 3] [ 4]  5V     ← Power In (alternate)
I2C SCL  [ 5] [ 6]  GND    ← Ground
   GPIO7 [ 7] [ 8]  GPIO14 ← UART TX (GPS emulation)
    GND  [ 9] [10]  GPIO15 ← UART RX (telemetry)
  GPIO17 [11] [12]  GPIO18
  GPIO27 [13] [14]  GND
  GPIO22 [15] [16]  GPIO23
    3V3  [17] [18]  GPIO24
SPI MOSI [19] [20]  GND
SPI MISO [21] [22]  GPIO25
SPI SCLK [23] [24]  SPI CE0 ← PMW3901 CS
    GND  [25] [26]  SPI CE1
    ...
```

**Key Pins:**
- **Pin 1 (3.3V)**: Sensor power
- **Pin 2/4 (5V)**: Pi power from BEC
- **Pin 3 (GPIO2)**: I2C SDA (Caddx Infra 256)
- **Pin 5 (GPIO3)**: I2C SCL (Caddx Infra 256)
- **Pin 6/9/14/20/25 (GND)**: Ground connections
- **Pin 8 (GPIO14)**: UART TX (GPS to FC)
- **Pin 10 (GPIO15)**: UART RX (Telemetry from FC)
- **Pin 19/21/23/24**: SPI (PMW3901)

---

## Configuration 1: Basic Indoor Setup

**Use Case**: Simple indoor hover, position hold 0-10m  
**Flight Controller**: Any (Betaflight, iNav, ArduPilot, PX4)  
**Sensor**: Caddx Infra 256 (I2C) or PMW3901 (SPI)

### Wiring Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                  RASPBERRY PI ZERO / 2W                        │
│                                                                │
│  Pin 1  [3.3V] ───────┐                                       │
│  Pin 2  [5V]   ────────────────────────────┐                 │
│  Pin 3  [SDA]  ──────────────┐             │                 │
│  Pin 5  [SCL]  ────────────┐ │             │                 │
│  Pin 6  [GND]  ──────────┐ │ │             │                 │
│  Pin 8  [TX]   ────────┐ │ │ │             │                 │
│                        │ │ │ │             │                 │
└────────────────────────┼─┼─┼─┼─────────────┼─────────────────┘
                         │ │ │ │             │
                         │ │ │ │             │  Power
                         │ │ │ │             │  ──────
                         │ │ │ │             │
                         │ │ │ │         ┌───┴────┐
                         │ │ │ │         │  BEC   │ 5V 2A+
                         │ │ │ │         │ 5V/GND │
                         │ │ │ │         └───┬────┘
                         │ │ │ │             │
                         │ │ │ │             │
    Sensor               │ │ │ │         Flight Controller
    ──────               │ │ │ │         ──────────────────
                         │ │ │ │
┌────────────────────┐   │ │ │ │     ┌──────────────────────┐
│ Caddx Infra 256    │   │ │ │ │     │  Betaflight / iNav   │
│   (I2C Sensor)     │   │ │ │ │     │   ArduPilot / PX4    │
│                    │   │ │ │ │     │                      │
│  VCC ──────────────┼───┘ │ │ │     │  GPS RX ←───────────┼───┘
│  GND ──────────────┼─────┘ │ │     │  GND ───────────────┼─────┐
│  SDA ──────────────┼───────┘ │     │  5V BEC ────────────┼───┐ │
│  SCL ──────────────┼─────────┘     │                      │   │ │
│                    │                └──────────────────────┘   │ │
└────────────────────┘                                           │ │
                                                                 │ │
                                                Common Ground ───┴─┘
```

### Connections Table

| Raspberry Pi | → | Component | Function |
|--------------|---|-----------|----------|
| Pin 1 (3.3V) | → | Sensor VCC | Sensor power |
| Pin 3 (SDA) | → | Sensor SDA | I2C data |
| Pin 5 (SCL) | → | Sensor SCL | I2C clock |
| Pin 6 (GND) | → | Sensor GND, FC GND | Common ground |
| Pin 2 (5V) | ← | BEC 5V | Pi power |
| Pin 8 (TX) | → | FC GPS RX | NMEA GPS data |

### Configuration

```json
{
  "sensor": {"type": "caddx_infra256"},
  "tracker": {"max_altitude": 10.0},
  "altitude": {"enabled": false, "type": "static"},
  "gps_emulation": {
    "enabled": true,
    "protocol": "nmea",
    "port": "/dev/ttyAMA0"
  }
}
```

**Power Requirements:**
- Raspberry Pi Zero W: 500mA @ 5V
- Caddx Infra 256: 15mA @ 3.3V
- **Total: 1A BEC minimum**

---

## Configuration 2: Outdoor 30-50m (Betaflight/iNav)

**Use Case**: Outdoor flights with barometer integration  
**Flight Controller**: Betaflight or iNav  
**Sensor**: Caddx Infra 256 (I2C)  
**Altitude**: 30-50m operational, 100m max

### Wiring Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                  RASPBERRY PI ZERO 2W                          │
│                                                                │
│  Pin 1  [3.3V] ───────┐                                       │
│  Pin 2  [5V]   ────────────────────────────┐                 │
│  Pin 3  [SDA]  ──────────────┐             │                 │
│  Pin 5  [SCL]  ────────────┐ │             │                 │
│  Pin 6  [GND]  ──────────┐ │ │             │                 │
│  Pin 8  [TX]   ────────┐ │ │ │             │                 │
│  Pin 10 [RX]   ──────┐ │ │ │ │             │                 │
│                      │ │ │ │ │             │                 │
│  USB Port ─────┐     │ │ │ │ │             │                 │
│                │     │ │ │ │ │             │                 │
└────────────────┼─────┼─┼─┼─┼─┼─────────────┼─────────────────┘
                 │     │ │ │ │ │             │
                 │     │ │ │ │ │             │
                 │     │ │ │ │ │         ┌───┴────┐
                 │     │ │ │ │ │         │  BEC   │ 5V 2A+
                 │     │ │ │ │ │         │ 5V/GND │
                 │     │ │ │ │ │         └───┬────┘
                 │     │ │ │ │ │             │
  Alt Source     │     │ │ │ │ │             │
  ──────────     │     │ │ │ │ │     Flight Controller
                 │     │ │ │ │ │     ──────────────────
  Option A: USB  │     │ │ │ │ │
     ┌───────────┘     │ │ │ │ │     ┌──────────────────────┐
     │                 │ │ │ │ │     │    Betaflight FC     │
     │  ┌──────────┐   │ │ │ │ │     │                      │
     └─→│USB Cable │───┼─┼─┼─┼─┼────→│  USB ←── Telemetry   │
        └──────────┘   │ │ │ │ │     │  GPS RX ←─────────────┼───┘
                       │ │ │ │ │     │  GND ────────────────┼─────┐
  Option B: UART       │ │ │ │ │     │  5V BEC ─────────────┼───┐ │
                       │ │ │ │ │     │                      │   │ │
 Sensor                │ │ │ │ │     │  UART4 TX (opt) ─────┼─┐ │ │
 ──────                │ │ │ │ │     └──────────────────────┘ │ │ │
                       │ │ │ │ │                              │ │ │
┌────────────────────┐ │ │ │ │ │                              │ │ │
│ Caddx Infra 256    │ │ │ │ │ │                              │ │ │
│   (I2C Sensor)     │ │ │ │ │ └──────────────────────────────┘ │ │
│                    │ │ │ │ │                                  │ │
│  VCC ──────────────┼─┘ │ │ │                                  │ │
│  SDA ──────────────┼───┘ │ │                                  │ │
│  SCL ──────────────┼─────┘ │                                  │ │
│  GND ──────────────┼───────┴──────────────────────────────────┴─┘
└────────────────────┘
```

### Connections Table

| Raspberry Pi | → | Component | Function |
|--------------|---|-----------|----------|
| Pin 1 (3.3V) | → | Sensor VCC | Sensor power |
| Pin 3 (SDA) | → | Sensor SDA | I2C data |
| Pin 5 (SCL) | → | Sensor SCL | I2C clock |
| Pin 2 (5V) | ← | BEC 5V | Pi power |
| Pin 6 (GND) | ↔ | Common GND | All grounds |
| Pin 8 (TX) | → | FC GPS RX | NMEA GPS data |
| **USB** or **Pin 10 (RX)** | ← | FC USB or UART4 TX | MAVLink telemetry |

### Configuration

```json
{
  "sensor": {"type": "caddx_infra256"},
  "tracker": {"max_altitude": 100.0, "initial_height": 2.0},
  "altitude": {
    "enabled": true,
    "type": "mavlink",
    "connection": "/dev/ttyUSB0",
    "baudrate": 115200
  },
  "gps_emulation": {
    "enabled": true,
    "protocol": "nmea",
    "port": "/dev/ttyAMA0",
    "baudrate": 115200
  },
  "stabilizer": {
    "altitude_adaptive": true,
    "high_altitude_damping_boost": 3.0
  }
}
```

**Power Requirements:**
- Raspberry Pi Zero 2W: 800mA @ 5V
- Sensor: 15mA @ 3.3V
- **Total: 2A BEC minimum**

---

## Configuration 3: Outdoor Missions (ArduPilot/PX4)

**Use Case**: Autonomous missions up to 100m  
**Flight Controller**: ArduPilot or PX4  
**Sensor**: Caddx Infra 256 (I2C)  
**Altitude**: 50m recommended, 100m max

### Wiring Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                  RASPBERRY PI ZERO 2W                          │
│                                                                │
│  Pin 1  [3.3V] ───────┐                                       │
│  Pin 2  [5V]   ────────────────────────────┐                 │
│  Pin 3  [SDA]  ──────────────┐             │                 │
│  Pin 5  [SCL]  ────────────┐ │             │                 │
│  Pin 6  [GND]  ──────────┐ │ │             │                 │
│  Pin 8  [TX]   ────────┐ │ │ │             │                 │
│  Pin 10 [RX]   ──────┐ │ │ │ │             │                 │
│                      │ │ │ │ │             │                 │
└──────────────────────┼─┼─┼─┼─┼─────────────┼─────────────────┘
                       │ │ │ │ │             │
                       │ │ │ │ │             │
                       │ │ │ │ │         ┌───┴────┐
                       │ │ │ │ │         │  BEC   │ 5V 3A
                       │ │ │ │ │         │ 5V/GND │
                       │ │ │ │ │         └───┬────┘
                       │ │ │ │ │             │
                       │ │ │ │ │             │
  Sensor               │ │ │ │ │     Flight Controller
  ──────               │ │ │ │ │     ──────────────────
                       │ │ │ │ │
┌────────────────────┐ │ │ │ │ │     ┌──────────────────────┐
│ Caddx Infra 256    │ │ │ │ │ │     │   ArduPilot / PX4    │
│   (I2C Sensor)     │ │ │ │ │ │     │                      │
│                    │ │ │ │ │ │     │  TELEM2 / GPS Port:  │
│  VCC ──────────────┼─┘ │ │ │ │     │    RX ←──────────────┼───┘
│  SDA ──────────────┼───┘ │ │ │     │    TX ───────────────┼───┐
│  SCL ──────────────┼─────┘ │ │     │  GND ────────────────┼─┐ │
│  GND ──────────────┼───────┴─┴─────┼  5V BEC ─────────────┼─┼─┼─┐
│                    │                │                      │ │ │ │
└────────────────────┘                └──────────────────────┘ │ │ │
                                                               │ │ │
                              Bidirectional MAVLink ───────────┴─┘ │
                              Common Ground ─────────────────────────┘

  ┌─────────────────────────────────────────────────────┐
  │  MAVLink Connection (Bidirectional)                 │
  │  ─────────────────────────────────────              │
  │  Pi TX (Pin 8) → FC RX : GPS_INPUT, commands       │
  │  Pi RX (Pin 10) ← FC TX : GLOBAL_POSITION_INT, vz  │
  │  Single connection for all data!                    │
  └─────────────────────────────────────────────────────┘
```

### Connections Table

| Raspberry Pi | ↔ | Flight Controller | Function |
|--------------|---|-------------------|----------|
| Pin 1 (3.3V) | → | Sensor VCC | Sensor power |
| Pin 3 (SDA) | → | Sensor SDA | I2C data |
| Pin 5 (SCL) | → | Sensor SCL | I2C clock |
| Pin 2 (5V) | ← | BEC 5V | Pi power |
| Pin 6 (GND) | ↔ | FC GND, Sensor GND | Common ground |
| Pin 8 (TX) | → | FC TELEM2 RX | MAVLink TX (GPS out) |
| Pin 10 (RX) | ← | FC TELEM2 TX | MAVLink RX (altitude in) |

### Configuration

```json
{
  "sensor": {"type": "caddx_infra256"},
  "tracker": {"max_altitude": 100.0, "initial_height": 3.0},
  "altitude": {
    "enabled": true,
    "type": "mavlink",
    "connection": "/dev/ttyAMA0",
    "baudrate": 57600
  },
  "gps_emulation": {
    "enabled": true,
    "protocol": "mavlink",
    "port": "/dev/ttyAMA0",
    "baudrate": 57600,
    "update_rate_hz": 10
  },
  "control": {"update_rate_hz": 100}
}
```

**Power Requirements:**
- Raspberry Pi Zero 2W: 1000mA @ 5V
- Sensor: 15mA @ 3.3V
- **Total: 2.5-3A BEC minimum**

---

## Configuration 4: Analog Camera (Caddx 256CA)

**Use Case**: Dual-purpose FPV + optical flow  
**Flight Controller**: Any  
**Sensor**: Caddx 256CA (analog CVBS via USB capture)  
**Altitude**: 30-50m recommended

### Wiring Diagram

```
┌───────────────────────────────────────────────────────────────┐
│                  RASPBERRY PI ZERO 2W                          │
│                                                                │
│  Pin 2  [5V]   ────────────────────────────┐                 │
│  Pin 6  [GND]  ──────────────────────────┐ │                 │
│  Pin 8  [TX]   ────────────────────────┐ │ │                 │
│                                        │ │ │                 │
│  USB Port (data) ──┐                   │ │ │                 │
│  USB Port (power)──┼───────────────┐   │ │ │                 │
│                    │               │   │ │ │                 │
└────────────────────┼───────────────┼───┼─┼─┼─────────────────┘
                     │               │   │ │ │
                     │               │   │ │ │
  Analog Camera      │               │   │ │ │
  ─────────────      │               │   │ │ │         Power
                     │               │   │ │ │         ─────
┌──────────────────┐ │               │   │ │ │
│  Caddx 256CA     │ │               │   │ │ │     ┌───────────┐
│  (Analog CVBS)   │ │               │   │ │ │     │    BEC    │
│                  │ │               │   │ │ │     │  5V 3A+   │
│  5V ─────────────┼─┼───────────────┼───┼─┼─┼─────┤ 5V        │
│  GND ────────────┼─┼───────────┐   │   │ │ │     │ GND       │
│  CVBS ───────────┼─┼─────┐     │   │   │ │ │     └─────┬─────┘
│                  │ │     │     │   │   │ │ │           │
└──────────────────┘ │     │     │   │   │ │ │           │
                     │     │     │   │   │ │ │           │
  USB Capture Card   │     │     │   │   │ │ │           │
  ────────────────   │     │     │   │   │ │ │           │
                     │     │     │   │   │ │ │           │
┌──────────────────┐ │     │     │   │   │ │ │           │
│  USB Capture     │ │     │     │   │   │ │ │           │
│  (UVC Device)    │ │     │     │   │   │ │ │           │
│                  │ │     │     │   │   │ │ │           │
│  Video In ←──────┼─┘     │     │   │   │ │ │           │
│  USB Out ────────┴───────┘     │   │   │ │ │           │
│  5V (optional) ─────────────────┴───────┘ │ │           │
│  GND ───────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────┘
                                         │   │
                               Flight Controller
                               ──────────────────
                                         │   │
                             ┌───────────┼───┼───────────┐
                             │           │   │           │
                             │  GPS RX ←─┘   │           │
                             │  GND ─────────┴───────────┤
                             │  5V BEC ───────────────────┤
                             │                           │
                             └───────────────────────────┘
                             
  ┌─────────────────────────────────────────────────────┐
  │  USB Hub (if needed for capture + telemetry)       │
  │  ───────────────────────────────────────           │
  │  Pi USB → Hub Input                                │
  │  Hub Port 1 → Capture Card                         │
  │  Hub Port 2 → FC USB (telemetry, optional)         │
  │  Powered hub recommended for stable operation      │
  └─────────────────────────────────────────────────────┘
```

### Connections Table

| Component A | → | Component B | Function |
|-------------|---|-------------|----------|
| Camera 5V | ← | BEC 5V | Camera power |
| Camera GND | → | Common GND | Ground |
| Camera CVBS | → | Capture Video In | Analog video |
| Capture USB | → | Pi USB | Video data |
| Pi Pin 2 (5V) | ← | BEC 5V | Pi power |
| Pi Pin 6 (GND) | → | Common GND | Ground |
| Pi Pin 8 (TX) | → | FC GPS RX | GPS data |

### Configuration

```json
{
  "sensor": {"type": "analog_usb"},
  "camera": {
    "device": "/dev/video0",
    "width": 720,
    "height": 480,
    "fps": 30,
    "method": "farneback",
    "deinterlace": true
  },
  "tracker": {"max_altitude": 100.0},
  "gps_emulation": {
    "enabled": true,
    "protocol": "nmea",
    "port": "/dev/ttyAMA0"
  }
}
```

**Power Requirements:**
- Raspberry Pi Zero 2W: 1000mA @ 5V
- Caddx 256CA: 100mA @ 5V
- USB Capture: 500mA @ 5V
- **Total: 3A BEC minimum**

**Recommended Hardware:**
- EasyCap DC60 ($5-10)
- Elgato Video Capture ($50+)
- Generic UVC capture cards

---

## Power Distribution Guidelines

### BEC Selection

| Setup | Min Current | Recommended BEC |
|-------|-------------|-----------------|
| Basic Indoor (Zero W) | 1A | 2A BEC |
| Outdoor (Zero 2W) | 2A | 2.5A BEC |
| With Capture Card | 2.5A | 3A BEC |
| Full System | 3A | 5A BEC (safe) |

### Recommended BECs

**Budget Options:**
- HobbyKing UBEC 3A ($5-8)
- Turnigy 5V 3A BEC ($8-12)

**Quality Options:**
- Castle Creations BEC 5V 3A ($20-25)
- Pololu 5V Step-Down 2.5A ($15-20)

**High Power:**
- HobbyKing UBEC 5V 5A ($12-18)
- Castle BEC Pro 5V 10A ($35-45)

### Power Wiring

```
Battery (7.4-25.2V)
     │
     ├─→ ESCs (motors)
     │
     └─→ BEC (5V regulator)
           │
           ├─→ Flight Controller (1A)
           ├─→ Raspberry Pi (1-2A)
           ├─→ USB Capture Card (0.5A, if used)
           └─→ Camera (0.1A)

Common Ground: Battery GND → BEC GND → FC GND → Pi GND → Sensor GND
```

### Power Tips

✅ **Best Practices:**
- Use thick wires (18-20 AWG) for power
- Keep power wires short
- Add 470µF capacitor near Pi 5V input
- Use separate BEC for Pi if possible
- Test voltage under load (should be 4.95-5.25V)

❌ **Avoid:**
- Daisy-chaining multiple devices on single BEC output
- Undersized BEC (causes brownouts)
- Long thin power wires
- Sharing ground with noisy motors
- Powering Pi from FC 5V rail (insufficient current)

---

## Troubleshooting

### No Sensor Detection

**I2C Sensor:**
```bash
i2cdetect -y 1
# Should show device at 0x29 or 0x30
```

**USB Capture:**
```bash
ls -l /dev/video*
v4l2-ctl --list-devices
```

### UART Not Working

```bash
# Check if UART is enabled
ls -l /dev/ttyAMA0  # Should exist

# Check for serial console (should be disabled)
sudo raspi-config
# Interface Options → Serial Port → No (console) Yes (hardware)

# Test UART
cat /dev/ttyAMA0 &  # Monitor output
# Start system, should see GPS sentences
```

### Power Issues

```bash
# Monitor voltage
vcgencmd get_throttled
# 0x0 = good, anything else = power issue

# Check current voltage
vcgencmd measure_volts
# Should be 4.95-5.25V
```

### FC Not Detecting GPS

**Betaflight:**
```
# Check serial port assignment
serial
# Should show GPS on correct UART

# Check GPS provider
get gps_provider
# Should be NMEA or AUTO
```

**ArduPilot:**
```
# Check serial protocol
param show SERIAL2_PROTOCOL
# Should be 5 (GPS)

# Check baudrate
param show SERIAL2_BAUD
# Should be 57 (57600)
```

---

## Summary

### Quick Reference

| Config | FC | Sensor | UARTs | Power | Best For |
|--------|---- |--------|-------|-------|----------|
| 1 | Any | I2C/SPI | 1 TX | 1A | Indoor |
| 2 | BF/iNav | I2C | TX + USB | 2A | Outdoor 50m |
| 3 | ArduPilot | I2C | TX+RX | 3A | Missions 100m |
| 4 | Any | Analog USB | TX | 3A | FPV + Flow |

### Connection Priority

1. **Always connect first**: Ground (GND)
2. **Then connect**: Power (5V, 3.3V)
3. **Finally connect**: Signal (TX, RX, I2C, SPI)
4. **Double check**: No shorts, correct voltages
5. **Power on**: Check voltages before connecting to FC

---

**For more details, see branch-specific documentation:**
- `README.betaflight.md` - Betaflight configurations
- `README.ardupilot.md` - ArduPilot configurations
- `OUTDOOR_50M_UPGRADE.md` - High altitude guide
