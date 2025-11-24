"""
GPS Emulation Module
Converts optical flow position data to GPS coordinates and sends to flight controller
Flight controller sees Raspberry Pi as a GPS module
"""

import time
import logging
import serial
from typing import Optional, Tuple
from datetime import datetime
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import MAVLink
try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False
    logger.warning("pymavlink not available - MAVLink GPS emulation disabled")


class GPSEmulator:
    """
    Base class for GPS emulation
    Converts local position (meters) to GPS-like data for flight controller
    """
    
    def __init__(self, port: str = '/dev/ttyAMA0', baudrate: int = 115200,
                 home_lat: float = 0.0, home_lon: float = 0.0, home_alt: float = 0.0):
        """
        Initialize GPS emulator
        
        Args:
            port: Serial port for UART communication
            baudrate: Serial baudrate
            home_lat: Home latitude in degrees (takeoff position)
            home_lon: Home longitude in degrees (takeoff position)
            home_alt: Home altitude in meters MSL
        """
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        
        # Home position (origin of local coordinate system)
        self.home_lat = home_lat
        self.home_lon = home_lon
        self.home_alt = home_alt
        
        # Earth radius in meters (for coordinate conversion)
        self.EARTH_RADIUS = 6378137.0
        
        # GPS state
        self.fix_type = 3  # 3D fix
        self.satellites = 12  # Number of satellites
        self.hdop = 1.0  # Horizontal dilution of precision
        self.speed = 0.0  # m/s
        self.course = 0.0  # degrees
        
        # Statistics
        self.messages_sent = 0
        self.last_send_time = time.time()
        
        logger.info(f"GPS Emulator initialized on {port} at {baudrate} baud")
    
    def set_home_position(self, lat: float, lon: float, alt: float):
        """
        Set home position (origin of local coordinate system)
        Call this once at takeoff to establish reference point
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees  
            alt: Altitude in meters MSL
        """
        self.home_lat = lat
        self.home_lon = lon
        self.home_alt = alt
        logger.info(f"Home position set: {lat:.7f}, {lon:.7f}, {alt:.1f}m")
    
    def local_to_gps(self, pos_x: float, pos_y: float, alt_agl: float) -> Tuple[float, float, float]:
        """
        Convert local position (meters from home) to GPS coordinates
        
        Args:
            pos_x: X position in meters (East positive)
            pos_y: Y position in meters (North positive)
            alt_agl: Altitude above ground level in meters
        
        Returns:
            Tuple of (latitude, longitude, altitude_msl) in degrees and meters
        """
        # Convert meters to degrees
        # At equator: 1 degree latitude = 111,320 meters
        # Longitude varies with latitude
        
        lat_offset = pos_y / self.EARTH_RADIUS * (180.0 / math.pi)
        lon_offset = pos_x / (self.EARTH_RADIUS * math.cos(self.home_lat * math.pi / 180.0)) * (180.0 / math.pi)
        
        latitude = self.home_lat + lat_offset
        longitude = self.home_lon + lon_offset
        altitude_msl = self.home_alt + alt_agl
        
        return (latitude, longitude, altitude_msl)
    
    def update_velocity(self, vel_x: float, vel_y: float):
        """
        Update velocity for GPS speed and course calculation
        
        Args:
            vel_x: X velocity in m/s (East positive)
            vel_y: Y velocity in m/s (North positive)
        """
        # Calculate ground speed
        self.speed = math.sqrt(vel_x**2 + vel_y**2)
        
        # Calculate course (0 = North, 90 = East, 180 = South, 270 = West)
        if self.speed > 0.1:  # Only update course if moving
            self.course = math.atan2(vel_x, vel_y) * (180.0 / math.pi)
            if self.course < 0:
                self.course += 360.0
    
    def send_position(self, pos_x: float, pos_y: float, alt_agl: float,
                     vel_x: float = 0.0, vel_y: float = 0.0):
        """
        Send position update to flight controller
        Override in subclasses
        
        Args:
            pos_x: X position in meters
            pos_y: Y position in meters
            alt_agl: Altitude above ground in meters
            vel_x: X velocity in m/s
            vel_y: Y velocity in m/s
        """
        raise NotImplementedError("Subclass must implement send_position()")
    
    def close(self):
        """Close serial connection"""
        if self.serial_conn:
            self.serial_conn.close()
            logger.info("GPS emulator closed")


