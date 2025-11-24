"""
Altitude Source Module for High Altitude Position Hold
Supports multiple altitude input sources: barometer, rangefinder, GPS, MAVLink
"""

import time
import logging
from typing import Optional
from abc import ABC, abstractmethod

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import MAVLink
try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False
    logger.warning("pymavlink not available - MAVLink altitude source disabled")

# Try to import serial for rangefinder
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False


class AltitudeSource(ABC):
    """Base class for altitude sources"""
    
    @abstractmethod
    def get_altitude(self) -> Optional[float]:
        """Get current altitude in meters above ground level (AGL)"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if altitude source is available and functioning"""
        pass


class StaticAltitudeSource(AltitudeSource):
    """
    Static altitude source - returns fixed altitude
    Useful for testing or when altitude is manually set
    """
    
    def __init__(self, altitude_m: float = 0.5):
        """
        Initialize static altitude source
        
        Args:
            altitude_m: Fixed altitude in meters
        """
        self.altitude_m = altitude_m
        logger.info(f"Static altitude source initialized at {altitude_m}m")
    
    def get_altitude(self) -> Optional[float]:
        """Return fixed altitude"""
        return self.altitude_m
    
    def set_altitude(self, altitude_m: float):
        """Update fixed altitude"""
        self.altitude_m = altitude_m
        logger.info(f"Static altitude updated to {altitude_m}m")
    
    def is_available(self) -> bool:
        """Always available"""
        return True


class MAVLinkAltitudeSource(AltitudeSource):
    """
    MAVLink altitude source - reads from flight controller
    Uses GLOBAL_POSITION_INT message for relative altitude
    """
    
    def __init__(self, connection_string: str = '/dev/ttyAMA0', baudrate: int = 115200):
        """
        Initialize MAVLink altitude source
        
        Args:
            connection_string: MAVLink connection string (serial port or UDP)
            baudrate: Serial baudrate (if using serial)
        """
        if not MAVLINK_AVAILABLE:
            raise RuntimeError("pymavlink required for MAVLink altitude source")
        
        self.connection_string = connection_string
        self.baudrate = baudrate
        self.mavlink_conn = None
        self.last_altitude = None
        self.last_update_time = 0
        self.timeout = 2.0  # Timeout in seconds
        
        self._connect()
    
    def _connect(self):
        """Establish MAVLink connection"""
        try:
            if self.connection_string.startswith('/dev/'):
                # Serial connection
                self.mavlink_conn = mavutil.mavlink_connection(
                    self.connection_string,
                    baud=self.baudrate
                )
            else:
                # UDP or other connection
                self.mavlink_conn = mavutil.mavlink_connection(self.connection_string)
            
            logger.info(f"MAVLink altitude source connected to {self.connection_string}")
            
            # Wait for heartbeat
            self.mavlink_conn.wait_heartbeat(timeout=5)
            logger.info("MAVLink heartbeat received")
            
        except Exception as e:
            logger.error(f"Failed to connect MAVLink altitude source: {e}")
            self.mavlink_conn = None
    
    def get_altitude(self) -> Optional[float]:
        """
        Get altitude from MAVLink GLOBAL_POSITION_INT message
        Returns altitude above ground level (relative_alt field)
        """
        if not self.mavlink_conn:
            return self.last_altitude
        
        try:
            # Try to get GLOBAL_POSITION_INT message (non-blocking)
            msg = self.mavlink_conn.recv_match(
                type='GLOBAL_POSITION_INT',
                blocking=False,
                timeout=0.01
            )
            
            if msg:
                # relative_alt is in millimeters, convert to meters
                altitude_m = msg.relative_alt / 1000.0
                self.last_altitude = altitude_m
                self.last_update_time = time.time()
                return altitude_m
            
            # Return last known altitude if recent
            if time.time() - self.last_update_time < self.timeout:
                return self.last_altitude
            else:
                logger.warning("MAVLink altitude data timeout")
                return None
                
        except Exception as e:
            logger.error(f"Error reading MAVLink altitude: {e}")
            return self.last_altitude
    
    def is_available(self) -> bool:
        """Check if MAVLink connection is active"""
        if not self.mavlink_conn:
            return False
        
        # Check if we've received data recently
        return time.time() - self.last_update_time < self.timeout


