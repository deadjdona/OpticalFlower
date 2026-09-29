# Installation Guide

Comprehensive setup and installation instructions for the Betafly Position Stabilization System on Raspberry Pi Zero, Zero 2 W, and Pi 4.

## Hardware Setup

The system supports multiple optical flow sensor and camera configurations. Choose the one that matches your build:

### Option 1: PMW3901 Optical Flow Sensor (SPI)
Connect via SPI to Raspberry Pi Zero GPIO header:
```
PMW3901 Sensor -> Raspberry Pi Zero
-----------------------------------------
VCC (3.3V)     -> Pin 1 (3.3V)
GND            -> Pin 6 (GND)
MOSI           -> Pin 19 (GPIO 10 / MOSI)
MISO           -> Pin 21 (GPIO 9 / MISO)
SCLK           -> Pin 23 (GPIO 11 / SCLK)
CS             -> Pin 24 (GPIO 8 / CE0)
```

### Option 2: Caddx Infra 256 Sensor (I2C)
Connect via I2C:
```
Caddx Infra 256 -> Raspberry Pi Zero
-----------------------------------------
VCC (3.3V)      -> Pin 1 (3.3V)
GND             -> Pin 6 (GND)
SDA             -> Pin 3 (GPIO 2 / I2C SDA)
SCL             -> Pin 5 (GPIO 3 / I2C SCL)
```

### Option 3: Caddx Infra 256CA + AI Box (Serial / TCP)
- **USB Serial**: Connect AI Box USB data port to Pi USB OTG data port (`/dev/ttyUSB0`, 921600 baud).
- **Network / TCP**: Connect AI Box via Ethernet / Wi-Fi and configure host/port in `config.json`.
- See [CADDX_INFRA256_GUIDE.md](CADDX_INFRA256_GUIDE.md) for full instructions.

### Option 4: Raspberry Pi Camera Module (CSI)
1. Locate the CSI camera ribbon connector on Pi Zero.
2. Flip up the black latch on the connector.
3. Insert camera ribbon cable (blue backing facing USB port, metal contacts facing HDMI ports).
4. Push latch down to secure.
5. See [CAMERA_SETUP.md](CAMERA_SETUP.md) for detailed camera wiring and tuning.

### Option 5: USB Webcam or Analog Camera (CVBS via USB Capture)
- Connect USB camera / UVC capture dongle to the Pi Zero micro-USB data port using a micro-USB OTG adapter.

### Power Supply (BEC)
- The Raspberry Pi requires a clean, regulated 5V supply (minimum 2A capacity recommended).
- Use a dedicated BEC from the drone battery.
- Add a filter capacitor (100–470 µF) near the Pi power pins for electrical noise suppression.

---

## Software Installation

### Quick Install (Automated)

```bash
# Clone repository
git clone https://github.com/deadjdona/OpticalFlower.git
cd OpticalFlower

# Run setup script (installs packages, sets up venv, enables interfaces)
chmod +x setup.sh
./setup.sh

# Reboot to apply hardware interface changes
sudo reboot
```

### Manual Install

```bash
# 1. Update system packages
sudo apt-get update && sudo apt-get upgrade -y

# 2. Install system packages
sudo apt-get install -y python3 python3-full python3-pip python3-dev git clang gcc

# 3. Create and activate virtual environment
python3 -m venv --system-site-packages optic
source optic/bin/activate

# 4. Enable hardware interfaces in raspi-config
sudo raspi-config
# - Interface Options -> SPI -> Enable
# - Interface Options -> I2C -> Enable
# - Interface Options -> Camera -> Enable
# - Interface Options -> Serial Port -> Shell: NO, Port: YES

# 5. Install Python dependencies
pip3 install -r requirements.txt

# 6. Make scripts executable
chmod +x betafly_stabilizer.py betafly_stabilizer_advanced.py main.py calibrate.py calibrate_thermal.py test_sensor.py setup.sh

# 7. Reboot
sudo reboot
```

---

## Verification

### 1. Test Camera Connection
```bash
# Check if camera interface is recognized
vcgencmd get_camera
# Expected: supported=1 detected=1

# Test capture (CSI)
libcamera-still -o test.jpg
# Or for legacy camera stack:
raspistill -o test.jpg

# Test USB / V4L2 cameras
ls /dev/video*
```

### 2. Test Camera Access via Python
```bash
python3 -c "
from camera_optical_flow import auto_detect_camera
cam_id = auto_detect_camera()
if cam_id is not None:
    print(f'✓ Camera detected at ID: {cam_id}')
else:
    print('✗ No camera detected')
"
```

