# OpticalFlower: Optical Position Stabilization System

A complete optical flow and visual position stabilization system for UAVs and drones (Betaflight, iNav, ArduPilot, PX4), optimized for Raspberry Pi Zero / Zero 2 W and Linux SBCs.

> **📌 NOTE**: This is the **universal `main` branch** supporting all flight controllers and sensors.  
> For optimized configurations, see:
> - **[`betaflight` branch](../../tree/betaflight)** - Optimized for Betaflight/iNav (NMEA GPS emulation)
> - **[`ardupilot` branch](../../tree/ardupilot)** - Optimized for ArduPilot/PX4 (MAVLink GPS / telemetry)
> - **[Branch Comparison](BRANCH_INFO.md)** - Detailed comparison and selection guide

## ✨ New Features

- **🌐 Web Interface**: Beautiful real-time dashboard for monitoring and configuration (port 8080)
- **📷 Multiple Camera Support**: PMW3901, USB cameras, CSI cameras, and analog FPV cameras
- **🧠 AI Box Integration**: Native Caddx Infra 256CA + AI Box streaming over USB serial or TCP
- **🎮 Manual Stick Inputs**: RC receiver integration with SBUS/PWM support and smooth blending
- **🔧 Live Configuration**: Edit PID gains and settings through web GUI
- **📊 Real-time Visualization**: Live position tracking and control output graphs

## Core Features

- **Optical Flow Sensing**: Multiple sensor options for precise motion tracking
- **Position Hold**: Maintains GPS-free position hold using visual odometry
- **GPS Emulation**: Pi acts as GPS module for flight controller via UART 📡
- **Visual Coordinate System**: Camera-frame position hold (no compass required) 📹
- **Barometer Integration**: Reads vertical velocity from flight controller for improved accuracy
- **High Altitude Support**: Works reliably at 30m+ altitude with adaptive algorithms ⬆️
- **Altitude-Adaptive Control**: Automatically adjusts filtering and gains based on altitude
- **Velocity Damping**: Reduces drift and oscillations during flight
- **PID Control**: Tunable PID controllers for X and Y axis stabilization
- **Multiple Modes**: Off, velocity damping, and position hold modes
- **Real-time Logging**: Optional CSV logging for flight data analysis
- **Lightweight**: Optimized for Raspberry Pi Zero's limited resources

## Hardware Requirements

### Required Components
- **Raspberry Pi Zero W** (or Zero 2 W for better performance)
- **Optical Flow Sensor** (choose one):
  - PMW3901 Optical Flow Sensor (SPI) - Pimoroni or similar
  - **Caddx Infra 256 (I2C)** - Recommended for production ⭐
- Caddx Infra 256CA (Analog CVBS) - Use with USB capture card
- **Caddx Infra 256CA + AI Box (Serial/TCP)** - Plug-and-play streaming + live height feed
- USB/CSI/Analog Camera (for computer vision approach)
- **Flight Controller** (Betaflight, iNav, or ArduPilot compatible)
- **Power Supply** (5V for Pi, shared with drone battery via BEC)

### Wiring Diagrams

#### Option 1: PMW3901 (SPI)
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

#### Option 2: Caddx Infra 256 (I2C) ⭐ Recommended
```
Caddx Infra 256 -> Raspberry Pi Zero
-----------------------------------------
VCC (3.3V)      -> Pin 1 (3.3V)
GND             -> Pin 6 (GND)
SDA             -> Pin 3 (GPIO 2 / I2C SDA)
SCL             -> Pin 5 (GPIO 3 / I2C SCL)
```

**Benefits of Caddx Infra 256:**
- ✅ Simpler wiring (4 wires vs 6)
- ✅ Infrared technology (better in varied lighting)
- ✅ Lower power consumption
- ✅ I2C interface (easier debugging)