class RangefinderAltitudeSource(AltitudeSource):
    """
    Rangefinder altitude source - reads from laser/ultrasonic rangefinder
    Supports common rangefinder protocols (serial output)
    """
    
    def __init__(self, port: str = '/dev/ttyUSB0', baudrate: int = 115200,
                 protocol: str = 'benewake'):
        """
        Initialize rangefinder altitude source
        
        Args:
            port: Serial port for rangefinder
            baudrate: Serial baudrate
            protocol: Rangefinder protocol ('benewake', 'lightware', 'leddarone')
        """
        if not SERIAL_AVAILABLE:
            raise RuntimeError("pyserial required for rangefinder altitude source")
        
        self.port = port
        self.baudrate = baudrate
        self.protocol = protocol
        self.serial_conn = None
        self.last_altitude = None
        self.last_update_time = 0
        self.timeout = 1.0
        
        self._connect()
    
    def _connect(self):
        """Establish serial connection to rangefinder"""
        try:
            self.serial_conn = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1
            )
            logger.info(f"Rangefinder connected on {self.port} ({self.protocol})")
        except Exception as e:
            logger.error(f"Failed to connect rangefinder: {e}")
            self.serial_conn = None
    
    def get_altitude(self) -> Optional[float]:
        """Read altitude from rangefinder"""
        if not self.serial_conn:
            return self.last_altitude
        
        try:
            if self.protocol == 'benewake':
                altitude = self._read_benewake()
            elif self.protocol == 'lightware':
                altitude = self._read_lightware()
            elif self.protocol == 'leddarone':
                altitude = self._read_leddarone()
            else:
                logger.error(f"Unknown rangefinder protocol: {self.protocol}")
                return self.last_altitude
            
            if altitude is not None:
                self.last_altitude = altitude
                self.last_update_time = time.time()
                return altitude
            
            # Return last known altitude if recent
            if time.time() - self.last_update_time < self.timeout:
                return self.last_altitude
            
            return None
            
        except Exception as e:
            logger.error(f"Error reading rangefinder: {e}")
            return self.last_altitude
    
    def _read_benewake(self) -> Optional[float]:
        """Read TF-mini / TFmini Plus rangefinder (Benewake protocol)"""
        if self.serial_conn.in_waiting >= 9:
            data = self.serial_conn.read(9)
            
            # Check header
            if data[0] == 0x59 and data[1] == 0x59:
                # Distance in cm (little endian)
                distance_cm = data[2] + (data[3] << 8)
                return distance_cm / 100.0  # Convert to meters
        
        return None
    
    def _read_lightware(self) -> Optional[float]:
        """Read LightWare rangefinder (ASCII protocol)"""
        if self.serial_conn.in_waiting > 0:
            line = self.serial_conn.readline().decode('ascii').strip()
            try:
                # LightWare outputs distance in meters directly
                distance_m = float(line)
                return distance_m
            except ValueError:
                return None
        
        return None
    
    def _read_leddarone(self) -> Optional[float]:
        """Read LeddarOne rangefinder (Modbus protocol)"""
        # Simplified LeddarOne reading
        # Full implementation would require proper Modbus handling
        if self.serial_conn.in_waiting >= 10:
            data = self.serial_conn.read(10)
            if len(data) >= 10:
                # Distance in cm (big endian at bytes 6-7)
                distance_cm = (data[6] << 8) + data[7]
                return distance_cm / 100.0
        
        return None
    
    def is_available(self) -> bool:
        """Check if rangefinder is active"""
        if not self.serial_conn or not self.serial_conn.is_open:
            return False
        
        return time.time() - self.last_update_time < self.timeout


class BarometerAltitudeSource(AltitudeSource):
    """
    Barometer altitude source - reads from I2C barometer (BMP280, MS5611, etc.)
    Note: Barometer gives altitude MSL, needs takeoff altitude for AGL
    """
    
    def __init__(self, sensor_type: str = 'bmp280', i2c_bus: int = 1):
        """
        Initialize barometer altitude source
        
        Args:
            sensor_type: Barometer type ('bmp280', 'ms5611')
            i2c_bus: I2C bus number
        """
        self.sensor_type = sensor_type
        self.i2c_bus = i2c_bus
        self.sensor = None
        self.takeoff_altitude = None
        self.last_altitude = None
        
        # Try to initialize barometer
        try:
            if sensor_type == 'bmp280':
                self._init_bmp280()
            elif sensor_type == 'ms5611':
                self._init_ms5611()
            else:
                logger.error(f"Unknown barometer type: {sensor_type}")
        except Exception as e:
            logger.error(f"Failed to initialize barometer: {e}")
    
    def _init_bmp280(self):
        """Initialize BMP280 barometer"""
        try:
            import board
            import adafruit_bmp280
            
            i2c = board.I2C()
            self.sensor = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
            self.sensor.sea_level_pressure = 1013.25  # Standard pressure
            logger.info("BMP280 barometer initialized")
        except ImportError:
            logger.error("adafruit_bmp280 library not available")
    
    def _init_ms5611(self):
        """Initialize MS5611 barometer"""
        # MS5611 initialization would go here
        logger.warning("MS5611 support not yet implemented")
    
    def calibrate_takeoff_altitude(self):
        """
        Calibrate takeoff altitude (current barometric altitude)
        Call this when drone is on the ground before takeoff
        """
        if not self.sensor:
            logger.error("Barometer not initialized")
            return
        
        try:
            self.takeoff_altitude = self.sensor.altitude
            logger.info(f"Barometer calibrated, takeoff altitude: {self.takeoff_altitude:.2f}m MSL")
        except Exception as e:
            logger.error(f"Failed to calibrate barometer: {e}")
    
    def get_altitude(self) -> Optional[float]:
        """
        Get altitude AGL from barometer
        Requires calibration before flight
        """
        if not self.sensor:
            return self.last_altitude
        
        if self.takeoff_altitude is None:
            logger.warning("Barometer not calibrated - call calibrate_takeoff_altitude()")
            return None
        
        try:
            current_altitude_msl = self.sensor.altitude
            altitude_agl = current_altitude_msl - self.takeoff_altitude
            self.last_altitude = altitude_agl
            return altitude_agl
        except Exception as e:
            logger.error(f"Error reading barometer: {e}")
            return self.last_altitude
    
    def is_available(self) -> bool:
        """Check if barometer is available and calibrated"""
        return self.sensor is not None and self.takeoff_altitude is not None