### 3. Test Optical Flow Tracking
```bash
./test_sensor.py --test tracking --duration 10
```
Move the sensor/camera over a textured surface and verify that position coordinates and velocity update.

---

## Configuration

Settings are controlled via [`config.json`](config.json) or through the interactive Web GUI (port 8080).

### Key Settings to Adjust

**Sensor Type Selection:**
```json
"sensor": {
  "type": "pmw3901",  // "pmw3901", "caddx_infra256", "caddx_infra256ca", "usb_camera", "csi_camera", "analog_usb"
  "rotation": 0       // 0, 90, 180, or 270 degrees
}
```

**Flight Height:**
```json
"tracker": {
  "initial_height": 0.5,  // meters
  "max_altitude": 50.0
}
```

**PID Gains:**
```json
"pid": {
  "position_x": { "kp": 0.5, "ki": 0.1, "kd": 0.2 },
  "position_y": { "kp": 0.5, "ki": 0.1, "kd": 0.2 }
}
```

---

## Running the System

### Standard Mode
```bash
# Velocity damping mode (recommended for initial flight test)
./betafly_stabilizer.py --mode velocity_damping

# Position hold mode
./betafly_stabilizer.py --mode position_hold --log
```

### Advanced Mode (with Web UI & Altitude Fusion)
```bash
./betafly_stabilizer_advanced.py
```
Open `http://<pi-ip-address>:8080` in your browser to view telemetry, live status, and configure parameters.

### Modular Tracking System (`main.py`)
```bash
python main.py
```

### Run Tests
```bash
pytest -v
```

### Auto-Start on Boot (systemd service)
```bash
# Copy service definition
sudo cp betafly-stabilizer.service /etc/systemd/system/

# Reload and enable
sudo systemctl daemon-reload
sudo systemctl enable betafly-stabilizer.service

# Start service
sudo systemctl start betafly-stabilizer.service

# Inspect logs
sudo journalctl -u betafly-stabilizer.service -f
```

---

## Flight Controller Integration

### Wiring: Pi Zero to Flight Controller (UART)
Connect UART serial pins between Pi and FC telemetry port:
```
┌─────────────────────┬───────────────────────────────┐
│ Pi Zero             │ Flight Controller             │
├─────────────────────┼───────────────────────────────┤
│ Pin 8 (GPIO14 TX)   │ RX (UART Receive)             │
│ Pin 10 (GPIO15 RX)  │ TX (UART Transmit)            │
│ Pin 6 (GND)         │ GND (Common Ground)           │
└─────────────────────┴───────────────────────────────┘
```
*Note: TX crosses to RX, and RX crosses to TX.*

### Protocol Configuration

**For MAVLink (ArduPilot / PX4):**
```json
{
  "output": {
    "interface": "mavlink",
    "port": "/dev/ttyAMA0",
    "baudrate": 115200
  }
}
```

**For MSP (Betaflight / iNav):**
```json
{
  "output": {
    "interface": "msp",
    "port": "/dev/ttyAMA0",
    "baudrate": 115200
  }
}
```

**For GPS Emulation (NMEA / MAVLink GPS):**
```json
{
  "gps_emulation": {
    "enabled": true,
    "protocol": "nmea",
    "port": "/dev/ttyAMA0",
    "baudrate": 115200,
    "update_rate_hz": 5,
    "home_lat": 10.0,
    "home_lon": 10.0,
    "home_alt": 0.0
  }
}
```

**See [WIRING_GUIDE.md](WIRING_GUIDE.md) and [GPS_EMULATION_GUIDE.md](GPS_EMULATION_GUIDE.md) for full configuration.**

---

## Initial Flight Test Checklist

- [ ] Sensor securely mounted facing downward
- [ ] Lens / optical sensor clean and unobstructed
- [ ] Pi powered from reliable BEC (not USB power bank)
- [ ] Common ground connected between Pi and Flight Controller
- [ ] RC stick manual override mapped to switch on transmitter
- [ ] Safe flight area with textured floor/ground (avoid flat uniform colors or mirrors)
- [ ] Lighting adequate for optical tracking

---

## Troubleshooting

### Sensor / Camera Not Detected
- Check SPI is enabled: `ls /dev/spidev*`
- Check I2C is enabled: `i2cdetect -y 1`
- Check Camera is enabled: `vcgencmd get_camera`
- Verify wiring and 3.3V/5V power pins.

### Permission Errors
```bash
sudo usermod -a -G spi,gpio,i2c,video $USER
sudo chmod +x *.py *.sh
```

### Low Quality / Drift
- Ensure ground has contrasting features (grass, carpet, pavement).
- Check camera focus.
- Add vibration dampers to flight controller and Pi mounts.