#### Option 3: Caddx Infra 256CA (Analog Camera)
```
Caddx Infra 256CA -> USB Capture Card -> Raspberry Pi
--------------------------------------------------------
5V              -> USB Capture Card 5V
GND             -> USB Capture Card GND
CVBS (Video)    -> USB Capture Card Video In
USB Capture Card -> Pi USB Port
```

**Note**: Caddx Infra 256CA outputs analog video (CVBS), not I2C. It requires a USB video capture card for optical flow processing. Configure as `"type": "analog_usb"` in config.json.

**Benefits:**
- ✅ Infrared technology (works in low light)
- ✅ Standard analog video output
- ✅ Can also record FPV footage
- ✅ Simple 3-wire connection (5V, GND, CVBS)

**Important**: Ensure the sensor is mounted facing downward with adequate lighting for optical tracking.

#### Option 3: Caddx Infra 256CA + AI Box
```
Caddx Infra 256CA -> AI Box -> Raspberry Pi Zero
-----------------------------------------------
Sensor ribbon     -> AI Box (factory cable)
AI Box USB (5V)   -> Pi USB data port (serial streaming)
AI Box Ethernet   -> (optional) Network switch / Pi (TCP streaming)
```

- Power the AI Box from a clean 5V supply (500mA+). USB from the Pi works for most setups.
- For USB mode, a `/dev/ttyUSBx` device will appear; set `serial_port` accordingly.
- For remote mounting, connect Ethernet/Wi-Fi and set `ai_box.tcp_host` + `ai_box.tcp_port` in `config.json`.
- The AI Box streams delta X/Y, surface quality, and height. The driver auto-converts the height feed to meters using `ai_box.height_scale`.

## Software Installation

### 1. Prepare Raspberry Pi Zero

```bash
# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python 3 and pip (if not already installed)
sudo apt-get install python3 python3-pip -y

# Enable SPI interface
sudo raspi-config
# Navigate to: Interface Options -> SPI -> Enable
```

### 2. Clone Repository

```bash
cd ~
git clone https://github.com/deadjdona/OpticalFlower.git
cd OpticalFlower
```

### 3. Install Dependencies

```bash
# Automated setup (creates venv and installs dependencies):
chmod +x setup.sh
./setup.sh

# Or manual installation:
python3 -m venv --system-site-packages optic
source optic/bin/activate
pip install -r requirements.txt
chmod +x betafly_stabilizer.py betafly_stabilizer_advanced.py main.py
```

### 4. Test Sensor Connection

```bash
# Test sensor via test utility:
python3 test_sensor.py -s pmw3901    # for PMW3901 SPI
python3 test_sensor.py -s caddx      # for Caddx Infra 256 / 256CA
python3 test_sensor.py -s camera     # for USB / CSI / Analog camera

# Or run automated unit tests:
pytest -v
```

## Configuration

Edit `config.json` to customize the system for your setup:

### Key Parameters

```json
{
  "sensor": {
    "type": "pmw3901",  // Options: pmw3901, caddx_infra256, analog_usb (for Caddx 256CA)
    "rotation": 0,  // Adjust based on sensor mounting orientation
  },
  "tracker": {
    "initial_height": 0.5,  // Expected flight height in meters
    "use_visual_coords": true,  // Use visual coordinate system (recommended)
  },
  "altitude": {
    "enabled": true,  // Enable for barometer velocity from flight controller
    "type": "mavlink",  // Read from flight controller via MAVLink
    "connection": "/dev/ttyAMA0"
  },
  "gps_emulation": {
    "enabled": false,  // Enable to make Pi act as GPS module for FC
    "protocol": "nmea",  // Options: nmea (most FCs), mavlink
    "port": "/dev/ttyAMA0",  // UART port to FC GPS input
    "baudrate": 115200,  // Must match FC GPS baudrate
    "home_lat": 0.0,  // Set to your takeoff location
    "home_lon": 0.0,
    "home_alt": 0.0
  },
  "pid": {
    "position_x": {
      "kp": 0.5,  // Increase for more aggressive position correction
      "ki": 0.1,  // Increase to eliminate steady-state error
      "kd": 0.2   // Increase to reduce oscillations
    }
  },
  "stabilizer": {
    "max_tilt_angle": 15.0,  // Maximum tilt command in degrees
    "velocity_damping": 0.3  // Damping factor (0-1)
  },
  "control": {
    "update_rate_hz": 50  // Control loop frequency
  }
}
```

