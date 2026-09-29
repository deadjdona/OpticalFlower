"""
Virtual GPS Module for Flight Controller Integration
Converts optical flow position to GPS-like data that flight controller can use
"""

import time
import math
import logging
from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import MAVLink
try:
    from pymavlink import mavutil
    MAVLINK_AVAILABLE = True
except ImportError:
    MAVLINK_AVAILABLE = False
    logger.warning("pymavlink not available - Virtual GPS disabled")


class VirtualGPS:
    """
    Converts optical flow position to GPS coordinates for flight controller
    Makes FC think it has GPS when actually using visual odometry
    """
    
    def __init__(self, 
                 connection_string: str = '/dev/ttyAMA0',
                 baudrate: int = 115200,
                 origin_lat: float = 0.0,
                 origin_lon: float = 0.0,
                 origin_alt: float = 0.0):
        """
        Initialize virtual GPS
        
        Args:
            connection_string: MAVLink connection to flight controller
            baudrate: Serial baudrate
            origin_lat: Origin latitude in degrees (can be arbitrary)
            origin_lon: Origin longitude in degrees (can be arbitrary)
            origin_alt: Origin altitude in meters
        """
        if not MAVLINK_AVAILABLE:
            raise RuntimeError("pymavlink required for Virtual GPS")
        
        self.connection_string = connection_string
        self.baudrate = baudrate
        
        # GPS origin (arbitrary starting point)
        self.origin_lat = origin_lat if origin_lat != 0 else 47.3977  # Default: somewhere in Europe
        self.origin_lon = origin_lon if origin_lon != 0 else 8.5456
        self.origin_alt = origin_alt
        
        # Conversion factors
        self.meters_per_degree_lat = 111320.0  # meters per degree latitude
        self.meters_per_degree_lon = None  # Calculated based on latitude
        self._calculate_lon_conversion()
        
        # MAVLink connection
        self.mavlink_conn = None
        self.system_id = 1  # Flight controller system ID
        self.component_id = 220  # GPS component ID (MAV_COMP_ID_GPS)
        
        # GPS parameters
        self.fix_type = 3  # 3D fix
        self.satellites_visible = 10  # Simulated satellite count
        self.hdop = 100  # HDOP in cm (1.0m)
        self.vdop = 100  # VDOP in cm
        
        # Position tracking
        self.last_send_time = 0
        self.send_rate_hz = 5  # GPS update rate (5 Hz typical)
        
        # Status
        self.enabled = False
        
        self._connect()
    
    def _calculate_lon_conversion(self):
        """Calculate meters per degree longitude at current latitude"""
        lat_rad = math.radians(self.origin_lat)
        self.meters_per_degree_lon = 111320.0 * math.cos(lat_rad)
    
    def _connect(self):
        """Establish MAVLink connection to flight controller"""
        try:
            if self.connection_string.startswith('/dev/'):
                # Serial connection
                self.mavlink_conn = mavutil.mavlink_connection(
                    self.connection_string,
                    baud=self.baudrate,
                    source_system=255,  # GCS/companion computer
                    source_component=mavutil.mavlink.MAV_COMP_ID_VISUAL_INERTIAL_ODOMETRY
                )
            else:
                # UDP or other connection
                self.mavlink_conn = mavutil.mavlink_connection(
                    self.connection_string,
                    source_system=255
                )
            
            logger.info(f"Virtual GPS connected to {self.connection_string}")
            
            # Wait for heartbeat
            logger.info("Waiting for flight controller heartbeat...")
            msg = self.mavlink_conn.wait_heartbeat(timeout=10)
            if msg:
                self.system_id = msg.get_srcSystem()
                logger.info(f"Connected to FC (system_id: {self.system_id})")
                self.enabled = True
            else:
                logger.error("No heartbeat received from flight controller")
                
        except Exception as e:
            logger.error(f"Failed to connect Virtual GPS: {e}")
            self.mavlink_conn = None
    
    def position_to_gps(self, 
                       x_meters: float, 
                       y_meters: float, 
                       z_meters: float) -> Tuple[float, float, float]:
        """
        Convert local position (meters) to GPS coordinates
        
        Args:
            x_meters: X position in meters (East)
            y_meters: Y position in meters (North)
            z_meters: Z altitude in meters (Up)
        
        Returns:
            Tuple of (latitude, longitude, altitude) in degrees and meters
        """
        # Convert meters to degrees
        lat_offset = y_meters / self.meters_per_degree_lat
        lon_offset = x_meters / self.meters_per_degree_lon
        
        # Add to origin
        latitude = self.origin_lat + lat_offset
        longitude = self.origin_lon + lon_offset
        altitude = self.origin_alt + z_meters
        
        return (latitude, longitude, altitude)
    
    def send_gps_input(self,
                      pos_x: float,
                      pos_y: float,
                      altitude: float,
                      vel_x: float = 0.0,
                      vel_y: float = 0.0,
                      vel_z: float = 0.0):
        """
        Send GPS_INPUT message to flight controller
        
        Args:
            pos_x: X position in meters (visual frame)
            pos_y: Y position in meters (visual frame)
            altitude: Altitude in meters
            vel_x: X velocity in m/s
            vel_y: Y velocity in m/s
            vel_z: Z velocity in m/s (positive = up)
        """
        if not self.enabled or not self.mavlink_conn:
            return
        
        # Rate limiting
        current_time = time.time()
        if current_time - self.last_send_time < 1.0 / self.send_rate_hz:
            return
        
        # Convert visual position to GPS coordinates
        lat, lon, alt = self.position_to_gps(pos_x, pos_y, altitude)
        
        # Convert to GPS_INPUT format
        lat_int = int(lat * 1e7)  # degrees * 10^7
        lon_int = int(lon * 1e7)
        alt_int = int(alt * 1000.0)  # meters to millimeters
        
        # Velocity in cm/s
        vel_north = int(vel_y * 100.0)  # m/s to cm/s
        vel_east = int(vel_x * 100.0)
        vel_down = int(-vel_z * 100.0)  # NED frame (down is positive)
        
        # Speed over ground
        speed_ms = math.sqrt(vel_x**2 + vel_y**2)
        
        # Course over ground (heading of movement)
        if speed_ms > 0.1:
            cog = math.degrees(math.atan2(vel_east, vel_north))
            if cog < 0:
                cog += 360.0
        else:
            cog = 0.0
        
        try:
            # Send GPS_INPUT message
            self.mavlink_conn.mav.gps_input_send(
                int(current_time * 1e6),  # time_usec (microseconds)
                0,  # gps_id (0 = first GPS)
                0 |  # ignore_flags (0 = use all fields)
                (0 << 0) |  # Use lat/lon
                (0 << 1) |  # Use altitude
                (0 << 2) |  # Use horizontal accuracy
                (0 << 3) |  # Use vertical accuracy
                (0 << 4) |  # Use velocity
                (0 << 5),   # Use speed accuracy
                lat_int,
                lon_int,
                alt_int,  # Altitude MSL
                self.hdop,  # HDOP in cm
                self.vdop,  # VDOP in cm
                vel_north,
                vel_east,
                vel_down,
                100,  # Speed accuracy in cm/s
                100,  # Horizontal accuracy in mm
                100,  # Vertical accuracy in mm
                self.satellites_visible,
                self.fix_type,  # 3D fix
                0  # yaw in degrees * 100 (not used)
            )
            
            self.last_send_time = current_time
            
            logger.debug(
                f"Sent GPS: lat={lat:.7f}, lon={lon:.7f}, alt={alt:.2f}, "
                f"vel=[{vel_x:.2f}, {vel_y:.2f}, {vel_z:.2f}]"
            )
            
        except Exception as e:
            logger.error(f"Failed to send GPS_INPUT: {e}")
    
    def send_vision_position_estimate(self,
                                     pos_x: float,
                                     pos_y: float,
                                     pos_z: float,
                                     roll: float = 0.0,
                                     pitch: float = 0.0,
                                     yaw: float = 0.0):
        """
        Send VISION_POSITION_ESTIMATE message (alternative to GPS_INPUT)
        Some flight controllers prefer this for visual odometry
        
        Args:
            pos_x: X position in meters
            pos_y: Y position in meters
            pos_z: Z position in meters
            roll: Roll angle in radians
            pitch: Pitch angle in radians
            yaw: Yaw angle in radians
        """
        if not self.enabled or not self.mavlink_conn:
            return
        
        try:
            current_time = time.time()
            usec = int(current_time * 1e6)
            
            self.mavlink_conn.mav.vision_position_estimate_send(
                usec,      # timestamp (microseconds)
                pos_x,     # x position (meters)
                pos_y,     # y position (meters)
                pos_z,     # z position (meters)
                roll,      # roll angle (rad)
                pitch,     # pitch angle (rad)
                yaw,       # yaw angle (rad)
                None,      # covariance (optional)
                0          # reset counter
            )
            
            logger.debug(f"Sent VISION_POSITION: [{pos_x:.3f}, {pos_y:.3f}, {pos_z:.3f}]")
            
        except Exception as e:
            logger.error(f"Failed to send VISION_POSITION_ESTIMATE: {e}")
    
    def send_global_vision_position_estimate(self,
                                            pos_x: float,
                                            pos_y: float,
                                            altitude: float,
                                            vel_x: float = 0.0,
                                            vel_y: float = 0.0,
                                            vel_z: float = 0.0):
        """
        Send GLOBAL_VISION_POSITION_ESTIMATE message
        Provides global position from visual odometry
        
        Args:
            pos_x: X position in meters
            pos_y: Y position in meters
            altitude: Altitude in meters
            vel_x: X velocity in m/s
            vel_y: Y velocity in m/s
            vel_z: Z velocity in m/s
        """
        if not self.enabled or not self.mavlink_conn:
            return
        
        # Rate limiting
        current_time = time.time()
        if current_time - self.last_send_time < 1.0 / self.send_rate_hz:
            return
        
        # Convert to GPS coordinates
        lat, lon, alt = self.position_to_gps(pos_x, pos_y, altitude)
        
        try:
            usec = int(current_time * 1e6)
            
            self.mavlink_conn.mav.global_vision_position_estimate_send(
                usec,      # timestamp
                pos_x,     # local x (meters)
                pos_y,     # local y (meters)
                altitude,  # local z (meters)
                roll=0.0,  # roll (rad)
                pitch=0.0, # pitch (rad)
                yaw=0.0    # yaw (rad)
            )
            
            self.last_send_time = current_time
            
        except Exception as e:
            logger.error(f"Failed to send GLOBAL_VISION_POSITION_ESTIMATE: {e}")
    
    def set_origin(self, lat: float, lon: float, alt: float = 0.0):
        """
        Set GPS origin (home position)
        
        Args:
            lat: Latitude in degrees
            lon: Longitude in degrees
            alt: Altitude in meters
        """
        self.origin_lat = lat
        self.origin_lon = lon
        self.origin_alt = alt
        self._calculate_lon_conversion()
        logger.info(f"GPS origin set to: lat={lat:.7f}, lon={lon:.7f}, alt={alt:.1f}m")
    
    def set_gps_quality(self, satellites: int = 10, hdop: float = 1.0):
        """
        Set simulated GPS quality parameters
        
        Args:
            satellites: Number of visible satellites (default 10)
            hdop: Horizontal dilution of precision in meters (default 1.0)
        """
        self.satellites_visible = satellites
        self.hdop = int(hdop * 100)  # Convert to cm
        self.vdop = int(hdop * 100)
    
    def is_connected(self) -> bool:
        """Check if connected to flight controller"""
        return self.enabled and self.mavlink_conn is not None
    
    def close(self):
        """Close MAVLink connection"""
        if self.mavlink_conn:
            self.mavlink_conn.close()
            self.enabled = False
            logger.info("Virtual GPS closed")


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    print("Virtual GPS Module Test")
    print("=" * 50)
    
    # Create virtual GPS
    try:
        vgps = VirtualGPS(
            connection_string='/dev/ttyAMA0',
            baudrate=115200,
            origin_lat=47.3977,  # Example coordinates
            origin_lon=8.5456,
            origin_alt=400.0
        )
        
        if vgps.is_connected():
            print("✓ Connected to flight controller")
            print(f"  System ID: {vgps.system_id}")
            print(f"  Origin: lat={vgps.origin_lat:.6f}, lon={vgps.origin_lon:.6f}")
            
            # Test position conversion
            print("\nTesting position conversions:")
            test_positions = [
                (0, 0, 0),      # Origin
                (10, 0, 0),     # 10m East
                (0, 10, 0),     # 10m North
                (10, 10, 5),    # 10m NE, 5m up
            ]
            
            for x, y, z in test_positions:
                lat, lon, alt = vgps.position_to_gps(x, y, z)
                print(f"  Pos({x:3.0f}, {y:3.0f}, {z:3.0f}) -> "
                      f"GPS({lat:.7f}, {lon:.7f}, {alt:.1f}m)")
            
            # Send test data
            print("\nSending test GPS data (5 seconds)...")
            start_time = time.time()
            
            while time.time() - start_time < 5.0:
                # Simulate circular motion
                t = time.time() - start_time
                x = 5.0 * math.sin(t)
                y = 5.0 * math.cos(t)
                z = 2.0
                
                vx = 5.0 * math.cos(t)
                vy = -5.0 * math.sin(t)
                vz = 0.0
                
                vgps.send_gps_input(x, y, z, vx, vy, vz)
                time.sleep(0.2)  # 5 Hz
            
            print("✓ Test complete!")
            vgps.close()
            
        else:
            print("✗ Failed to connect to flight controller")
            print("  Check:")
            print("  - Serial connection (/dev/ttyAMA0)")
            print("  - Flight controller powered on")
            print("  - Correct baudrate (115200)")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
