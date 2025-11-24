# Branch Information

This repository has multiple optimized branches for different flight controller firmwares.

## Available Branches

### 🔵 `betaflight` - Betaflight/iNav Optimized
**Best for**: Betaflight and iNav flight controllers

**Key Features:**
- NMEA GPS emulation (most compatible)
- MSP protocol support
- Lightweight configuration
- Optimized for Pi Zero W
- Simple setup

**Default Settings:**
- GPS Protocol: NMEA
- FC Interface: MSP
- GPS Update Rate: 5Hz
- Control Rate: 50Hz
- Altitude: Static (simple)

**Target Hardware:**
- Raspberry Pi Zero W (minimum)
- Raspberry Pi Zero 2W (recommended)

**Documentation:**
- See `README.betaflight.md`
- Run: `./start_betaflight.sh`

---

### 🟢 `ardupilot` - ArduPilot/PX4 Optimized
**Best for**: ArduPilot and PX4 flight controllers

**Key Features:**
- MAVLink GPS_INPUT (advanced)
- Full MAVLink integration
- Barometer altitude + velocity
- EKF sensor fusion ready
- Autonomous mission support

**Default Settings:**
- GPS Protocol: MAVLink GPS_INPUT
- FC Interface: MAVLink (shared connection)
- GPS Update Rate: 10Hz
- Control Rate: 100Hz (Pi Zero 2W), 50Hz (Pi Zero W)
- Altitude: MAVLink (barometer + velocity)

**Target Hardware:**
- Raspberry Pi Zero 2W (recommended)
- Raspberry Pi Zero W (reduced features)

**Documentation:**
- See `README.ardupilot.md`
- Run: `./start_ardupilot.sh`

---

### ⚪ `main` - Universal (All Flight Controllers)
**Best for**: Flexibility, testing, development

**Key Features:**
- Supports both NMEA and MAVLink GPS emulation
- MSP and MAVLink FC interfaces
- All sensors supported
- All altitude sources
- Configurable for any setup

**Default Settings:**
- GPS Protocol: Configurable
- FC Interface: Configurable
- All options available

**Target Hardware:**
- Any Raspberry Pi with GPIO

**Documentation:**
- See `README.md`
- Full configuration in `config.json`

---

## Quick Branch Selection

**Choose `betaflight` if:**
- ✅ Using Betaflight or iNav FC
- ✅ Want simplest setup
- ✅ Indoor hover/position hold
- ✅ Raspberry Pi Zero W is sufficient

**Choose `ardupilot` if:**
- ✅ Using ArduPilot or PX4 FC
- ✅ Want autonomous missions
- ✅ Need barometer integration
- ✅ Have Pi Zero 2W
- ✅ Planning outdoor flights

**Choose `main` if:**
- ✅ Need maximum flexibility
- ✅ Testing different configurations
- ✅ Contributing to development
- ✅ Using custom flight controller

## Switching Branches

```bash
# Clone repository
git clone https://github.com/yourusername/betafly-stabilization.git
cd betafly-stabilization

# For Betaflight
git checkout betaflight
./start_betaflight.sh

# For ArduPilot
git checkout ardupilot
./start_ardupilot.sh

# For Universal
git checkout main
./betafly_stabilizer_advanced.py
```

## Configuration Files

Each branch has its own optimized config:

| Branch | Config File | Default GPS | Default FC |
|--------|-------------|-------------|------------|
| `betaflight` | `config.betaflight.json` | NMEA | MSP |
| `ardupilot` | `config.ardupilot.json` | MAVLink | MAVLink |
| `main` | `config.json` | Configurable | Configurable |

## Feature Comparison

| Feature | Betaflight | ArduPilot | Main |
|---------|------------|-----------|------|
| NMEA GPS | ✅ Primary | ⚠️ Fallback | ✅ |
| MAVLink GPS | ❌ | ✅ Primary | ✅ |
| MSP Protocol | ✅ | ❌ | ✅ |
| MAVLink Protocol | ❌ | ✅ | ✅ |
| Barometer Velocity | ⚠️ Optional | ✅ Standard | ✅ |
| 3D Tracking | 2D (X,Y) | 3D (X,Y,Z) | Both |
| EKF Integration | ❌ | ✅ | ⚠️ Partial |
| Autonomous Missions | ❌ | ✅ | ⚠️ Partial |
| Optimization | Pi Zero W | Pi Zero 2W | Any |

## Performance Characteristics

### Betaflight Branch
- **CPU Usage**: ~20-30% (Pi Zero W)
- **Memory**: ~80MB
- **GPS Rate**: 5Hz
- **Control Rate**: 50Hz
- **Latency**: ~50ms
- **Best Altitude**: 0.5-2m

### ArduPilot Branch
- **CPU Usage**: ~40-50% (Pi Zero 2W), ~60-80% (Pi Zero W)
- **Memory**: ~100MB
- **GPS Rate**: 10Hz
- **Control Rate**: 100Hz (2W), 50Hz (W)
- **Latency**: ~30ms (2W), ~50ms (W)
- **Best Altitude**: 1-5m

### Main Branch
- **CPU Usage**: Varies by configuration
- **Memory**: ~90MB
- **GPS Rate**: Configurable
- **Control Rate**: Configurable
- **Latency**: Varies
- **Best Altitude**: Configurable

## Code Differences

### Betaflight Branch Optimizations
- Removed complex MAVLink features (except GPS emulation)
- Simplified altitude sources
- Reduced default update rates
- NMEA-focused GPS emulation
- Lightweight imports

### ArduPilot Branch Optimizations
- Enhanced MAVLink integration
- Barometer velocity by default
- Higher update rates
- MAVLink-focused GPS emulation
- Additional EKF support code

### Main Branch
- All features included
- Maximum flexibility
- Larger codebase
- More dependencies

## Maintenance

- **Betaflight**: Focuses on stability and simplicity
- **ArduPilot**: Focuses on features and performance
- **Main**: Focuses on compatibility and new features

## Contributing

**Bug fixes**: Apply to `main` first, then cherry-pick to branch-specific branches if applicable.

**New features**: 
- Universal features → `main`
- Betaflight-specific → `betaflight`
- ArduPilot-specific → `ardupilot`

**Optimization**:
- Branch-specific optimizations go to respective branches
- Don't break `main` branch compatibility

## Support Matrix

### Flight Controllers

| FC Firmware | Recommended Branch | Alternative Branch |
|-------------|-------------------|-------------------|
| Betaflight 4.x | `betaflight` | `main` |
| iNav 5.x, 6.x | `betaflight` | `main` |
| ArduPilot 4.x | `ardupilot` | `main` |
| PX4 1.13+ | `ardupilot` | `main` |

### Raspberry Pi Models

| Pi Model | Betaflight | ArduPilot | Main |
|----------|------------|-----------|------|
| Pi Zero W | ✅ Great | ⚠️ Limited | ✅ Good |
| Pi Zero 2W | ✅ Excellent | ✅ Excellent | ✅ Excellent |
| Pi 3 | ✅ Overkill | ✅ Great | ✅ Great |
| Pi 4 | ✅ Overkill | ✅ Great | ✅ Great |

## Getting Help

- **Betaflight issues**: Check `README.betaflight.md` and Betaflight forums
- **ArduPilot issues**: Check `README.ardupilot.md` and ArduPilot forums
- **General issues**: Check `README.md` and GitHub issues

---

**Choose the branch that best fits your flight controller and mission requirements!** 🚁
