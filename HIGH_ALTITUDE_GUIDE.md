# High Altitude Operation Guide (30m+)

## Overview

This guide covers position hold operation at altitudes over 30 meters. The Betafly stabilization system now includes **altitude-adaptive algorithms** that automatically adjust optical flow processing, filtering, and control gains to maintain reliable position hold at high altitudes.

## Why High Altitude is Challenging

Optical flow sensors face several challenges at high altitudes:

1. **Reduced Angular Resolution**: At 30m altitude, ground features appear ~60x smaller than at 0.5m
2. **Signal-to-Noise Ratio**: Sensor noise becomes more significant relative to motion signals
3. **Surface Quality**: Ground texture becomes less distinct, reducing tracking confidence
4. **Scale Factor Uncertainty**: Height estimation errors have proportionally larger impact
5. **Environmental Effects**: Wind and atmospheric conditions have greater influence

## System Enhancements for High Altitude

### 1. Altitude-Adaptive Optical Flow Tracking

The system automatically adjusts optical flow processing based on altitude:

| Altitude Range | Filter Window | Scale Compensation | Tracking Confidence |
|----------------|---------------|-------------------|---------------------|
| 0-5m           | 5 samples     | 1.0x             | 100% (optimal)      |
| 5-15m          | 7 samples     | 1.05x            | 95%                 |
| 15-30m         | 10 samples    | 1.15x            | 85%                 |
| 30-50m         | 15 samples    | 1.20-1.40x       | 50-85%              |

**Automatic Adjustments:**
- **Increased Filtering**: More samples averaged to reduce noise
- **Weighted Averaging**: Recent samples weighted more heavily
- **Scale Compensation**: Adjusts for reduced sensor sensitivity
- **Confidence Tracking**: Real-time quality metrics

### 2. Altitude-Adaptive Velocity Damping

Velocity damping automatically increases with altitude for enhanced stability:

```
Damping Factor = Base Damping × Altitude Factor

where:
  Altitude Factor = 1.0                                    (altitude ≤ 15m)
  Altitude Factor = 1.0 + (alt - 15) / 30 × boost         (15m < altitude ≤ 30m)
  Altitude Factor = 1.0 + boost + (alt - 30) × 0.02       (altitude > 30m)
```

**Example** (base damping = 0.3, boost = 0.5):
- At 15m: Damping = 0.3 × 1.0 = 0.3
- At 30m: Damping = 0.3 × 1.5 = 0.45
- At 40m: Damping = 0.3 × 1.7 = 0.51
- At 50m: Damping = 0.3 × 1.9 = 0.57

### 3. Dynamic Altitude Input Sources

Multiple altitude sources supported:

- **Static**: Manual altitude setting (basic, requires manual updates)
- **MAVLink**: Real-time from flight controller (recommended for 30m+)
- **Rangefinder**: Laser/ultrasonic (accurate up to max range)
- **Barometer**: Pressure-based (requires ground calibration)
- **Fused**: Combines multiple sources (most reliable)

## Configuration for High Altitude

### Basic Configuration (30-50m)

```json
{
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 30.0,
    "max_altitude": 50.0
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
    "altitude_adaptive": true,
    "high_altitude_damping_boost": 0.5
  },
  "pid": {
    "position_x": {
      "kp": 0.4,
      "ki": 0.05,
      "kd": 0.3
    },
    "position_y": {
      "kp": 0.4,
      "ki": 0.05,
      "kd": 0.3
    }
  }
}
```

### Recommended PID Gains by Altitude

| Altitude  | Kp  | Ki   | Kd  | Reasoning |
|-----------|-----|------|-----|-----------|
| 0-10m     | 0.5 | 0.10 | 0.2 | Fast response, aggressive |
| 10-20m    | 0.45| 0.08 | 0.25| Slightly more conservative |
| 20-30m    | 0.4 | 0.05 | 0.3 | Increased damping (Kd) |
| 30-40m    | 0.35| 0.03 | 0.35| Reduced aggression, high damping |
| 40-50m    | 0.3 | 0.02 | 0.4 | Maximum stability emphasis |