## Usage

### Quick Start

```bash
# Option 1: Unified runner with auto-detection & web interface (recommended)
python3 main.py

# Option 2: Direct advanced stabilizer script
./betafly_stabilizer_advanced.py

# Access web interface at:
# http://raspberrypi.local:8080 (or http://<pi-ip>:8080)
```

The web interface provides:
- Real-time position and velocity display
- Live control output visualization
- Configuration editor
- Mode switching controls
- Stick input monitoring

### GPS Emulation Mode 📡

Enable GPS emulation to make the Raspberry Pi act as a GPS module:

```bash
# Edit config.json
nano config.json

# Set:
# "gps_emulation": {
#   "enabled": true,
#   "protocol": "nmea",
#   "port": "/dev/ttyAMA0",
#   "baudrate": 115200
# }

# Then start the system
./betafly_stabilizer_advanced.py
```

**With GPS emulation enabled:**
- Pi sends optical flow position as GPS data via UART
- Flight controller thinks it has GPS connected
- FC does position hold using standard GPS modes
- No need for Pi to send pitch/roll corrections

See **[GPS_EMULATION_GUIDE.md](GPS_EMULATION_GUIDE.md)** for complete setup instructions

### Basic Command Line Usage

```bash
# Start with velocity damping (reduces drift)
./betafly_stabilizer.py --mode velocity_damping

# Start advanced system with all features
./betafly_stabilizer_advanced.py --mode position_hold

# Use custom config file
./betafly_stabilizer_advanced.py --config my_config.json

# Enable data logging
./betafly_stabilizer_advanced.py --log --mode position_hold

# Disable web interface
./betafly_stabilizer_advanced.py --no-web
```

### Using Different Camera Types

```bash
# PMW3901 sensor (default)
./betafly_stabilizer_advanced.py

# USB camera
# Edit config.json: "sensor": {"type": "usb_camera"}
./betafly_stabilizer_advanced.py --config config.json

# Analog camera via USB capture card
# Edit config.json: "sensor": {"type": "analog_usb"}
./betafly_stabilizer_advanced.py --config config.json
```

**Caddx Infra 256CA + AI Box:** Set `"sensor.type": "caddx_infra256ca"` and populate the nested `ai_box` block to match your wiring:

```json
"sensor": {
  "type": "caddx_infra256ca",
  "rotation": 0,
  "ai_box": {
    "connection": "auto",
    "serial_port": "/dev/ttyUSB0",
    "serial_baudrate": 921600,
    "tcp_host": "",
    "tcp_port": 8899,
    "data_timeout": 0.25,
    "height_scale": 1.0
  }
}
```

Use `connection="serial"` for USB tethering or set `tcp_host` to stream over Wi-Fi/Ethernet. The AI Box height feed is automatically fused into the tracker, so tune `height_scale` if the measured altitude does not match reality. All of these values are editable from the web interface under **Configuration → Sensor** when the new sensor type is selected.

### Command Line Options

```
-c, --config FILE       Configuration file (JSON)
-m, --mode MODE         Initial mode: off, velocity_damping, position_hold
-l, --log              Enable CSV data logging
-v, --verbose          Enable verbose logging
```

### Operating Modes

1. **Off**: No stabilization (pass-through)
2. **Velocity Damping**: Reduces drift by opposing velocity
3. **Position Hold**: Maintains position at the point where mode was activated

## Integration with Flight Controller

The system outputs pitch and roll correction angles that need to be sent to your flight controller.