class NMEAGPSEmulator(GPSEmulator):
    """
    GPS emulator using NMEA protocol
    Sends NMEA sentences that flight controllers recognize as GPS data
    """
    
    def __init__(self, port: str = '/dev/ttyAMA0', baudrate: int = 115200,
                 home_lat: float = 0.0, home_lon: float = 0.0, home_alt: float = 0.0):
        """Initialize NMEA GPS emulator"""
        super().__init__(port, baudrate, home_lat, home_lon, home_alt)
        
        try:
            self.serial_conn = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=0.1
            )
            logger.info(f"NMEA GPS emulator serial port opened: {port}")
        except Exception as e:
            logger.error(f"Failed to open serial port: {e}")
            self.serial_conn = None
    
    def _calculate_checksum(self, sentence: str) -> str:
        """Calculate NMEA checksum"""
        checksum = 0
        for char in sentence:
            checksum ^= ord(char)
        return f"{checksum:02X}"
    
    def _create_nmea_sentence(self, sentence: str) -> str:
        """Create complete NMEA sentence with checksum"""
        checksum = self._calculate_checksum(sentence)
        return f"${sentence}*{checksum}\r\n"
    
    def send_position(self, pos_x: float, pos_y: float, alt_agl: float,
                     vel_x: float = 0.0, vel_y: float = 0.0):
        """
        Send NMEA GPS sentences to flight controller
        Sends GPGGA (position) and GPRMC (recommended minimum) messages
        """
        if not self.serial_conn or not self.serial_conn.is_open:
            return
        
        # Convert local position to GPS coordinates
        lat, lon, alt_msl = self.local_to_gps(pos_x, pos_y, alt_agl)
        
        # Update velocity
        self.update_velocity(vel_x, vel_y)
        
        # Get current UTC time
        now = datetime.utcnow()
        time_str = now.strftime("%H%M%S.%f")[:-4]  # HHMMSS.SS
        date_str = now.strftime("%d%m%y")  # DDMMYY
        
        # Convert lat/lon to NMEA format (DDMM.MMMM)
        lat_deg = int(abs(lat))
        lat_min = (abs(lat) - lat_deg) * 60.0
        lat_dir = 'N' if lat >= 0 else 'S'
        lat_nmea = f"{lat_deg:02d}{lat_min:07.4f}"
        
        lon_deg = int(abs(lon))
        lon_min = (abs(lon) - lon_deg) * 60.0
        lon_dir = 'E' if lon >= 0 else 'W'
        lon_nmea = f"{lon_deg:03d}{lon_min:07.4f}"
        
        # GPGGA - Global Positioning System Fix Data
        gpgga = (
            f"GPGGA,{time_str},{lat_nmea},{lat_dir},{lon_nmea},{lon_dir},"
            f"{self.fix_type},{self.satellites:02d},{self.hdop:.1f},"
            f"{alt_msl:.1f},M,0.0,M,,"
        )
        
        # GPRMC - Recommended Minimum Specific GPS/Transit Data
        speed_knots = self.speed * 1.94384  # m/s to knots
        gprmc = (
            f"GPRMC,{time_str},A,{lat_nmea},{lat_dir},{lon_nmea},{lon_dir},"
            f"{speed_knots:.2f},{self.course:.2f},{date_str},,,A"
        )
        
        # Send sentences
        try:
            self.serial_conn.write(self._create_nmea_sentence(gpgga).encode('ascii'))
            self.serial_conn.write(self._create_nmea_sentence(gprmc).encode('ascii'))
            self.messages_sent += 1
            
            # Log periodically
            if self.messages_sent % 50 == 0:
                logger.debug(
                    f"GPS Emulation: {lat:.7f},{lon:.7f} Alt:{alt_msl:.1f}m "
                    f"Spd:{self.speed:.2f}m/s Course:{self.course:.0f}°"
                )
                
        except Exception as e:
            logger.error(f"Failed to send NMEA sentences: {e}")