**Key Principle**: As altitude increases:
- ↓ Decrease Kp (less aggressive position correction)
- ↓ Decrease Ki (prevent integral windup from noise)
- ↑ Increase Kd (more damping to resist oscillations)

## Altitude Source Setup

### Option 1: MAVLink (Recommended for 30m+)

**Setup:**

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

**Wiring:**
```
Flight Controller TX -> Pi RX (GPIO 15 / Pin 10)
Flight Controller RX -> Pi TX (GPIO 14 / Pin 8)
GND -> GND
```

**Advantages:**
- ✅ Real-time altitude updates
- ✅ Already available from flight controller
- ✅ Works at any altitude
- ✅ Fused from multiple sources (baro, GPS, rangefinder)

**Setup Commands:**
```bash
# Enable serial port
sudo raspi-config
# Interface Options -> Serial Port -> 
#   Login shell: No
#   Serial hardware: Yes

# Test MAVLink connection
python3 -c "from pymavlink import mavutil; m = mavutil.mavlink_connection('/dev/ttyAMA0', baud=115200); m.wait_heartbeat(); print('OK')"
```

### Option 2: Rangefinder (Best Accuracy)

**Setup:**

```json
{
  "altitude": {
    "enabled": true,
    "type": "rangefinder",
    "port": "/dev/ttyUSB0",
    "baudrate": 115200,
    "protocol": "benewake"
  }
}
```

**Supported Rangefinders:**
- **Benewake TFmini Plus**: 0.1-12m range (standard)
- **Benewake TF03**: 0.1-180m range (long range, recommended for 30m+)
- **LightWare SF11**: 0.5-120m range (excellent for high altitude)
- **LeddarOne**: 0.5-40m range

**Advantages:**
- ✅ Most accurate altitude measurement
- ✅ Direct ground measurement
- ✅ Fast update rate (100+ Hz)

**Limitations:**
- ⚠️ Limited maximum range (check sensor specs)
- ⚠️ Affected by ground slope
- ⚠️ May lose tracking over water/uniform surfaces

### Option 3: Barometer (Backup)

**Setup:**

```json
{
  "altitude": {
    "enabled": true,
    "type": "barometer",
    "sensor": "bmp280",
    "i2c_bus": 1
  }
}
```

**Calibration Required:**
```python
from altitude_source import BarometerAltitudeSource

# On ground before takeoff
baro = BarometerAltitudeSource(sensor_type='bmp280')
baro.calibrate_takeoff_altitude()  # Sets reference altitude

# Now ready for flight
altitude = baro.get_altitude()  # Returns AGL altitude
```

**Advantages:**
- ✅ Unlimited altitude range
- ✅ No line-of-sight required
- ✅ Low cost

**Limitations:**
- ⚠️ Requires ground calibration before each flight
- ⚠️ Affected by weather/pressure changes
- ⚠️ Lower accuracy than rangefinder (~0.5-1m error)

### Option 4: Fused Sources (Most Reliable)

Combines multiple altitude sources:

```json
{
  "altitude": {
    "enabled": true,
    "type": "fused",
    "sources": [
      {
        "type": "rangefinder",
        "port": "/dev/ttyUSB0",
        "protocol": "benewake",
        "weight": 2.0
      },
      {
        "type": "mavlink",
        "connection": "/dev/ttyAMA0",
        "weight": 1.0
      },
      {
        "type": "barometer",
        "sensor": "bmp280",
        "weight": 0.5
      }
    ]
  }
}
```

**How Fusion Works:**
1. Reads altitude from all available sources
2. Weights each source by reliability
3. Computes weighted average
4. Automatically adapts if sources drop out

## Flight Operations at High Altitude

### Pre-Flight Checklist

1. **Altitude Source Check**:
   ```bash
   python3 altitude_source.py  # Test altitude reading
   ```

2. **Sensor Quality Check**:
   - Verify surface quality > 30 at target altitude
   - Check tracking confidence > 0.5