### Option 1: MAVLink (Recommended)

For ArduPilot or PX4:
- Connect Pi serial to FC telemetry port
- Set `"interface": "mavlink"` in config
- System sends `SET_POSITION_TARGET_LOCAL_NED` messages

### Option 2: MSP Protocol

For Betaflight/iNav:
- Connect Pi serial to FC UART
- Set `"interface": "msp"` in config
- Implement MSP message handling in `_send_corrections()`

### Option 3: PWM Override

- Connect Pi GPIO to FC receiver inputs
- Set `"interface": "pwm"` in config
- Use pigpio library for PWM generation

## Tuning Guide

### Step 1: Verify Optical Flow

1. Start system with logging enabled
2. Manually move drone and observe position tracking
3. Ensure `surface_quality` (squal) stays above 50

### Step 2: Tune Velocity Damping

1. Start in velocity_damping mode
2. Adjust `velocity_damping` factor (0.1 to 0.5)
3. Higher values = more aggressive damping

### Step 3: Tune Position Hold

1. Start with conservative PID gains
2. Increase Kp until position holds with minimal error
3. Add Kd to reduce oscillations
4. Add small Ki to eliminate steady-state error

### Tuning Tips

- **Too oscillatory?** Decrease Kp, increase Kd
- **Too slow to respond?** Increase Kp
- **Steady-state error?** Increase Ki (but keep small!)
- **Drifting away?** Check sensor mounting and height setting

## Performance Optimization

### For Raspberry Pi Zero

The Pi Zero is single-core and slower, so:

1. **Reduce update rate**: Try 30-40 Hz instead of 50 Hz
2. **Disable logging**: Reduces CPU and SD card writes
3. **Use lightweight OS**: Raspberry Pi OS Lite (no desktop)
4. **Overclock safely**: Add to `/boot/config.txt`:
   ```
   arm_freq=1000
   over_voltage=2
   ```

### For Raspberry Pi Zero 2 W

The quad-core Zero 2 W can handle:
- 100 Hz update rate
- Real-time logging
- Additional sensor fusion (IMU integration)

## Data Analysis

Flight logs are saved as CSV files with columns:
- `time`: Time in seconds
- `pos_x`, `pos_y`: Position in meters
- `vel_x`, `vel_y`: Velocity in m/s
- `pitch_cmd`, `roll_cmd`: Control outputs in degrees
- `mode`: Current stabilization mode
- `squal`: Surface quality (0-255)

Analyze with Python:

```python
import pandas as pd
import matplotlib.pyplot as plt

df = pd.read_csv('flight_log.csv')
plt.plot(df['time'], df['pos_x'], label='X position')
plt.plot(df['time'], df['pos_y'], label='Y position')
plt.legend()
plt.show()
```

## Troubleshooting

### Sensor Not Detected

- Verify SPI is enabled: `lsmod | grep spi`
- Check wiring connections
- Test with `spidev` directly

### Poor Tracking Quality

- Ensure adequate lighting (avoid direct sunlight)
- Check sensor is clean and unobstructed
- Verify height setting matches actual height
- Ensure surface below has visible texture (not blank/uniform)

### Position Drift

- Verify sensor rotation setting matches physical mounting
- Check for vibrations (dampen sensor mounting)
- Increase velocity damping factor
- Ensure height is set correctly (scales optical flow)

### Control Loop Running Slow

- Reduce update rate in config
- Disable data logging
- Close unnecessary processes
- Consider Pi Zero 2 W for better performance

## System Architecture

```
┌─────────────────────────────────────────────────┐
│          Betafly Stabilization System           │
└─────────────────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
┌───────▼────────┐         ┌────────▼────────┐
│ Optical Flow   │         │  Stabilization  │
│    Tracking    │         │   Controller    │
│                │         │                 │
│ - PMW3901      │────────▶│ - Position PID  │
│ - Position Est │         │ - Velocity Damp │
│ - Velocity Est │         │ - Mode Control  │
└────────────────┘         └─────────┬───────┘
                                     │
                            ┌────────▼────────┐
                            │ Flight Control  │
                            │   Interface     │
                            │                 │
                            │ - MAVLink / MSP │
                            │ - PWM Output    │
                            └─────────────────┘
```

