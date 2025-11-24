# Caddx Infra 256CA with AI Box Setup Guide

## Overview

The **Caddx Infra 256CA with AI Box** is an advanced infrared optical flow sensor featuring AI-powered tracking and enhanced stabilization. It combines traditional optical flow with intelligent computer vision for superior performance in challenging conditions.

### Key Features

- **🤖 AI-Powered Tracking**: Intelligent object detection and tracking
- **📍 Enhanced Optical Flow**: AI-enhanced motion tracking with noise reduction
- **🎯 Target Recognition**: Detect and track persons, vehicles, landing pads, and more
- **🔍 Region of Interest (ROI)**: Focus processing on specific areas for efficiency
- **⚡ Real-time Processing**: Up to 100 Hz update rate with AI acceleration
- **🔄 Multiple Modes**: Adaptive modes for different flight scenarios
- **📡 Dual Communication**: I2C for sensor data, optional UART for AI commands

### Advantages over Standard Caddx Infra 256

| Feature | Standard Infra 256 | Infra 256CA AI Box |
|---------|-------------------|-------------------|
| Optical Flow | ✅ Yes | ✅ Enhanced |
| AI Tracking | ❌ No | ✅ Yes |
| Object Detection | ❌ No | ✅ Yes |
| ROI Processing | ❌ No | ✅ Yes |
| Adaptive Stabilization | ❌ No | ✅ Yes |
| Target Confidence | ❌ No | ✅ 0-100% |
| Processing FPS | 100 Hz | 50-100 Hz |

## Hardware Setup

### Wiring Diagram

```
Caddx Infra 256CA AI Box -> Raspberry Pi Zero
------------------------------------------------
VCC (3.3V)      -> Pin 1  (3.3V Power)
GND             -> Pin 6  (Ground)
SDA (I2C)       -> Pin 3  (GPIO 2 / I2C SDA)
SCL (I2C)       -> Pin 5  (GPIO 3 / I2C SCL)
TX (Optional)   -> Pin 10 (GPIO 15 / UART RX)  [For advanced AI features]
RX (Optional)   -> Pin 8  (GPIO 14 / UART TX)  [For advanced AI features]
```

### Pin Reference

| AI Box Pin | Pi Pin | GPIO | Function | Required |
|-----------|--------|------|----------|----------|
| VCC       | 1      | -    | 3.3V Power | ✅ Yes |
| GND       | 6/9/14 | -    | Ground | ✅ Yes |
| SDA       | 3      | 2    | I2C Data | ✅ Yes |
| SCL       | 5      | 3    | I2C Clock | ✅ Yes |
| TX        | 10     | 15   | UART RX | ⚪ Optional |
| RX        | 8      | 14   | UART TX | ⚪ Optional |

**Note**: UART is optional. The sensor works with I2C only, but UART enables advanced AI configuration and real-time AI data streaming.

### Mounting Recommendations

- **Position**: Mount sensor facing **downward** with unobstructed view
- **Angle**: Keep perpendicular to ground (±5° tolerance)
- **Height**: Optimal performance at 0.3m - 2.0m above ground
- **Vibration**: Use soft mounting or dampers to isolate from vibrations
- **Lighting**: Works in low light (infrared), but some ambient light improves performance
- **Avoid**: Direct sunlight on lens, reflective surfaces below (water, glass, mirrors)

## Software Installation

### 1. Enable I2C and UART (if using)

```bash
# Enable I2C
sudo raspi-config
# Navigate to: Interface Options -> I2C -> Enable

# Enable UART (optional, for advanced AI features)
sudo raspi-config
# Navigate to: Interface Options -> Serial Port -> 
#   "Login shell over serial?" -> No
#   "Serial port hardware enabled?" -> Yes

# Reboot to apply changes
sudo reboot
```

### 2. Install Required Libraries

```bash
# Install I2C tools
sudo apt-get install -y i2c-tools python3-smbus

# Install Python dependencies
pip3 install smbus2 pyserial

# Or use requirements.txt
pip3 install -r requirements.txt
```