class MAVLinkGPSEmulator(GPSEmulator):
    """
    GPS emulator using MAVLink protocol
    Sends GPS_INPUT or GPS_RAW_INT messages
    """
    
    def __init__(self, port: str = '/dev/ttyAMA0', baudrate: int = 115200,
                 home_lat: float = 0.0, home_lon: float = 0.0, home_alt: float = 0.0):
        """Initialize MAVLink GPS emulator"""
        super().__init__(port, baudrate, home_lat, home_lon, home_alt)
        
        if not MAVLINK_AVAILABLE:
            logger.error("pymavlink not available - cannot use MAVLink GPS emulation")
            return
        
        try:
            self.mavlink_conn = mavutil.mavlink_connection(
                port,
                baud=baudrate,
                source_system=1,
                source_component=220  # GPS component ID
            )
            logger.info(f"MAVLink GPS emulator initialized on {port}")
        except Exception as e:
            logger.error(f"Failed to initialize MAVLink connection: {e}")
            self.mavlink_conn = None
    
    def send_position(self, pos_x: float, pos_y: float, alt_agl: float,
                     vel_x: float = 0.0, vel_y: float = 0.0):
        """
        Send MAVLink GPS_INPUT message to flight controller
        """
        if not self.mavlink_conn:
            return
        
        # Convert local position to GPS coordinates
        lat, lon, alt_msl = self.local_to_gps(pos_x, pos_y, alt_agl)
        
        # Update velocity
        self.update_velocity(vel_x, vel_y)
        
        # Convert to MAVLink units
        lat_int = int(lat * 1e7)  # degrees * 1e7
        lon_int = int(lon * 1e7)  # degrees * 1e7
        alt_int = int(alt_msl * 1000)  # meters to millimeters
        
        # Velocity in cm/s
        vn = int(vel_y * 100)  # North velocity
        ve = int(vel_x * 100)  # East velocity
        vd = 0  # Down velocity (we don't have this from optical flow)
        
        # Speed and course
        speed_ms = int(self.speed * 100)  # m/s to cm/s
        
        # Accuracy estimates (optical flow is pretty accurate locally)
        horiz_acc = 50  # cm (0.5m accuracy)
        vert_acc = 100  # cm (1.0m accuracy)
        speed_acc = 30  # cm/s
        
        try:
            # Send GPS_INPUT message
            self.mavlink_conn.mav.gps_input_send(
                int(time.time() * 1e6),  # Timestamp (microseconds)
                0,  # GPS ID
                0 |  # ignore flags (0 = use all fields)
                1 << 0 |  # GPS fix valid
                1 << 1 |  # GPS latitude valid
                1 << 2 |  # GPS longitude valid  
                1 << 3 |  # GPS altitude valid
                1 << 4 |  # GPS horizontal accuracy valid
                1 << 5 |  # GPS vertical accuracy valid
                1 << 6 |  # GPS velocity valid
                1 << 7,   # GPS speed accuracy valid
                3,  # Fix type: 3D fix
                lat_int,
                lon_int,
                alt_int,
                0.5,  # HDOP
                0.5,  # VDOP
                vn,
                ve,
                vd,
                speed_ms,
                horiz_acc,
                vert_acc,
                speed_acc,
                self.satellites
            )
            
            self.messages_sent += 1
            
            # Log periodically
            if self.messages_sent % 50 == 0:
                logger.debug(
                    f"MAVLink GPS: {lat:.7f},{lon:.7f} Alt:{alt_msl:.1f}m "
                    f"Spd:{self.speed:.2f}m/s Sats:{self.satellites}"
                )
                
        except Exception as e:
            logger.error(f"Failed to send MAVLink GPS message: {e}")
    
    def close(self):
        """Close MAVLink connection"""
        if self.mavlink_conn:
            self.mavlink_conn.close()
        super().close()