## API Reference

### OpticalFlowTracker

```python
tracker = OpticalFlowTracker(sensor, scale_factor=0.001, height_m=0.5)
pos_x, pos_y = tracker.update()  # Get current position
vel_x, vel_y = tracker.get_velocity()  # Get velocity
tracker.reset_position()  # Reset to origin
tracker.set_height(new_height)  # Update height
```

### PositionStabilizer

```python
stabilizer = PositionStabilizer(x_gains, y_gains, max_tilt_angle=15.0)
stabilizer.set_target_position(x, y)  # Set target
stabilizer.enable()  # Enable position hold
pitch, roll = stabilizer.update(current_x, current_y)  # Get corrections
```

### StabilizationController

```python
controller = StabilizationController(gains_x, gains_y, damping, max_tilt)
controller.set_mode("position_hold")  # Set mode
pitch, roll = controller.update(x, y, vx, vy)  # Update control
controller.hold_current_position(x, y)  # Hold at position
```

## New Features Documentation

For detailed information about new features:
- **[FEATURES.md](FEATURES.md)** - Complete guide to web interface, camera support, and stick inputs
- **[INSTALL.md](INSTALL.md)** - Installation and setup instructions
- **[GPS_EMULATION_GUIDE.md](GPS_EMULATION_GUIDE.md)** - GPS emulation for flight controller integration 📡
- **[CADDX_INFRA256_GUIDE.md](CADDX_INFRA256_GUIDE.md)** - Caddx Infra 256 (I2C) setup guide
- **[VISUAL_COORDINATES_GUIDE.md](VISUAL_COORDINATES_GUIDE.md)** - Visual coordinates and barometer integration 📹
- **[HIGH_ALTITUDE_GUIDE.md](HIGH_ALTITUDE_GUIDE.md)** - High altitude operation (30m+) guide ⬆️

## Project Files

### Core System & Entry Points
- `main.py` - Unified runner supporting CLI, web interface, GPS emulation, and hardware auto-detection
- `betafly_stabilizer_advanced.py` - Advanced stabilization system with web UI and all features
- `betafly_stabilizer.py` - Original lightweight control script
- `caddx_infra256ca.py` - Driver for Caddx Infra 256CA + AI Box (Serial/TCP streaming + height feed)
- `caddx_infra256.py` - Caddx Infra 256 driver (I2C)
- `optical_flow_sensor.py` - PMW3901 sensor interface (SPI, with altitude-adaptive tracking)
- `camera_optical_flow.py` - Computer-vision optical flow (USB/CSI/Analog cameras)
- `sensor_factory.py` - Factory pattern for dynamic sensor creation and auto-detection
- `altitude_source.py` - Multi-source altitude fusion (MAVLink, rangefinder, barometer) ⬆️
- `gps_emulation.py` - GPS emulation engine (NMEA/MAVLink) for flight controller integration 📡
- `virtual_gps.py` - Standalone virtual GPS emulator module
- `position_stabilizer.py` - PID control with altitude-adaptive filtering and anti-windup
- `stick_input.py` - RC receiver input handling (SBUS/PWM)
- `web_interface.py` - Flask web server and telemetry API
- `calibrate.py` / `calibrate_thermal.py` - Camera and thermal calibration utilities

### Hardware Guides
- `WIRING_GUIDE.md` - Complete wiring diagrams for all configurations 🔌
- `CAMERA_SETUP.md` - Raspberry Pi CSI, USB, and analog camera setup guide