### 3. Verify I2C Connection

```bash
# Scan I2C bus
sudo i2cdetect -y 1

# Expected output (sensor at 0x29):
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 20: -- -- -- -- -- -- -- -- -- 29 -- -- -- -- -- -- 
```

### 4. Test Sensor and AI Box

```bash
# Run standalone test
python3 caddx_infra256_aibox.py

# Expected output:
# - Sensor detected at address 0x29
# - AI Box: Yes
# - AI status information
# - Real-time motion and tracking data
```

## Configuration

### Basic Configuration

Edit `config.json`:

```json
{
  "sensor": {
    "type": "caddx_infra256_aibox",
    "i2c_bus": 1,
    "i2c_address": 41,
    "uart_port": null,
    "rotation": 0
  },
  "ai_box": {
    "enabled": true,
    "mode": "auto_mode",
    "tracking_target": "ground_texture",
    "roi_enabled": true,
    "roi_x": 160,
    "roi_y": 160,
    "roi_width": 160,
    "roi_height": 160,
    "detection_threshold": 0.6,
    "stabilization_strength": 0.5,
    "update_rate_hz": 50
  }
}
```

### AI Box Modes

#### 1. **Optical Flow Only** (`optical_flow_only`)
- Standard optical flow without AI enhancement
- Lowest processing overhead
- Best for simple scenarios
- Use when: Flying over uniform terrain

#### 2. **Tracking Assist** (`tracking_assist`)
- AI enhances optical flow with feature tracking
- Improved accuracy and noise reduction
- Moderate processing load
- Use when: General indoor/outdoor flight

#### 3. **Object Detection** (`object_detection`)
- Active object detection and classification
- Tracks specific object types
- Higher processing load
- Use when: Following targets, landing on marked pads

#### 4. **Stabilization Enhanced** (`stabilization_enhanced`)
- AI-powered motion prediction and compensation
- Best accuracy in challenging conditions
- Highest processing load
- Use when: Precision hovering, windy conditions

#### 5. **Auto Mode** (`auto_mode`) **[Recommended]**
- Automatically switches between modes based on conditions
- Balances performance and accuracy
- Dynamic resource allocation
- Use when: General purpose, mixed scenarios

### Tracking Targets

Configure what the AI should track:

| Target Type | Description | Best Use Case |
|------------|-------------|---------------|
| `none` | No specific target | General flight |
| `person` | Human detection | Follow-me mode |
| `vehicle` | Cars, bikes, etc. | Vehicle tracking |
| `custom_object` | User-trained object | Specialized tasks |
| `landing_pad` | Landing marker/pad | Precision landing |
| `ground_texture` | General ground features | Position hold (default) |

### Region of Interest (ROI)

Focus AI processing on a specific area to improve performance:

```json
"ai_box": {
  "roi_enabled": true,
  "roi_x": 160,       // Center X (320x320 sensor)
  "roi_y": 160,       // Center Y
  "roi_width": 160,   // ROI width in pixels
  "roi_height": 160   // ROI height in pixels
}
```

**ROI Tips:**
- Center ROI (160, 160) works best for position hold
- Larger ROI = more features but slower processing
- Smaller ROI = faster but may miss important features
- For landing: Place ROI where landing pad appears

### Detection Threshold

Controls how confident the AI must be before using detections:

```json
"detection_threshold": 0.6  // Range: 0.0 to 1.0
```

- **Low (0.3-0.5)**: More detections, may include false positives
- **Medium (0.6-0.7)**: Balanced (recommended)
- **High (0.8-0.9)**: Only very confident detections, may miss targets

### Stabilization Strength

How much AI enhancement to apply to optical flow:

```json
"stabilization_strength": 0.5  // Range: 0.0 to 1.0
```

- **Low (0.2-0.4)**: Subtle enhancement, trust raw optical flow more
- **Medium (0.5-0.6)**: Balanced blend (recommended)
- **High (0.7-0.9)**: Strong AI influence, aggressive noise reduction