3. **Configuration Review**:
   - Confirm `max_altitude` set appropriately
   - Verify PID gains suitable for altitude
   - Enable altitude_adaptive mode

4. **Safety Limits**:
   - Set failsafe altitude in flight controller
   - Configure geofence if available
   - Plan emergency landing zones

### Ascent Procedure

1. **Takeoff at Low Altitude** (< 2m):
   - Engage position hold
   - Verify stable hover
   - Monitor tracking confidence

2. **Gradual Climb** (2m -> 15m):
   - Climb at ~2 m/s
   - Watch surface quality metrics
   - System auto-adapts filtering

3. **Medium Altitude Hold** (15m):
   - Test position hold
   - Observe damping increase
   - Verify no oscillations

4. **Continue to Target Altitude** (15m -> 30m+):
   - Maintain slow climb rate
   - Monitor tracking confidence (should stay > 0.5)
   - System increases damping automatically

5. **High Altitude Hold** (30m+):
   - Engage position hold
   - Allow 5-10 seconds for system adaptation
   - Monitor altitude and confidence logs

### In-Flight Monitoring

Watch these metrics during high altitude hold:

```bash
# Real-time monitoring via logs
./betafly_stabilizer_advanced.py -v

# Key metrics to watch:
# - Alt: Current altitude in meters
# - Conf: Tracking confidence (>0.5 good, >0.7 excellent)
# - Quality: Surface quality (>30 acceptable at high altitude)
# - Vel: Velocity should be near zero in position hold
```

**Normal Values at 30-50m:**
- Surface Quality: 30-80 (lower than low altitude)
- Tracking Confidence: 0.5-0.8
- Velocity Drift: < 0.5 m/s
- Position Error: < 2-3 meters

**Warning Signs:**
- ⚠️ Confidence < 0.4: Consider descending
- ⚠️ Quality < 20: Poor surface tracking
- ⚠️ Increasing oscillations: Reduce Kp, increase Kd
- ⚠️ Drift > 1 m/s: Increase damping boost

### Descent Procedure

1. **Exit Position Hold**: Switch to velocity damping mode
2. **Gradual Descent**: 2-3 m/s descent rate
3. **Monitor Confidence**: Should increase as altitude decreases
4. **Re-engage Position Hold**: Below 20m if needed
5. **Final Approach**: Manual or assisted landing

## Troubleshooting

### Position Drift at High Altitude

**Symptoms**: Drone drifts horizontally at 30m+ altitude

**Causes & Solutions**:

1. **Insufficient Altitude Input**:
   - ❌ Using static altitude while actually ascending/descending
   - ✅ Enable MAVLink or rangefinder altitude source

2. **Scale Factor Mismatch**:
   - Check `scale_factor` in config
   - At 30m, try increasing by 10-20%: `0.001 -> 0.0011`

3. **Low Surface Quality**:
   - Surface quality < 30 unreliable
   - Solution: Descend or fly over higher texture terrain

4. **Insufficient Damping**:
   - Increase `high_altitude_damping_boost`: `0.5 -> 0.8`
   - Or increase base `velocity_damping`: `0.3 -> 0.4`

### Oscillations at High Altitude

**Symptoms**: Drone oscillates back and forth

**Causes & Solutions**:

1. **Excessive Proportional Gain**:
   - Reduce Kp: `0.5 -> 0.35`

2. **Insufficient Derivative Damping**:
   - Increase Kd: `0.2 -> 0.35`

3. **Altitude-Adaptive Damping Disabled**:
   - Set `altitude_adaptive: true` in config

4. **Delayed Altitude Updates**:
   - Check altitude source update rate
   - Switch to faster source (rangefinder > MAVLink > barometer)

### Low Tracking Confidence

**Symptoms**: Confidence < 0.5 at high altitude

**Expected at 30m+**: Confidence naturally lower than low altitude

**Improvements**:

1. **Better Ground Texture**:
   - Fly over areas with visible features
   - Avoid uniform surfaces (water, concrete, grass fields)