class FusedAltitudeSource(AltitudeSource):
    """
    Fused altitude source - combines multiple altitude sources with sensor fusion
    Provides most reliable altitude estimate
    """
    
    def __init__(self, sources: list, weights: Optional[list] = None):
        """
        Initialize fused altitude source
        
        Args:
            sources: List of AltitudeSource objects
            weights: Optional weights for each source (defaults to equal weighting)
        """
        self.sources = sources
        
        if weights is None:
            self.weights = [1.0 / len(sources)] * len(sources)
        else:
            if len(weights) != len(sources):
                raise ValueError("Weights must match number of sources")
            # Normalize weights
            total_weight = sum(weights)
            self.weights = [w / total_weight for w in weights]
        
        self.last_altitude = None
        logger.info(f"Fused altitude source initialized with {len(sources)} sources")
    
    def get_altitude(self) -> Optional[float]:
        """
        Get fused altitude from multiple sources
        Uses weighted average of available sources
        """
        altitudes = []
        active_weights = []
        
        for source, weight in zip(self.sources, self.weights):
            if source.is_available():
                alt = source.get_altitude()
                if alt is not None:
                    altitudes.append(alt)
                    active_weights.append(weight)
        
        if not altitudes:
            logger.warning("No altitude sources available")
            return self.last_altitude
        
        # Normalize active weights
        total_weight = sum(active_weights)
        if total_weight == 0:
            return self.last_altitude
        
        normalized_weights = [w / total_weight for w in active_weights]
        
        # Weighted average
        fused_altitude = sum(alt * w for alt, w in zip(altitudes, normalized_weights))
        self.last_altitude = fused_altitude
        
        return fused_altitude
    
    def is_available(self) -> bool:
        """Check if at least one source is available"""
        return any(source.is_available() for source in self.sources)


def create_altitude_source(config: dict) -> AltitudeSource:
    """
    Factory function to create altitude source from configuration
    
    Args:
        config: Altitude configuration dictionary
    
    Returns:
        Configured AltitudeSource instance
    """
    altitude_type = config.get('type', 'static')
    
    if altitude_type == 'static':
        return StaticAltitudeSource(
            altitude_m=config.get('fixed_altitude', 0.5)
        )
    
    elif altitude_type == 'mavlink':
        return MAVLinkAltitudeSource(
            connection_string=config.get('connection', '/dev/ttyAMA0'),
            baudrate=config.get('baudrate', 115200)
        )
    
    elif altitude_type == 'rangefinder':
        return RangefinderAltitudeSource(
            port=config.get('port', '/dev/ttyUSB0'),
            baudrate=config.get('baudrate', 115200),
            protocol=config.get('protocol', 'benewake')
        )
    
    elif altitude_type == 'barometer':
        return BarometerAltitudeSource(
            sensor_type=config.get('sensor', 'bmp280'),
            i2c_bus=config.get('i2c_bus', 1)
        )
    
    elif altitude_type == 'fused':
        # Create multiple sources and fuse them
        sources = []
        weights = []
        
        for source_config in config.get('sources', []):
            source = create_altitude_source(source_config)
            sources.append(source)
            weights.append(source_config.get('weight', 1.0))
        
        return FusedAltitudeSource(sources, weights)
    
    else:
        logger.warning(f"Unknown altitude type: {altitude_type}, using static")
        return StaticAltitudeSource()


# Example usage and testing
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    print("Altitude Source Module Test")
    print("=" * 50)
    
    # Test static source
    print("\n1. Testing Static Altitude Source:")
    static_source = StaticAltitudeSource(altitude_m=30.0)
    print(f"   Altitude: {static_source.get_altitude()}m")
    print(f"   Available: {static_source.is_available()}")
    
    # Test with dynamic altitude
    print("\n2. Testing Dynamic Altitude:")
    for alt in [10.0, 20.0, 35.0, 50.0]:
        static_source.set_altitude(alt)
        print(f"   Set to {alt}m, reading: {static_source.get_altitude()}m")
    
    print("\n3. Configuration Example:")
    config = {
        'type': 'static',
        'fixed_altitude': 30.0
    }
    source = create_altitude_source(config)
    print(f"   Created source: {type(source).__name__}")
    print(f"   Altitude: {source.get_altitude()}m")
    
    print("\nTest complete!")