## Usage

### Start System with AI Box

```bash
# Start with AI Box enabled
./betafly_stabilizer_advanced.py --config config.json

# Or start web interface (recommended)
./betafly_stabilizer_advanced.py

# Access web interface
# http://raspberrypi.local:8080
```

### Web Interface Features

The web interface provides real-time AI Box monitoring:

1. **AI Status Panel**:
   - Current AI mode
   - Tracking status (active/inactive)
   - Target detection status
   - Confidence level (0-100%)
   - Processing FPS

2. **Configuration Panel**:
   - Change AI mode on the fly
   - Adjust tracking target
   - Modify ROI settings
   - Tune thresholds

3. **Visualization**:
   - Real-time position tracking
   - AI confidence graph
   - Target detection overlay

### Python API

Use AI Box programmatically:

```python
from caddx_infra256_aibox import (
    CaddxInfra256AIBox, AIBoxConfig, AIBoxMode, TrackingTarget
)

# Configure AI Box
ai_config = AIBoxConfig(
    mode=AIBoxMode.AUTO_MODE,
    tracking_target=TrackingTarget.GROUND_TEXTURE,
    roi_enabled=True,
    stabilization_strength=0.7
)

# Initialize sensor
sensor = CaddxInfra256AIBox(
    bus_number=1,
    i2c_address=0x29,
    ai_config=ai_config
)

# Get enhanced motion data
delta_x, delta_y = sensor.get_motion()

# Get AI status
ai_status = sensor.get_ai_status()
print(f"Tracking: {ai_status.tracking_active}")
print(f"Confidence: {ai_status.target_confidence:.2f}")
print(f"FPS: {ai_status.processing_fps}")

# Change AI mode dynamically
sensor.set_ai_mode(AIBoxMode.STABILIZATION_ENHANCED)

# Set custom ROI
sensor.set_roi(x=100, y=100, width=120, height=120)
```

## Advanced Features

### UART Communication

For advanced AI features, connect UART:

```json
{
  "sensor": {
    "type": "caddx_infra256_aibox",
    "uart_port": "/dev/ttyAMA0"
  }
}
```

UART enables:
- Faster AI configuration updates
- Real-time AI data streaming
- Custom object training data upload
- Firmware updates

### Performance Tuning

#### For Maximum Accuracy
```json
{
  "ai_box": {
    "mode": "stabilization_enhanced",
    "roi_enabled": true,
    "roi_width": 200,
    "roi_height": 200,
    "detection_threshold": 0.7,
    "stabilization_strength": 0.8,
    "update_rate_hz": 50
  }
}
```

#### For Maximum Speed
```json
{
  "ai_box": {
    "mode": "tracking_assist",
    "roi_enabled": true,
    "roi_width": 100,
    "roi_height": 100,
    "detection_threshold": 0.5,
    "stabilization_strength": 0.4,
    "update_rate_hz": 100
  }
}
```

#### For Battery Efficiency
```json
{
  "ai_box": {
    "mode": "optical_flow_only",
    "roi_enabled": false,
    "update_rate_hz": 50
  }
}
```

## Troubleshooting

### AI Box Not Detected

**Problem**: Sensor detected but AI Box shows as unavailable

**Solutions**:
```bash
# 1. Verify product ID
python3 -c "from caddx_infra256_aibox import detect_caddx_infra256_aibox; print(detect_caddx_infra256_aibox())"

# 2. Check sensor is genuine AI Box version (not standard)
# Product ID should be 0x4A for AI Box, 0x49 for standard

# 3. Update sensor firmware (if available from manufacturer)
```

### Low AI Confidence

**Problem**: AI confidence always low (<50%)

**Solutions**:
1. **Improve Lighting**: Add subtle ambient lighting (not direct)
2. **Surface Texture**: Ensure ground has visible features
3. **Lower Threshold**: Reduce `detection_threshold` to 0.4-0.5
4. **Adjust ROI**: Make ROI larger to capture more features
5. **Change Target**: Try different `tracking_target` types

