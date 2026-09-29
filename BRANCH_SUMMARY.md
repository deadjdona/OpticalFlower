# Branch Summary

## Quick Branch Selection Guide

This repository has **3 branches** optimized for different use cases:

---

### 🔵 Betaflight Branch
```bash
git checkout betaflight
./start_betaflight.sh
```

**For**: Betaflight, iNav flight controllers  
**GPS Protocol**: NMEA (simple, compatible)  
**FC Interface**: MSP  
**Best With**: Raspberry Pi Zero W  
**Use Case**: Simple indoor position hold  

**Configuration**: `config.betaflight.json`  
**Documentation**: `README.betaflight.md`

---

### 🟢 ArduPilot Branch
```bash
git checkout ardupilot
./start_ardupilot.sh
```

**For**: ArduPilot, PX4 flight controllers  
**GPS Protocol**: MAVLink GPS_INPUT (advanced)  
**FC Interface**: MAVLink (full integration)  
**Best With**: Raspberry Pi Zero 2W  
**Use Case**: Autonomous missions, outdoor flight  

**Configuration**: `config.ardupilot.json`  
**Documentation**: `README.ardupilot.md`

---

### ⚪ Main Branch (Current)
```bash
git checkout main
./betafly_stabilizer_advanced.py
```

**For**: All flight controllers, flexible setup  
**GPS Protocol**: Both NMEA and MAVLink  
**FC Interface**: MSP, MAVLink, PWM  
**Best With**: Any Raspberry Pi  
**Use Case**: Development, testing, maximum flexibility  

**Configuration**: `config.json` (fully configurable)  
**Documentation**: `README.md`

---

## Feature Matrix

| Feature | Betaflight | ArduPilot | Main |
|---------|:----------:|:---------:|:----:|
| **NMEA GPS** | ✅ | ✅ | ✅ |
| **MAVLink GPS** | ❌ | ✅ | ✅ |
| **MSP Protocol** | ✅ | ❌ | ✅ |
| **MAVLink Protocol** | ❌ | ✅ | ✅ |
| **Barometer Velocity** | Optional | ✅ | ✅ |
| **EKF Integration** | ❌ | ✅ | ✅ |
| **Autonomous Missions** | ❌ | ✅ | ✅ |
| **Optimized For** | Pi Zero W | Pi Zero 2W | Any Pi |

---

## Which Branch Should I Use?

### Choose **Betaflight** if:
- ✅ You're using Betaflight or iNav
- ✅ You want the simplest setup
- ✅ You're flying indoors
- ✅ You have a Pi Zero W

### Choose **ArduPilot** if:
- ✅ You're using ArduPilot or PX4
- ✅ You want autonomous waypoint missions
- ✅ You need barometer integration
- ✅ You have a Pi Zero 2W

### Choose **Main** if:
- ✅ You want maximum flexibility
- ✅ You're testing different configurations
- ✅ You're developing new features
- ✅ You're unsure which FC you'll use

---

## Installation Quick Start

### Betaflight Users:
```bash
git clone https://github.com/deadjdona/OpticalFlower.git
cd OpticalFlower
git checkout betaflight
cp config.betaflight.json config.json
# Edit config.json with your home position
./start_betaflight.sh
```

### ArduPilot Users:
```bash
git clone https://github.com/deadjdona/OpticalFlower.git
cd OpticalFlower
git checkout ardupilot
cp config.ardupilot.json config.json
# Edit config.json with your home position
./start_ardupilot.sh
```

### Universal Setup:
```bash
git clone https://github.com/deadjdona/OpticalFlower.git
cd OpticalFlower
# Edit config.json for your specific setup
./betafly_stabilizer_advanced.py
```

---

## Full Documentation

- **[BRANCH_INFO.md](BRANCH_INFO.md)** - Complete branch comparison
- **[README.md](README.md)** - Main documentation (this branch)
- **[GPS_EMULATION_GUIDE.md](GPS_EMULATION_GUIDE.md)** - GPS emulation setup

**Branch-Specific Docs:**
- `README.betaflight.md` (in betaflight branch)
- `README.ardupilot.md` (in ardupilot branch)

---

**Need help choosing?** See the [full branch comparison](BRANCH_INFO.md).
