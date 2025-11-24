# GPS Emulation Guide

## Overview

The Raspberry Pi Zero can act as a **GPS module** for the flight controller, sending optical flow-based position data as GPS coordinates via UART. The flight controller thinks it's receiving data from a real GPS and can perform its own position hold using standard GPS modes.

## How It Works

```
┌─────────────────┐
│ Optical Flow    │
│ Sensor          │
└────────┬────────┘
         │ Motion data
         ↓
┌─────────────────┐
│ Raspberry Pi    │
│ - Tracks position (meters)
│ - Converts to GPS coordinates
│ - Sends NMEA/MAVLink messages
└────────┬────────┘
         │ UART (GPS data)
         ↓
┌─────────────────┐
│ Flight Controller│
│ - Receives "GPS" data
│ - Thinks GPS is connected
│ - Does position hold with GPS mode
└─────────────────┘
```

##Benefits

### Why GPS Emulation?

1. **Flight Controller Does Control**: FC handles all position hold logic
2. **Standard GPS Modes**: Use normal GPS loiter/position hold modes
3. **No Custom Firmware**: FC runs standard firmware
4. **Simple Integration**: Just UART connection required
5. **FC Tuning**: Use FC's existing GPS position PID tuning
6. **Failsafes**: FC's GPS failsafes work normally

### Advantages Over Direct Control

| Approach | GPS Emulation | Direct Control (Pi commands) |
|----------|---------------|------------------------------|
| FC Workload | FC does position hold | FC just stabilizes attitude |
| Pi Workload | Just send position | Calculate + send corrections |
| FC Configuration | Standard GPS setup | Need external position mode |
| Failsafes | Built-in GPS failsafes | Need custom failsafes |
| Tuning | Use FC's GPS PIDs | Need separate PID tuning |
| Complexity | Simple | Complex |

## Hardware Setup

### Wiring

```
Raspberry Pi Zero -> Flight Controller
─────────────────────────────────────
GPIO 14 (TX) -> GPS RX on FC
GPIO 15 (RX) -> GPS TX on FC (optional, not needed for GPS data)
GND -> GND
```

**Important Notes:**
- Connect Pi TX to FC's GPS RX pin
- Most FCs have dedicated GPS UART port
- Check FC documentation for GPS port location
- Common locations: UART3, UART4, or labeled "GPS"

### Flight Controller Configuration

#### For Betaflight/iNav:
```
# Enable GPS on correct UART
set gps_provider = NMEA
set gps_sbas_mode = AUTO
set gps_auto_config = ON
set gps_auto_baud = ON

# Configure UART (example for UART3)
serial 2 1024 115200 57600 0 115200

save
```

#### For ArduPilot:
```
# Set GPS type and port
GPS_TYPE = 1  (AUTO)
SERIAL3_PROTOCOL = 5  (GPS)
SERIAL3_BAUD = 115 (115200)
GPS_AUTO_SWITCH = 0
```

#### For PX4:
```
# Enable GPS on TELEM2 (or appropriate port)
GPS_1_CONFIG = GPS 1
SER_GPS1_BAUD = 115200
```

## Configuration

### Basic Configuration

Edit `config.json`:

```json
{
  "gps_emulation": {
    "enabled": true,
    "protocol": "nmea",
    "port": "/dev/ttyAMA0",
    "baudrate": 115200,
    "update_rate_hz": 5,
    "home_lat": 37.7749,
    "home_lon": -122.4194,
    "home_alt": 10.0
  }
}
```

### Parameters

#### `enabled` (boolean)
- Enable/disable GPS emulation
- `true`: Pi acts as GPS module
- `false`: Direct control mode (Pi sends corrections)

#### `protocol` (string)
- `"nmea"`: NMEA 0183 protocol (recommended, most compatible)
- `"mavlink"`: MAVLink GPS_INPUT messages (for MAVLink-based FCs)

#### `port` (string)
- Serial port for UART communication
- Raspberry Pi: `/dev/ttyAMA0` (primary UART)
- Alternative: `/dev/ttyS0` (mini UART, less reliable)

#### `baudrate` (integer)
- Serial baudrate (must match FC GPS settings)
- Common: `9600`, `38400`, `57600`, `115200`
- Recommended: `115200` for NMEA, `57600` also common