### AI Tracking Not Active

**Problem**: `tracking_active` stays false

**Solutions**:
1. **Check Mode**: Ensure mode is not `optical_flow_only`
2. **Verify Configuration**: Confirm `ai_box.enabled = true`
3. **Surface Quality**: Check surface quality > 50
4. **Height**: Ensure flying within 0.3m - 2.0m range
5. **Movement**: AI activates better with slight motion

### Slow Processing FPS

**Problem**: AI FPS < 30

**Solutions**:
1. **Reduce ROI Size**: Smaller ROI = faster processing
2. **Simpler Mode**: Use `tracking_assist` instead of `object_detection`
3. **Lower Resolution**: Check if firmware supports resolution modes
4. **Update Pi**: Consider Pi Zero 2 W for 4x CPU performance

### Position Drift with AI

**Problem**: Position drifts despite AI enhancement

**Solutions**:
1. **Blend Factor**: Reduce `stabilization_strength` to 0.3-0.4
2. **Trust Raw Data**: Use `optical_flow_only` mode temporarily
3. **Calibrate Scale**: Adjust `scale_factor` in tracker config
4. **Check Confidence**: Only trust AI when confidence > 60%
5. **ROI Position**: Ensure ROI centered on stable ground features

## Comparison with Other Sensors

### vs Standard Caddx Infra 256

| Aspect | Standard | AI Box |
|--------|----------|--------|
| Accuracy | Good | Excellent |
| Noise Handling | Moderate | Excellent |
| Low Light | Good | Good |
| Processing Load | Low | Medium |
| Power Consumption | ~15mA | ~25mA |
| Cost | $ | $$ |
| Best For | Budget builds | Performance builds |

### vs PMW3901

| Aspect | PMW3901 | AI Box |
|--------|---------|--------|
| Interface | SPI | I2C (+UART) |
| Wiring Complexity | 6 wires | 4 wires |
| AI Features | None | Extensive |
| Lighting | Visible light | Infrared |
| Object Tracking | No | Yes |
| Best For | Prototyping | Production |

### vs Camera Optical Flow

| Aspect | USB Camera | AI Box |
|--------|------------|--------|
| Setup Complexity | Complex | Simple |
| Processing | Heavy (Pi) | Onboard |
| Power | ~500mA | ~25mA |
| Latency | Higher | Lower |
| Resolution | High | Optimized |
| Best For | Vision tasks | Flight control |

## Best Practices

### Flight Operations

1. **Pre-flight Check**:
   - Verify AI Box detection
   - Check AI confidence > 50% on ground
   - Confirm tracking active
   - Monitor processing FPS > 30

2. **Takeoff**:
   - Start in `auto_mode` or `tracking_assist`
   - Allow 2-3 seconds for AI calibration
   - Verify position hold before full throttle

3. **During Flight**:
   - Monitor confidence levels
   - Watch for target detection status
   - Check processing FPS remains stable

4. **Landing**:
   - Switch to `landing_pad` target if using markers
   - Reduce speed for AI to track accurately
   - Trust position hold for final descent

### Optimal Conditions

- **Lighting**: Moderate ambient light (indoors or outdoor shade)
- **Surface**: Textured ground (carpet, grass, concrete with patterns)
- **Height**: 0.5m - 1.5m for best results
- **Speed**: < 5 m/s for accurate tracking
- **Weather**: Calm conditions (wind < 10 mph)

### Maintenance

1. **Clean Lens**: Wipe with microfiber cloth weekly
2. **Check Connections**: Verify I2C wiring monthly
3. **Firmware Updates**: Check manufacturer for updates
4. **Calibration**: Re-calibrate after mounting changes
5. **Log Analysis**: Review logs for confidence trends

## Example Configurations

### Indoor Racing Drone
```json
{
  "sensor": {"type": "caddx_infra256_aibox", "rotation": 0},
  "ai_box": {
    "enabled": true,
    "mode": "tracking_assist",
    "tracking_target": "ground_texture",
    "roi_enabled": true,
    "roi_width": 120,
    "roi_height": 120,
    "detection_threshold": 0.5,
    "stabilization_strength": 0.6,
    "update_rate_hz": 100
  }
}
```