2. **Lighting Conditions**:
   - Midday sun: Good for most sensors
   - Caddx Infra 256: Works in low light (infrared)
   - Avoid direct sunlight on sensor lens

3. **Sensor Selection**:
   - Standard sensors: Good to ~15m
   - Caddx Infra 256: Good to ~30m
   - Caddx 256CA Analog: Best performance 30-50m (analog video processing)

4. **Slower Movements**:
   - Reduce maximum velocity
   - Give system time to track

### Altitude Reading Unavailable

**Symptoms**: System reports altitude errors or uses fixed altitude

**Solutions**:

1. **MAVLink Connection**:
   ```bash
   # Check MAVLink
   ls /dev/ttyAMA0  # Should exist
   sudo cat /dev/ttyAMA0  # Should show data
   ```

2. **Rangefinder Connection**:
   ```bash
   # Check USB rangefinder
   ls /dev/ttyUSB*  # Find correct port
   # Update port in config
   ```

3. **Barometer Calibration**:
   ```python
   # Recalibrate before flight
   baro.calibrate_takeoff_altitude()
   ```

4. **Fallback to Static**:
   - Manually set altitude if sensors fail
   - Update via web interface or config

## Performance Expectations

### Realistic Performance by Altitude

| Altitude | Position Accuracy | Max Wind | Recommended Use |
|----------|-------------------|----------|-----------------|
| 0-10m    | ±0.1-0.3m        | 15 mph   | Precision tasks |
| 10-20m   | ±0.3-0.5m        | 12 mph   | Photography, inspection |
| 20-30m   | ±0.5-1.0m        | 10 mph   | Mapping, surveying |
| 30-40m   | ±1.0-2.0m        | 8 mph    | Area coverage |
| 40-50m   | ±2.0-3.0m        | 5 mph    | High overview |

### Battery Consumption

High altitude operation typically uses **10-20% more battery** due to:
- Increased processing (more filtering)
- More aggressive control corrections
- Wind resistance at altitude

**Recommendation**: Reserve 30% battery for safe descent and landing.

## Best Practices

### Do's ✅

1. **Test at Low Altitude First**: Verify system works below 10m
2. **Gradual Ascent**: Climb slowly to allow system adaptation
3. **Monitor Confidence**: Watch tracking confidence metrics
4. **Use Altitude Source**: Enable MAVLink or rangefinder for accuracy
5. **Adjust PID Gains**: Reduce aggression at high altitude
6. **Plan Descent Path**: Have clear descent strategy
7. **Check Weather**: Calm conditions essential above 30m
8. **Good Ground Texture**: Fly over areas with visible features

### Don'ts ❌

1. **Don't Disable Altitude Adaptive**: Keep `altitude_adaptive: true`
2. **Don't Use Aggressive PIDs**: High Kp causes oscillations
3. **Don't Ignore Warnings**: Heed low confidence alerts
4. **Don't Fly in Wind**: High altitude + wind = difficult tracking
5. **Don't Rapid Altitude Changes**: System needs time to adapt
6. **Don't Exceed Max Altitude**: Stay within configured limits
7. **Don't Forget Failsafes**: Set controller failsafe altitude
8. **Don't Skip Testing**: Always test at low altitude first

## Example Configurations

### Configuration 1: Conservative (30-35m)

```json
{
  "tracker": {
    "scale_factor": 0.001,
    "max_altitude": 40.0
  },
  "altitude": {
    "enabled": true,
    "type": "mavlink"
  },
  "stabilizer": {
    "velocity_damping": 0.35,
    "altitude_adaptive": true,
    "high_altitude_damping_boost": 0.6
  },
  "pid": {
    "position_x": {"kp": 0.35, "ki": 0.03, "kd": 0.35},
    "position_y": {"kp": 0.35, "ki": 0.03, "kd": 0.35}
  }
}
```

**Use Case**: First time high altitude, prioritize stability

### Configuration 2: Balanced (35-45m)