#### `update_rate_hz` (integer)
- GPS update rate (messages per second)
- Range: 1-10 Hz
- Recommended: 5 Hz (good balance)
- Lower = less CPU load
- Higher = more frequent updates

#### `home_lat`, `home_lon`, `home_alt` (float)
- Home position (takeoff location)
- `home_lat`: Latitude in degrees
- `home_lon`: Longitude in degrees
- `home_alt`: Altitude in meters MSL

**Important**: Set these to your actual takeoff location for accurate GPS emulation!

## Setting Home Position

### Option 1: Manual Configuration

Get coordinates from:
- Google Maps (right-click → coordinates)
- GPS app on phone
- Existing GPS module reading

Update `config.json`:
```json
"home_lat": 37.7749,    // Your latitude
"home_lon": -122.4194,  // Your longitude
"home_alt": 50.0        // Your ground elevation MSL
```

### Option 2: Programmatic (Future Enhancement)

```python
# Set home position at takeoff
if gps_emulator:
    gps_emulator.set_home_position(
        lat=current_gps_lat,
        lon=current_gps_lon,
        alt=current_gps_alt
    )
```

### Why Home Position Matters

The system converts local position (meters from optical flow) to GPS coordinates:

```
Local Position: 10m East, 5m North from takeoff
    ↓ (using home position)
GPS Coordinates: 37.7750°N, 122.4193°W

Without accurate home position:
- GPS coordinates will be wrong
- But relative position hold still works!
```

## NMEA Protocol (Recommended)

### What is NMEA?

NMEA 0183 is the standard GPS protocol used by most flight controllers.

### Messages Sent

The system sends two NMEA sentences every update:

#### GPGGA - Global Positioning System Fix Data
```
$GPGGA,123456.00,3746.494,N,12225.164,W,3,12,1.0,50.0,M,0.0,M,,*XX
```
- Time, position, fix quality, satellites, altitude

#### GPRMC - Recommended Minimum
```
$GPRMC,123456.00,A,3746.494,N,12225.164,W,1.94,45.0,241124,,,A*XX
```
- Time, position, speed, course, date

### Format Details

**Position Format**: DDMM.MMMM (degrees and decimal minutes)
- Example: 3746.494 N = 37° 46.494' N = 37.7749° N

**Fix Type**:
- `1`: No fix
- `2`: 2D fix
- `3`: 3D fix (we send this)