### Outdoor Mapping Drone
```json
{
  "sensor": {"type": "caddx_infra256_aibox", "rotation": 0},
  "ai_box": {
    "enabled": true,
    "mode": "stabilization_enhanced",
    "tracking_target": "ground_texture",
    "roi_enabled": true,
    "roi_width": 200,
    "roi_height": 200,
    "detection_threshold": 0.7,
    "stabilization_strength": 0.8,
    "update_rate_hz": 50
  }
}
```

### Follow-Me Drone
```json
{
  "sensor": {"type": "caddx_infra256_aibox", "rotation": 0},
  "ai_box": {
    "enabled": true,
    "mode": "object_detection",
    "tracking_target": "person",
    "roi_enabled": true,
    "roi_width": 160,
    "roi_height": 240,
    "detection_threshold": 0.7,
    "stabilization_strength": 0.5,
    "update_rate_hz": 50
  }
}
```

### Precision Landing
```json
{
  "sensor": {"type": "caddx_infra256_aibox", "rotation": 0},
  "ai_box": {
    "enabled": true,
    "mode": "object_detection",
    "tracking_target": "landing_pad",
    "roi_enabled": true,
    "roi_x": 160,
    "roi_y": 200,
    "roi_width": 120,
    "roi_height": 120,
    "detection_threshold": 0.8,
    "stabilization_strength": 0.7,
    "update_rate_hz": 50
  }
}
```

## Technical Specifications

### AI Box Hardware

- **Processor**: Dedicated AI accelerator chip
- **Memory**: 64MB onboard RAM
- **AI Framework**: TensorFlow Lite / Custom
- **Models**: Pre-trained object detection and tracking
- **Inference Time**: 10-20ms per frame
- **Power**: 25mA @ 3.3V (typical), 40mA (peak)

### Sensor Specifications

- **Resolution**: 256 x 256 pixels (infrared)
- **Frame Rate**: Up to 100 Hz (optical flow), 50 Hz (AI processing)
- **Field of View**: ~42° diagonal
- **Wavelength**: 850nm (infrared)
- **Range**: 0.3m - 3.0m (optical flow), 0.5m - 2.0m (AI optimal)
- **Interface**: I2C (100/400 kHz), UART (115200 baud)
- **I2C Address**: 0x29 (default, configurable to 0x28-0x2F)

### AI Capabilities

- **Object Classes**: 6 (person, vehicle, landing pad, etc.)
- **Max Tracked Objects**: 3 simultaneous
- **Tracking Accuracy**: ±2cm @ 0.5m height
- **Confidence Range**: 0-100% (0-255 in firmware)
- **Update Latency**: < 20ms total (sensor + I2C + AI)

## Support & Resources

### Official Resources

- **Manufacturer**: [Caddx FPV](https://www.caddxfpv.com)
- **Product Page**: Check manufacturer website
- **Firmware Updates**: Available from manufacturer
- **Datasheet**: Contact distributor

### Community Support

- **GitHub Issues**: [Repository Issues](https://github.com/yourusername/betafly-stabilization/issues)
- **Forums**: RC Groups, Reddit /r/Multicopter
- **Discord**: Betafly Community Server

### Getting Help

1. **Check Diagnostics**: Run `python3 caddx_infra256_aibox.py`
2. **View Logs**: `sudo journalctl -u betafly-stabilizer.service -f`
3. **Enable Verbose**: `./betafly_stabilizer_advanced.py -v`
4. **Web Dashboard**: http://raspberrypi.local:8080

---

**Note**: The Caddx Infra 256CA AI Box is a cutting-edge sensor that brings AI capabilities to optical flow tracking. While it offers significant advantages, proper configuration and tuning are essential for optimal performance. Start with default settings and adjust based on your specific use case.

**Happy Flying with AI! 🚁🤖**
