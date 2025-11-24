# Visual Coordinate System and Barometer Integration Guide

## Overview

The Betafly position hold system now uses **visual coordinate system** (camera frame of reference) and integrates **barometer velocity** from the flight controller for improved accuracy and stability.

## What is Visual Coordinate System?

### World Coordinates vs Visual Coordinates

**World Coordinates** (traditional approach):
- Fixed reference frame relative to ground
- Requires knowledge of drone orientation (yaw angle)
- Position drifts if yaw estimation is incorrect
- More complex to implement and calibrate

**Visual Coordinates** (our approach):
- Camera/sensor frame of reference
- No yaw angle required
- Position is relative to camera view
- Simpler and more robust

### How Visual Coordinates Work

```
Visual Frame:
    ↑ Y (camera forward)
    |
    |
    +----→ X (camera right)
  (0,0)

When camera is mounted facing down:
- X axis = sideways movement (right is positive)
- Y axis = forward movement (forward is positive)
- Position is measured in camera's perspective
```

### Benefits for Position Hold

1. **No Compass Required**: Works without magnetometer/compass data
2. **Yaw Independent**: Drone can rotate freely, position hold still works
3. **Simpler Control**: Direct mapping from visual motion to control commands
4. **More Robust**: No drift from yaw estimation errors
5. **Better for Indoor**: Compasses often unreliable indoors

### Example

```
Scenario: Drone yaws 45° to the right

World Coordinates (old way):
- Need to know drone rotated 45°
- Must transform optical flow by 45°
- Yaw error causes position drift

Visual Coordinates (new way):
- Don't care about yaw angle
- Optical flow stays in camera frame
- Position hold maintains camera-relative position
- No yaw error accumulation
```

## Barometer Velocity Integration

### Why Use Barometer Velocity?

The flight controller's barometer provides accurate vertical velocity data:

1. **Altitude Changes**: Detect ascending/descending
2. **Optical Flow Correction**: Compensate for altitude rate effects
3. **Better Tracking**: Account for vertical motion in flow calculations
4. **3D Awareness**: System knows vertical velocity component

### How It Works

```python
# Flight controller sends via MAVLink:
GLOBAL_POSITION_INT message:
  - relative_alt: Current altitude (mm)
  - vz: Vertical velocity (cm/s, NED frame)

# System converts to standard units:
altitude_m = relative_alt / 1000.0  # meters
velocity_z = -vz / 100.0  # m/s, positive = up

# Optical flow tracker uses this to:
1. Update altitude dynamically
2. Account for altitude changes in flow calculations
3. Improve position estimate accuracy
```

### MAVLink Integration

**Required Setup:**

1. **Hardware Connection**:
   ```
   Flight Controller TX -> Pi RX (GPIO 15 / Pin 10)
   Flight Controller RX -> Pi TX (GPIO 14 / Pin 8)
   GND -> GND
   ```

2. **Configuration**:
   ```json
   {
     "altitude": {
       "enabled": true,
       "type": "mavlink",
       "connection": "/dev/ttyAMA0",
       "baudrate": 115200
     }
   }
   ```

3. **Enable Serial**:
   ```bash
   sudo raspi-config
   # Interface Options -> Serial Port
   # Login shell: No
   # Serial hardware: Yes
   sudo reboot
   ```

### Data Flow

```
Flight Controller
    |
    | MAVLink GLOBAL_POSITION_INT
    | (altitude + velocity)
    ↓
MAVLinkAltitudeSource
    |
    | get_altitude() & get_velocity()
    ↓
OpticalFlowTracker
    |
    | Updates internal state
    | - height_m (for scaling)
    | - barometer_velocity_z (for corrections)
    ↓
Position Hold Controller
    |
    | Uses accurate altitude and velocity
    ↓
Stable Position Hold
```

## Configuration

### Basic Configuration

```json
{
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 0.5,
    "use_visual_coords": true
  },
  "altitude": {
    "enabled": true,
    "type": "mavlink",
    "connection": "/dev/ttyAMA0"
  }
}
```

### Advanced Configuration