```json
{
  "tracker": {
    "scale_factor": 0.0011,
    "max_altitude": 50.0
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
    "velocity_damping": 0.3,
    "altitude_adaptive": true,
    "high_altitude_damping_boost": 0.5
  },
  "pid": {
    "position_x": {"kp": 0.4, "ki": 0.05, "kd": 0.3},
    "position_y": {"kp": 0.4, "ki": 0.05, "kd": 0.3}
  }
}
```

**Use Case**: General purpose high altitude operation

### Configuration 3: Maximum Altitude (45-50m)

```json
{
  "tracker": {
    "scale_factor": 0.0012,
    "max_altitude": 50.0
  },
  "altitude": {
    "enabled": true,
    "type": "rangefinder",
    "protocol": "benewake"
  },
  "stabilizer": {
    "velocity_damping": 0.4,
    "altitude_adaptive": true,
    "high_altitude_damping_boost": 0.8
  },
  "pid": {
    "position_x": {"kp": 0.3, "ki": 0.02, "kd": 0.4},
    "position_y": {"kp": 0.3, "ki": 0.02, "kd": 0.4}
  }
}
```

**Use Case**: Maximum altitude with emphasis on stability

### Configuration 4: Analog Camera (Advanced Processing)

```json
{
  "sensor": {
    "type": "analog_usb"
  },
  "camera": {
    "device": "/dev/video0",
    "width": 720,
    "height": 480,
    "fps": 30,
    "method": "farneback"
  },
  "tracking": {
    "enabled": true,
    "mode": "stabilization_enhanced",
    "stabilization_strength": 0.8
  },
  "tracker": {
    "scale_factor": 0.0011,
    "max_altitude": 50.0
  },
  "altitude": {
    "enabled": true,
    "type": "mavlink"
  },
  "stabilizer": {
    "velocity_damping": 0.3,
    "altitude_adaptive": true,
    "high_altitude_damping_boost": 0.5
  }
}
```

**Use Case**: Best tracking quality with AI enhancement

## Web Interface Monitoring

Access real-time altitude metrics via web interface:

```bash
# Start with web interface
./betafly_stabilizer_advanced.py

# Open browser
http://raspberrypi.local:8080
```

**High Altitude Dashboard Shows:**
- Current altitude (real-time)
- Tracking confidence (should stay > 0.5)
- Surface quality
- Position hold accuracy
- Velocity (should be near zero)
- Altitude validity indicator

## Safety Considerations

### Emergency Procedures

1. **Low Confidence (<0.4)**:
   - Switch to velocity damping mode
   - Descend to lower altitude
   - Re-engage position hold below 20m

2. **Position Runaway**:
   - Immediately switch to manual control
   - Descend quickly but safely
   - Do not rely on position hold until diagnosed

3. **Altitude Source Failure**:
   - System will use last known altitude
   - Land as soon as safely possible
   - Fix altitude source before next flight

4. **High Wind Conditions**:
   - Position hold struggles above 10 mph wind at 30m+
   - Descend to lower altitude
   - Land if wind continues

### Flight Controller Integration

Configure flight controller failsafes:

```
# Example ArduPilot parameters
ALTITUDE_MAX = 50     # Maximum altitude limit
FS_THR_ENABLE = 1     # Enable throttle failsafe
FS_THR_VALUE = 975    # Failsafe PWM value
RTL_ALT = 15          # Return home at 15m (lower altitude)
LAND_SPEED = 50       # Landing speed cm/s
```

## Conclusion

High altitude position hold (30m+) is achievable with proper configuration and altitude-adaptive algorithms. The system automatically adjusts filtering, scaling, and control gains based on current altitude. For best results:

1. Use real-time altitude source (MAVLink or rangefinder)
2. Enable altitude-adaptive mode
3. Reduce PID aggression at high altitude
4. Monitor tracking confidence
5. Fly in calm conditions
6. Test thoroughly at lower altitudes first

**Success depends on**: Good ground texture, accurate altitude measurement, conservative PID tuning, and calm weather conditions.

---

**For additional support**: See main README.md, check web interface diagnostics, and review system logs for detailed altitude and confidence metrics.

**Happy High-Altitude Flying! 🚁⬆️**