**Satellites**: Reports 12 satellites (simulated, FC doesn't verify)

**HDOP**: 1.0 (good dilution of precision)

## MAVLink Protocol (Advanced)

### When to Use MAVLink

- FC already uses MAVLink for telemetry
- Want richer GPS data (more fields)
- Need GPS_INPUT message support

### Message Sent

```
GPS_INPUT message:
- Timestamp (microseconds)
- GPS ID: 0
- Fix type: 3D fix
- Latitude/Longitude (degrees × 1e7)
- Altitude (millimeters)
- Velocities (cm/s)
- Horizontal/vertical accuracy
- Speed accuracy
- Satellites: 12
```

### Advantages

- More comprehensive data
- Accuracy estimates included
- Velocity vectors (North, East, Down)
- Better integration with MAVLink systems

### Disadvantages

- More complex protocol
- Not all FCs support GPS_INPUT
- Requires pymavlink library

## Flight Operations

### Pre-Flight Setup

1. **Configure Home Position**:
   ```bash
   # Edit config.json with actual coordinates
   nano config.json
   # Set home_lat, home_lon, home_alt
   ```

2. **Enable GPS Emulation**:
   ```json
   "gps_emulation": {
     "enabled": true
   }
   ```

3. **Start System**:
   ```bash
   ./betafly_stabilizer_advanced.py
   ```

4. **Verify GPS on FC**:
   - Check FC OSD/GUI
   - Should show "GPS: 12 satellites"
   - Should show "3D fix"
   - Position should appear reasonable

### Flight Procedure

1. **Takeoff**:
   - Normal takeoff in manual/stabilize mode
   - Optical flow starts tracking position

2. **Enable GPS Mode**:
   - Switch to GPS loiter/position hold mode
   - FC now uses "GPS" for position hold
   - FC commands pitch/roll to maintain position

3. **Position Hold**:
   - FC maintains position using GPS data
   - Optical flow provides position updates
   - System handles altitude changes automatically

4. **Landing**:
   - Can land in GPS mode or manual
   - System continues sending GPS data until shutdown

### Important Notes

⚠️ **The "GPS" position is relative to takeoff point**, not absolute!
- If you take off at one location
- Fly 10m away
- Land and take off again at same spot
- "GPS" will show different coordinates (home position changed)

✅ **For flight controller, this is fine:**
- FC just wants stable position data
- Doesn't care about absolute coordinates
- Position hold works perfectly

## Troubleshooting

### FC Not Detecting GPS

**Check Serial Connection**:
```bash
# Verify UART is enabled
ls -l /dev/ttyAMA0  # Should exist

# Test serial output
cat /dev/ttyAMA0 &  # Run in background
# Start betafly system
# Should see NMEA sentences: $GPGGA... $GPRMC...
```

**Check FC Configuration**:
- Is GPS UART enabled?
- Correct baudrate? (115200)
- GPS type set to AUTO or NMEA?

**Check Wiring**:
- Pi TX → FC RX (not TX to TX!)
- GND connected
- Correct FC pin (check manual)

### GPS Fix Shows "No Fix" or "2D Fix"

**Check NMEA Messages**:
```python
# Test GPS emulation standalone
python3 gps_emulation.py
```

**Verify Data**:
- Fix type should be `3` in GPGGA
- Satellites should be > 5
- HDOP should be reasonable (< 2.0)

**Most Common**: Home position not set
- FC sees GPS data but rejects bad coordinates
- Solution: Set valid home_lat/home_lon

### Position Hold Drifts

**This is Normal Behavior**:
- Optical flow has drift over time
- "GPS" position will slowly drift
- This is expected, not a bug

**Mitigation**:
- Use altitude-adaptive tracking
- Enable barometer velocity
- Fly at optimal altitude (0.5-2m)
- Good ground texture helps

**Remember**: This is optical flow limitation, not GPS emulation issue

### "GPS" Position Jumps

**Possible Causes**:
1. **Lost optical flow tracking**:
   - Surface quality dropped
   - Solution: Better lighting/texture

2. **Altitude changed rapidly**:
   - Optical flow scale changed
   - Solution: Gradual altitude changes

3. **System reset**:
   - Position tracking reset
   - Solution: Don't reset during flight

### FC Failsafes Triggering

**GPS Failsafe Activating**:
- FC lost GPS messages
- Check serial connection
- Verify system still running

**Position Jump Failsafe**:
- FC detected large position change
- Increase FC's GPS glitch tolerance
- Betaflight: `gps_rescue_sanity_checks`

## Performance Considerations

### Update Rates

```
Component               Rate
─────────────────────────────
Optical Flow Sensor     50-100 Hz
Position Calculation    50 Hz
GPS Emulation           5 Hz (configurable)
FC GPS Processing       5-10 Hz
```

**Why 5 Hz for GPS?**
- Real GPS updates at 5-10 Hz
- FC expects this rate
- Lower CPU load
- Sufficient for position hold

### CPU Load

**With GPS Emulation**:
- Pi: ~20-30% CPU (optical flow + GPS messages)
- FC: Standard GPS processing load
- FC does position control

**Without GPS Emulation** (direct control):
- Pi: ~30-40% CPU (optical flow + PID control)
- FC: Minimal (just attitude stabilization)
- Pi does position control

### Latency

```
Optical Flow Reading → Position Calculation → GPS Message → FC
      ~10ms                 ~20ms               ~5ms        ~10ms
      
Total Latency: ~45ms (acceptable for position hold)
```

## Advanced Configuration

### Multiple Serial Ports

If FC needs UART for both GPS and telemetry:

**Option 1**: Use different UARTs
```json
// GPS emulation on UART0
"gps_emulation": {
  "port": "/dev/ttyAMA0"
}

// MAVLink telemetry on USB
"altitude": {
  "type": "mavlink",
  "connection": "/dev/ttyACM0"
}
```

**Option 2**: Software serial (not recommended)
- Poor reliability
- Use hardware UART when possible

### Custom Update Rates

```json
"gps_emulation": {
  "update_rate_hz": 10  // Faster updates
}
```

**Trade-offs**:
- Higher rate = more CPU load
- Higher rate = more serial bandwidth
- Higher rate = slightly lower latency
- Most FCs work best at 5-10 Hz

### Protocol Selection

**Use NMEA when**:
- Standard FC (Betaflight, iNav, most FCs)
- Simple setup required
- Maximum compatibility

**Use MAVLink when**:
- ArduPilot/PX4 based system
- Already using MAVLink
- Want richer GPS data

## Example Configurations

### Indoor Hover (Simple)

```json
{
  "sensor": {"type": "caddx_infra256"},
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 1.0,
    "use_visual_coords": true
  },
  "gps_emulation": {
    "enabled": true,
    "protocol": "nmea",
    "port": "/dev/ttyAMA0",
    "baudrate": 115200,
    "update_rate_hz": 5,
    "home_lat": 37.7749,
    "home_lon": -122.4194,
    "home_alt": 10.0
  }
}
```

### Outdoor Flight (with MAVLink telemetry)

```json
{
  "sensor": {"type": "caddx_infra256"},
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 2.0,
    "use_visual_coords": true
  },
  "altitude": {
    "enabled": true,
    "type": "mavlink",
    "connection": "/dev/ttyUSB0"  // USB telemetry
  },
  "gps_emulation": {
    "enabled": true,
    "protocol": "nmea",
    "port": "/dev/ttyAMA0",  // Hardware UART for GPS
    "baudrate": 115200,
    "update_rate_hz": 5,
    "home_lat": 37.7749,
    "home_lon": -122.4194,
    "home_alt": 50.0
  }
}
```

### High Performance

```json
{
  "sensor": {"type": "pmw3901"},
  "tracker": {
    "scale_factor": 0.001,
    "initial_height": 0.5,
    "max_altitude": 30.0,
    "use_visual_coords": true
  },
  "gps_emulation": {
    "enabled": true,
    "protocol": "nmea",
    "baudrate": 115200,
    "update_rate_hz": 10,  // Faster updates
    "home_lat": 37.7749,
    "home_lon": -122.4194,
    "home_alt": 10.0
  },
  "control": {
    "update_rate_hz": 100  // High rate tracking
  }
}
```

## Testing

### Test GPS Emulation

```bash
# Test GPS emulation module
python3 gps_emulation.py

# Should show:
# - NMEA sentences generated
# - Coordinate conversions
# - Test output
```

### Monitor GPS Messages

```bash
# Monitor serial output
cat /dev/ttyAMA0

# Should see NMEA sentences:
# $GPGGA,123456.00,3746.494,N,12225.164,W,3,12,1.0,10.0,M,0.0,M,,*XX
# $GPRMC,123456.00,A,3746.494,N,12225.164,W,0.00,0.00,241124,,,A*XX
```

### Verify with FC

- Connect FC configurator
- Check GPS tab
- Should show:
  - Satellites: 12
  - Fix: 3D
  - Position updating
  - Reasonable coordinates

## Summary

**GPS Emulation allows**:
- ✅ Pi acts as GPS module for FC
- ✅ FC does position hold with standard GPS modes
- ✅ Simple UART connection
- ✅ No custom FC firmware needed
- ✅ Standard GPS failsafes work

**How it works**:
1. Optical flow tracks position (meters)
2. Pi converts to GPS coordinates
3. Sends NMEA/MAVLink via UART
4. FC thinks it has GPS
5. FC does position hold

**Key Points**:
- Set correct home position (lat/lon/alt)
- Use NMEA protocol for most FCs
- 5 Hz update rate is sufficient
- Connect Pi TX to FC GPS RX
- FC handles position control

**Result**: Robust optical flow-based position hold using FC's built-in GPS modes! 🚁📡

---

For more information see:
- [VISUAL_COORDINATES_GUIDE.md](VISUAL_COORDINATES_GUIDE.md) - Visual coordinates
- [HIGH_ALTITUDE_GUIDE.md](HIGH_ALTITUDE_GUIDE.md) - High altitude operations
- [README.md](README.md) - Main documentation