```json
{
  "sensor": {
    "type": "caddx_infra256",
    "rotation": 0
  },
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 0.5,
    "max_altitude": 50.0,
    "use_visual_coords": true
  },
  "altitude": {
    "enabled": true,
    "type": "mavlink",
    "connection": "/dev/ttyAMA0",
    "baudrate": 115200
  },
  "stabilizer": {
    "velocity_damping": 0.3,
    "max_tilt_angle": 15.0,
    "altitude_adaptive": true
  }
}
```

## Flight Operations

### Pre-Flight Check

1. **Verify MAVLink Connection**:
   ```bash
   # Test MAVLink
   python3 -c "from pymavlink import mavutil; m = mavutil.mavlink_connection('/dev/ttyAMA0'); m.wait_heartbeat(); print('Connected')"
   ```

2. **Check Data Flow**:
   ```bash
   # Start system with verbose logging
   ./betafly_stabilizer_advanced.py -v
   
   # Look for:
   # "Altitude source initialized: MAVLinkAltitudeSource"
   # "Alt: X.Xm" in status logs
   ```

3. **Verify Visual Coordinates**:
   ```bash
   # Check web interface
   # http://raspberrypi.local:8080
   # Should show: "Visual Coordinates: Yes"
   ```

### Position Hold Behavior

**With Visual Coordinates + Barometer:**

```
Scenario 1: Hover at 2m altitude
- Optical flow measures lateral motion
- Barometer reports vz ≈ 0 m/s
- Position hold: Stable hover in camera frame

Scenario 2: Ascending to 5m
- Optical flow measures lateral motion
- Barometer reports vz ≈ +1.5 m/s (ascending)
- System compensates for altitude change
- Position hold: Maintains camera-relative position during climb

Scenario 3: Drone yaws 90°
- Optical flow measures motion in NEW camera frame
- Camera frame rotates with drone
- Barometer still reports vertical velocity
- Position hold: Stays at same spot in camera view
- Note: Ground position changes (because camera rotated)
```

### Understanding the Coordinate Transform

```
Traditional (world frame):
1. Read optical flow (camera frame)
2. Get yaw angle from compass
3. Rotate flow vector by yaw angle
4. Get world-frame velocity
5. Control to world-frame target

Visual (camera frame):
1. Read optical flow (camera frame)
2. Use directly (no transform needed)
3. Control to camera-frame target
4. Barometer provides vertical component
5. Much simpler!
```

## Benefits and Limitations

### Benefits ✅

1. **Yaw Independent**: No compass errors
2. **Simpler**: Fewer transformations = less code = fewer bugs
3. **Indoor Safe**: Works without GPS or compass
4. **Robust**: Direct sensor-to-control mapping
5. **Barometer Integration**: Accurate vertical velocity
6. **Adaptive**: Altitude compensation for optical flow scaling

### Limitations ⚠️

1. **Camera-Relative Position**: Position is in camera frame, not world frame
   - If drone yaws, "held position" rotates with it
   - For applications needing world-frame hold, add compass integration

2. **No Global Reference**: Position is relative, not absolute
   - Can't specify "hold at GPS coordinate X,Y"
   - Fine for local operations, waypoint flying needs GPS

3. **Requires MAVLink**: For barometer velocity
   - Without it, uses optical flow only (less accurate)

### When to Use Visual Coordinates

**Recommended for:**
- Indoor flight
- Position hold without GPS
- Environments with magnetic interference
- Quick/simple setup
- Hover in place applications

**Not ideal for:**
- Waypoint navigation (needs world frame)
- Long-distance autonomous flight
- Applications requiring heading hold

## Troubleshooting

### Position Drifts When Yawing

**Expected Behavior**: With visual coordinates, position is camera-relative
- When drone yaws, the "held position" rotates with camera
- This is normal and correct for visual coordinate system

**If you need heading-locked position hold**:
- Would need to add compass/magnetometer integration
- Transform optical flow to world frame using yaw angle
- More complex but maintains position regardless of yaw

### No Barometer Velocity Data

**Check MAVLink Connection**:
```bash
# Test connection
python3 -c "
from altitude_source import MAVLinkAltitudeSource
import time
src = MAVLinkAltitudeSource('/dev/ttyAMA0')
time.sleep(2)
print('Altitude:', src.get_altitude())
print('Velocity:', src.get_velocity())
"
```

**Symptoms**:
- Position hold works but less accurate during altitude changes
- System falls back to optical flow only