### Web Interface
- `web/server.py` - Standalone web server entrypoint
- `templates/index.html` - Web dashboard UI
- `static/css/style.css` - Styling
- `static/js/app.js` - Frontend JavaScript

### Configuration & Setup
- `config.json` - Configuration file with all options (100m altitude support)
- `setup.sh` - Automated environment setup script
- `requirements.txt` - Python dependencies (OpenCV, Flask, PySerial, PyMAVLink, etc.)
- `pyproject.toml` - Project configuration and pytest settings

### Testing & Verification
- `tests/test_basic.py` - Automated pytest suite covering imports, sensor loading, PID controllers, and position stabilization
- `test_sensor.py` - Hardware sensor diagnostic utility (`-s {camera,pmw3901,caddx}`)

### Documentation
- `README.md` - Project overview and quick start guide
- `FEATURES.md` - Detailed guide for all features
- `INSTALL.md` - Comprehensive installation and troubleshooting guide
- `CADDX_INFRA256_GUIDE.md` - Caddx Infra 256 (I2C) and 256CA + AI Box guide
- `VISUAL_COORDINATES_GUIDE.md` - Visual coordinates and barometer integration 📹
- `HIGH_ALTITUDE_GUIDE.md` - High altitude operation (30m+) guide ⬆️
- `instruction.md` - Step-by-step setup guide for Raspberry Pi (Ukrainian / Russian)

## Running Tests

Run the unit test suite:
```bash
pytest -v
```

Run interactive hardware diagnostics:
```bash
python3 test_sensor.py -s pmw3901     # Test PMW3901 SPI sensor
python3 test_sensor.py -s caddx       # Test Caddx I2C / AI Box sensor
python3 test_sensor.py -s camera      # Test CSI / USB / Analog camera
```

## Contributing

Contributions welcome! Areas for improvement:
- Flight controller integration implementations
- Additional sensor support (VL53L0X for height)
- Kalman filter for sensor fusion
- Auto-tuning algorithms
- Ground effect compensation
- Additional web interface features
- Mobile app development
- Advanced computer vision algorithms
- Multi-sensor fusion improvements

## License

MIT License - See LICENSE file for details

## Safety Warning

⚠️ **IMPORTANT**: This system is experimental. Always:
- Test in a safe environment
- Have manual control override ready
- Start with low gains and gentle movements
- Monitor battery voltage (Pi can brownout)
- Never fly over people or property

## Support

For issues, questions, or contributions:
- GitHub Issues: https://github.com/deadjdona/OpticalFlower/issues
- Repository: https://github.com/deadjdona/OpticalFlower

## Credits

Developed for the Betafly / OpticalFlower drone project using:
- PMW3901 optical flow sensor
- Caddx Infra 256 (I2C) optical flow sensor
- Caddx Infra 256CA + AI Box (Serial/TCP)
- Caddx Infra 256CA (analog camera) with computer vision
- Raspberry Pi Zero / Zero 2 W platform
- PID control theory
- Visual odometry principles

## Sensor Comparison Quick Reference

| Feature | PMW3901 | Caddx Infra 256 | Caddx Infra 256CA (Analog) | Caddx Infra 256CA + AI Box |
|---------|---------|-----------------|----------------------------|----------------------------|
| Interface | SPI | I2C | Analog CVBS | Serial (USB) / TCP |
| Wiring | 6 wires | 4 wires | 3 wires + USB capture | USB Cable or Ethernet |
| Direct Connection | Yes | Yes | No (needs capture card) | Yes (Plug & Play) |
| Power | ~20mA | ~15mA | ~100mA | 5V 500mA (from Pi USB) |
| Lighting | Visible | Infrared | Infrared | Infrared |
| Video Output | No | No | Yes (analog FPV) | Sensor stream + Height feed |
| Best For | Prototyping | Production I2C | Analog FPV + Optical Flow | High-precision production |
| Price | $ | $$ | $$ | $$$ |

---

**Happy Flying! 🚁**