def create_gps_emulator(config: dict) -> Optional[GPSEmulator]:
    """
    Factory function to create GPS emulator from configuration
    
    Args:
        config: GPS emulation configuration dictionary
    
    Returns:
        GPSEmulator instance or None if disabled
    """
    if not config.get('enabled', False):
        return None
    
    protocol = config.get('protocol', 'nmea').lower()
    port = config.get('port', '/dev/ttyAMA0')
    baudrate = config.get('baudrate', 115200)
    
    # Home position (can be updated later)
    home_lat = config.get('home_lat', 0.0)
    home_lon = config.get('home_lon', 0.0)
    home_alt = config.get('home_alt', 0.0)
    
    try:
        if protocol == 'nmea':
            emulator = NMEAGPSEmulator(port, baudrate, home_lat, home_lon, home_alt)
            logger.info("Created NMEA GPS emulator")
            return emulator
        elif protocol == 'mavlink':
            emulator = MAVLinkGPSEmulator(port, baudrate, home_lat, home_lon, home_alt)
            logger.info("Created MAVLink GPS emulator")
            return emulator
        else:
            logger.error(f"Unknown GPS emulation protocol: {protocol}")
            return None
    except Exception as e:
        logger.error(f"Failed to create GPS emulator: {e}")
        return None


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    print("GPS Emulation Test")
    print("=" * 50)
    
    # Test NMEA emulator
    print("\n1. Testing NMEA GPS Emulator:")
    print("   (Note: Requires serial port, may fail in test)")
    
    try:
        nmea_config = {
            'enabled': True,
            'protocol': 'nmea',
            'port': '/dev/ttyAMA0',
            'baudrate': 115200,
            'home_lat': 37.7749,  # San Francisco example
            'home_lon': -122.4194,
            'home_alt': 10.0
        }
        
        emulator = create_gps_emulator(nmea_config)
        
        if emulator:
            # Simulate movement
            print("\n   Simulating drone movement:")
            for i in range(5):
                pos_x = i * 1.0  # Move 1m east each second
                pos_y = i * 0.5  # Move 0.5m north each second
                alt = 15.0 + i * 0.2  # Climb slowly
                
                emulator.send_position(pos_x, pos_y, alt, 1.0, 0.5)
                print(f"   Sent position: X={pos_x:.1f}m Y={pos_y:.1f}m Alt={alt:.1f}m")
                time.sleep(1)
            
            emulator.close()
            print("\n   Test complete!")
        else:
            print("   Could not create emulator (expected if no serial port)")
            
    except Exception as e:
        print(f"   Test failed: {e}")
    
    print("\n2. Coordinate Conversion Test:")
    emulator = GPSEmulator(
        port='/dev/null',  # Dummy port
        home_lat=37.7749,
        home_lon=-122.4194,
        home_alt=10.0
    )
    
    test_positions = [
        (0.0, 0.0, 0.0, "Home position"),
        (10.0, 0.0, 0.0, "10m East"),
        (0.0, 10.0, 0.0, "10m North"),
        (10.0, 10.0, 0.0, "10m Northeast"),
        (0.0, 0.0, 50.0, "50m altitude")
    ]
    
    for pos_x, pos_y, alt, desc in test_positions:
        lat, lon, alt_msl = emulator.local_to_gps(pos_x, pos_y, alt)
        print(f"   {desc:20s}: {lat:.7f}°, {lon:.7f}°, {alt_msl:.1f}m")
    
    print("\nAll tests complete!")