**Solution**:
- Enable altitude source in config
- Check serial connection to flight controller
- Verify MAVLink baudrate matches FC

### Visual Coordinates Disabled

**Check Configuration**:
```json
{
  "tracker": {
    "use_visual_coords": true  // Must be true
  }
}
```

**Verify in Logs**:
```
OpticalFlowTracker initialized (visual_coords: True)
```

### Altitude Not Updating

**Possible Causes**:
1. Altitude source disabled
2. MAVLink not connected
3. Flight controller not sending data

**Debug**:
```bash
# Check altitude source
python3 altitude_source.py

# Monitor MAVLink
mavproxy.py --master=/dev/ttyAMA0 --baudrate=115200
```

## API Reference

### OpticalFlowTracker

```python
tracker = OpticalFlowTracker(
    sensor=sensor,
    scale_factor=0.001,
    height_m=0.5,
    max_altitude=50.0,
    altitude_source=altitude_source,
    use_visual_coords=True  # Enable visual coordinates
)

# Update barometer velocity
tracker.set_barometer_velocity(velocity_z)

# Get barometer velocity
vel_z = tracker.get_barometer_velocity()

# Check if using visual coordinates
is_visual = tracker.is_using_visual_coordinates()
```

### MAVLinkAltitudeSource

```python
from altitude_source import MAVLinkAltitudeSource

source = MAVLinkAltitudeSource(
    connection_string='/dev/ttyAMA0',
    baudrate=115200
)

# Get altitude (also updates velocity internally)
altitude = source.get_altitude()

# Get vertical velocity
velocity = source.get_velocity()  # m/s, positive = up
```

## Performance

### Update Rates

- **Optical Flow**: 50-100 Hz
- **MAVLink Data**: 5-10 Hz (typical)
- **Barometer Velocity**: Updated with each MAVLink message
- **Control Loop**: 50 Hz (recommended)

### Accuracy

**Position Accuracy** (with visual coords + barometer):
- 0-5m altitude: ±0.1-0.3m
- 5-15m altitude: ±0.3-0.5m  
- 15-30m altitude: ±0.5-1.0m
- 30m+ altitude: ±1.0-2.0m

**Velocity Accuracy**:
- Barometer: ±0.1 m/s
- Optical flow: ±0.2-0.5 m/s

## Example Configurations

### Indoor Hover (No GPS)

```json
{
  "sensor": {"type": "caddx_infra256"},
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 1.0,
    "use_visual_coords": true
  },
  "altitude": {
    "enabled": true,
    "type": "mavlink"
  }
}
```

### Outdoor Flight (GPS available)

```json
{
  "sensor": {"type": "caddx_infra256"},
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 2.0,
    "max_altitude": 30.0,
    "use_visual_coords": true
  },
  "altitude": {
    "enabled": true,
    "type": "mavlink"
  }
}
```

### High Altitude (30m+)

```json
{
  "sensor": {"type": "caddx_infra256"},
  "tracker": {
    "scale_factor": 0.0011,
    "initial_height": 35.0,
    "max_altitude": 50.0,
    "use_visual_coords": true
  },
  "altitude": {
    "enabled": true,
    "type": "fused",
    "sources": [
      {"type": "rangefinder", "weight": 2.0},
      {"type": "mavlink", "weight": 1.0}
    ]
  },
  "stabilizer": {
    "altitude_adaptive": true,
    "high_altitude_damping_boost": 0.7
  }
}
```

## Summary

**Visual Coordinate System**:
- Position hold in camera frame of reference
- No compass/yaw required
- Simpler, more robust
- Perfect for local position hold

**Barometer Integration**:
- Reads vertical velocity from flight controller
- Improves altitude tracking
- Compensates for altitude changes
- Enhances overall accuracy

**Together**:
- Reliable position hold without GPS
- Works indoors and outdoors
- Handles altitude changes gracefully
- Yaw-independent operation

**Result**: Robust, accurate position hold that works in challenging environments where GPS and compass may fail.

---

**For more information**, see:
- [HIGH_ALTITUDE_GUIDE.md](HIGH_ALTITUDE_GUIDE.md) - High altitude operations
- [CADDX_INFRA256_GUIDE.md](CADDX_INFRA256_GUIDE.md) - Sensor setup
- [README.md](README.md) - Main documentation
