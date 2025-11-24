"""
Caddx Infra 256CA with AI Box Support
Enhanced optical flow sensor with AI-powered tracking and object detection
Supports both I2C and UART communication for AI features
"""

import time
import logging
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass
from enum import IntEnum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import I2C library
try:
    import smbus2 as smbus
    I2C_AVAILABLE = True
except ImportError:
    try:
        import smbus
        I2C_AVAILABLE = True
    except ImportError:
        I2C_AVAILABLE = False
        logger.warning("smbus/smbus2 not available - Caddx Infra 256CA AI Box disabled")

# Try to import serial for UART communication
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logger.warning("pyserial not available - AI Box UART features disabled")


class AIBoxMode(IntEnum):
    """AI Box operating modes"""
    OPTICAL_FLOW_ONLY = 0
    TRACKING_ASSIST = 1
    OBJECT_DETECTION = 2
    STABILIZATION_ENHANCED = 3
    AUTO_MODE = 4


class TrackingTarget(IntEnum):
    """Target types for AI tracking"""
    NONE = 0
    PERSON = 1
    VEHICLE = 2
    CUSTOM_OBJECT = 3
    LANDING_PAD = 4
    GROUND_TEXTURE = 5


@dataclass
class AIBoxStatus:
    """AI Box status information"""
    mode: AIBoxMode
    tracking_active: bool
    target_detected: bool
    target_type: TrackingTarget
    target_confidence: float
    target_x: int
    target_y: int
    processing_fps: int
    optical_flow_quality: int


@dataclass
class AIBoxConfig:
    """AI Box configuration"""
    mode: AIBoxMode = AIBoxMode.AUTO_MODE
    tracking_target: TrackingTarget = TrackingTarget.GROUND_TEXTURE
    roi_enabled: bool = True
    roi_x: int = 160  # Center of 320x320 sensor
    roi_y: int = 160
    roi_width: int = 160
    roi_height: int = 160
    detection_threshold: float = 0.6
    stabilization_strength: float = 0.5
    update_rate_hz: int = 50


class CaddxInfra256AIBox:
    """
    Driver for Caddx Infra 256CA with AI Box
    Enhanced optical flow sensor with AI-powered features
    """
    
    # I2C address (same as standard version)
    DEFAULT_I2C_ADDRESS = 0x29
    
    # Standard optical flow registers (compatible with base version)
    REG_PRODUCT_ID = 0x00
    REG_REVISION_ID = 0x01
    REG_MOTION = 0x02
    REG_DELTA_X_L = 0x03
    REG_DELTA_X_H = 0x04
    REG_DELTA_Y_L = 0x05
    REG_DELTA_Y_H = 0x06
    REG_SQUAL = 0x07
    REG_SHUTTER_UPPER = 0x08
    REG_SHUTTER_LOWER = 0x09
    REG_PIX_MAX = 0x0A
    REG_PIX_AVG = 0x0B
    REG_PIX_MIN = 0x0C
    REG_CONFIG = 0x10
    REG_RESOLUTION = 0x11
    REG_POWER_MODE = 0x12
    
    # AI Box specific registers (extended register map)
    REG_AI_MODE = 0x20
    REG_AI_STATUS = 0x21
    REG_AI_TARGET_TYPE = 0x22
    REG_AI_TARGET_X_L = 0x23
    REG_AI_TARGET_X_H = 0x24
    REG_AI_TARGET_Y_L = 0x25
    REG_AI_TARGET_Y_H = 0x26
    REG_AI_CONFIDENCE = 0x27
    REG_AI_FPS = 0x28
    REG_AI_ROI_X_L = 0x29
    REG_AI_ROI_X_H = 0x2A
    REG_AI_ROI_Y_L = 0x2B
    REG_AI_ROI_Y_H = 0x2C
    REG_AI_ROI_W_L = 0x2D
    REG_AI_ROI_W_H = 0x2E
    REG_AI_ROI_H_L = 0x2F
    REG_AI_ROI_H_H = 0x30
    REG_AI_THRESHOLD = 0x31
    REG_AI_STABILIZATION = 0x32
    REG_AI_ENABLE = 0x33
    
    # Product IDs
    PRODUCT_ID_STANDARD = 0x49
    PRODUCT_ID_AI_BOX = 0x4A
    
    def __init__(self, 
                 bus_number: int = 1,
                 i2c_address: int = DEFAULT_I2C_ADDRESS,
                 uart_port: Optional[str] = None,
                 rotation: int = 0,
                 ai_config: Optional[AIBoxConfig] = None):
        """
        Initialize Caddx Infra 256CA with AI Box
        
        Args:
            bus_number: I2C bus number (1 for Raspberry Pi)
            i2c_address: I2C address (default 0x29)
            uart_port: Optional UART port for AI features (/dev/ttyAMA0)
            rotation: Sensor rotation in degrees (0, 90, 180, 270)
            ai_config: AI Box configuration
        """
        if not I2C_AVAILABLE:
            raise RuntimeError("smbus or smbus2 library required for Caddx Infra 256CA")
        
        self.bus_number = bus_number
        self.i2c_address = i2c_address
        self.rotation = rotation
        self.uart_port = uart_port
        self.serial_conn = None
        
        # AI Box configuration
        self.ai_config = ai_config or AIBoxConfig()
        self.ai_box_available = False
        
        # Enhanced tracking data
        self.ai_delta_x = 0
        self.ai_delta_y = 0
        self.last_ai_update = time.time()
        
        # Initialize I2C bus
        self.bus = smbus.SMBus(bus_number)
        
        # Initialize sensor
        self._reset()
        self._init_sensor()
        
        # Detect AI Box capability
        self._detect_ai_box()
        
        # Initialize UART if available and AI Box detected
        if self.ai_box_available and uart_port and SERIAL_AVAILABLE:
            self._init_uart()
        
        # Configure AI Box if available
        if self.ai_box_available:
            self._configure_ai_box()
        
        logger.info(f"Caddx Infra 256CA initialized (AI Box: {self.ai_box_available})")
    
    def _read_register(self, register: int) -> int:
        """Read a single byte from register"""
        try:
            value = self.bus.read_byte_data(self.i2c_address, register)
            return value
        except Exception as e:
            logger.error(f"Failed to read register 0x{register:02X}: {e}")
            return 0
    
    def _write_register(self, register: int, value: int):
        """Write a single byte to register"""
        try:
            self.bus.write_byte_data(self.i2c_address, register, value)
            time.sleep(0.001)
        except Exception as e:
            logger.error(f"Failed to write register 0x{register:02X}: {e}")
    
    def _read_word(self, register_low: int) -> int:
        """Read 16-bit word (low byte, then high byte)"""
        try:
            low = self._read_register(register_low)
            high = self._read_register(register_low + 1)
            return (high << 8) | low
        except Exception as e:
            logger.error(f"Failed to read word at 0x{register_low:02X}: {e}")
            return 0
    
    def _write_word(self, register_low: int, value: int):
        """Write 16-bit word (low byte, then high byte)"""
        low = value & 0xFF
        high = (value >> 8) & 0xFF
        self._write_register(register_low, low)
        self._write_register(register_low + 1, high)
    
    def _reset(self):
        """Perform soft reset of sensor"""
        try:
            self._write_register(self.REG_POWER_MODE, 0x5A)
            time.sleep(0.05)
            logger.info("Sensor reset complete")
        except Exception as e:
            logger.warning(f"Reset failed: {e}")
    
    def _init_sensor(self):
        """Initialize sensor with optimal settings"""
        try:
            # High resolution mode
            self._write_register(self.REG_RESOLUTION, 0x00)
            
            # Normal power mode
            self._write_register(self.REG_POWER_MODE, 0x00)
            
            # Enable motion detection
            self._write_register(self.REG_CONFIG, 0x01)
            
            time.sleep(0.02)
            logger.info("Sensor configuration complete")
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
    
    def _detect_ai_box(self):
        """Detect if AI Box is present"""
        try:
            product_id = self._read_register(self.REG_PRODUCT_ID)
            
            # Check for AI Box product ID
            if product_id == self.PRODUCT_ID_AI_BOX:
                self.ai_box_available = True
                logger.info("AI Box detected!")
                
                # Try to read AI status register to confirm
                ai_status = self._read_register(self.REG_AI_STATUS)
                logger.info(f"AI Box status: 0x{ai_status:02X}")
            else:
                logger.info(f"Standard sensor detected (Product ID: 0x{product_id:02X})")
                self.ai_box_available = False
                
        except Exception as e:
            logger.warning(f"Could not detect AI Box: {e}")
            self.ai_box_available = False
    
    def _init_uart(self):
        """Initialize UART communication for AI Box"""
        try:
            self.serial_conn = serial.Serial(
                port=self.uart_port,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1
            )
            logger.info(f"UART initialized on {self.uart_port}")
        except Exception as e:
            logger.error(f"Failed to initialize UART: {e}")
            self.serial_conn = None
    
    def _configure_ai_box(self):
        """Configure AI Box with user settings"""
        try:
            # Enable AI Box
            self._write_register(self.REG_AI_ENABLE, 0x01)
            
            # Set AI mode
            self._write_register(self.REG_AI_MODE, int(self.ai_config.mode))
            
            # Set target type
            self._write_register(self.REG_AI_TARGET_TYPE, int(self.ai_config.tracking_target))
            
            # Configure ROI
            if self.ai_config.roi_enabled:
                self._write_word(self.REG_AI_ROI_X_L, self.ai_config.roi_x)
                self._write_word(self.REG_AI_ROI_Y_L, self.ai_config.roi_y)
                self._write_word(self.REG_AI_ROI_W_L, self.ai_config.roi_width)
                self._write_word(self.REG_AI_ROI_H_L, self.ai_config.roi_height)
            
            # Set detection threshold (0-255 scale)
            threshold_byte = int(self.ai_config.detection_threshold * 255)
            self._write_register(self.REG_AI_THRESHOLD, threshold_byte)
            
            # Set stabilization strength (0-255 scale)
            stab_byte = int(self.ai_config.stabilization_strength * 255)
            self._write_register(self.REG_AI_STABILIZATION, stab_byte)
            
            time.sleep(0.05)
            logger.info("AI Box configured successfully")
            
        except Exception as e:
            logger.error(f"AI Box configuration failed: {e}")
    
    def get_motion(self) -> Tuple[int, int]:
        """
        Read motion data with AI enhancement
        
        Returns:
            Tuple of (delta_x, delta_y) in sensor units
        """
        try:
            # Check if motion data is available
            motion = self._read_register(self.REG_MOTION)
            
            if not (motion & 0x80):
                return (0, 0)
            
            # Read standard delta values
            delta_x = self._read_word(self.REG_DELTA_X_L)
            delta_y = self._read_word(self.REG_DELTA_Y_L)
            
            # Convert to signed 16-bit
            delta_x = self._to_signed_16bit(delta_x)
            delta_y = self._to_signed_16bit(delta_y)
            
            # Apply AI enhancement if available
            if self.ai_box_available:
                delta_x, delta_y = self._apply_ai_enhancement(delta_x, delta_y)
            
            # Apply rotation correction
            delta_x, delta_y = self._apply_rotation(delta_x, delta_y)
            
            return (delta_x, delta_y)
            
        except Exception as e:
            logger.error(f"Failed to read motion: {e}")
            return (0, 0)
    
    def _apply_ai_enhancement(self, x: int, y: int) -> Tuple[int, int]:
        """
        Apply AI-based motion enhancement
        Uses AI Box for improved tracking and noise reduction
        """
        try:
            # Get AI status
            ai_status = self._read_register(self.REG_AI_STATUS)
            
            # Check if AI tracking is active (bit 0)
            if ai_status & 0x01:
                # Get AI-enhanced deltas from target tracking
                target_dx = self._read_word(self.REG_AI_TARGET_X_L)
                target_dy = self._read_word(self.REG_AI_TARGET_Y_L)
                
                target_dx = self._to_signed_16bit(target_dx)
                target_dy = self._to_signed_16bit(target_dy)
                
                # Get confidence
                confidence = self._read_register(self.REG_AI_CONFIDENCE) / 255.0
                
                # Blend AI tracking with raw optical flow based on confidence
                if confidence > 0.5:
                    blend_factor = min(confidence, 0.8)
                    x = int(x * (1 - blend_factor) + target_dx * blend_factor)
                    y = int(y * (1 - blend_factor) + target_dy * blend_factor)
                    
                    self.ai_delta_x = target_dx
                    self.ai_delta_y = target_dy
            
            return (x, y)
            
        except Exception as e:
            logger.debug(f"AI enhancement failed: {e}")
            return (x, y)
    
    def _to_signed_16bit(self, value: int) -> int:
        """Convert unsigned 16-bit to signed"""
        if value > 32767:
            return value - 65536
        return value
    
    def _apply_rotation(self, x: int, y: int) -> Tuple[int, int]:
        """Apply rotation correction based on sensor orientation"""
        if self.rotation == 0:
            return (x, y)
        elif self.rotation == 90:
            return (y, -x)
        elif self.rotation == 180:
            return (-x, -y)
        elif self.rotation == 270:
            return (-y, x)
        return (x, y)
    
    def get_surface_quality(self) -> int:
        """Get surface quality (0-255)"""
        try:
            squal = self._read_register(self.REG_SQUAL)
            
            # If AI Box is active, blend with AI quality metric
            if self.ai_box_available:
                ai_status = self._read_register(self.REG_AI_STATUS)
                if ai_status & 0x01:  # AI active
                    confidence = self._read_register(self.REG_AI_CONFIDENCE)
                    # Boost quality when AI tracking is confident
                    squal = max(squal, int(confidence * 0.8))
            
            return squal
        except Exception as e:
            logger.error(f"Failed to read surface quality: {e}")
            return 0
    
    def get_ai_status(self) -> Optional[AIBoxStatus]:
        """
        Get comprehensive AI Box status
        
        Returns:
            AIBoxStatus object or None if AI Box not available
        """
        if not self.ai_box_available:
            return None
        
        try:
            ai_status_byte = self._read_register(self.REG_AI_STATUS)
            mode = AIBoxMode(self._read_register(self.REG_AI_MODE))
            target_type = TrackingTarget(self._read_register(self.REG_AI_TARGET_TYPE))
            
            tracking_active = bool(ai_status_byte & 0x01)
            target_detected = bool(ai_status_byte & 0x02)
            
            target_x = self._read_word(self.REG_AI_TARGET_X_L)
            target_y = self._read_word(self.REG_AI_TARGET_Y_L)
            confidence = self._read_register(self.REG_AI_CONFIDENCE) / 255.0
            fps = self._read_register(self.REG_AI_FPS)
            quality = self._read_register(self.REG_SQUAL)
            
            return AIBoxStatus(
                mode=mode,
                tracking_active=tracking_active,
                target_detected=target_detected,
                target_type=target_type,
                target_confidence=confidence,
                target_x=target_x,
                target_y=target_y,
                processing_fps=fps,
                optical_flow_quality=quality
            )
            
        except Exception as e:
            logger.error(f"Failed to get AI status: {e}")
            return None
    
    def set_ai_mode(self, mode: AIBoxMode):
        """Set AI Box operating mode"""
        if not self.ai_box_available:
            logger.warning("AI Box not available")
            return
        
        try:
            self._write_register(self.REG_AI_MODE, int(mode))
            self.ai_config.mode = mode
            logger.info(f"AI mode set to: {mode.name}")
        except Exception as e:
            logger.error(f"Failed to set AI mode: {e}")
    
    def set_tracking_target(self, target: TrackingTarget):
        """Set AI tracking target type"""
        if not self.ai_box_available:
            logger.warning("AI Box not available")
            return
        
        try:
            self._write_register(self.REG_AI_TARGET_TYPE, int(target))
            self.ai_config.tracking_target = target
            logger.info(f"Tracking target set to: {target.name}")
        except Exception as e:
            logger.error(f"Failed to set tracking target: {e}")
    
    def set_roi(self, x: int, y: int, width: int, height: int):
        """
        Set region of interest for AI processing
        
        Args:
            x, y: Top-left corner coordinates
            width, height: ROI dimensions
        """
        if not self.ai_box_available:
            logger.warning("AI Box not available")
            return
        
        try:
            self._write_word(self.REG_AI_ROI_X_L, x)
            self._write_word(self.REG_AI_ROI_Y_L, y)
            self._write_word(self.REG_AI_ROI_W_L, width)
            self._write_word(self.REG_AI_ROI_H_L, height)
            
            self.ai_config.roi_x = x
            self.ai_config.roi_y = y
            self.ai_config.roi_width = width
            self.ai_config.roi_height = height
            
            logger.info(f"ROI set to: ({x}, {y}) {width}x{height}")
        except Exception as e:
            logger.error(f"Failed to set ROI: {e}")
    
    def get_diagnostics(self) -> dict:
        """
        Get comprehensive diagnostic information
        
        Returns:
            Dictionary with sensor status
        """
        try:
            diag = {
                'product_id': f"0x{self._read_register(self.REG_PRODUCT_ID):02X}",
                'revision': f"0x{self._read_register(self.REG_REVISION_ID):02X}",
                'surface_quality': self.get_surface_quality(),
                'shutter': (self._read_register(self.REG_SHUTTER_UPPER) << 8) | 
                           self._read_register(self.REG_SHUTTER_LOWER),
                'pixel_max': self._read_register(self.REG_PIX_MAX),
                'pixel_avg': self._read_register(self.REG_PIX_AVG),
                'pixel_min': self._read_register(self.REG_PIX_MIN),
                'ai_box_available': self.ai_box_available
            }
            
            # Add AI Box diagnostics if available
            if self.ai_box_available:
                ai_status = self.get_ai_status()
                if ai_status:
                    diag['ai_mode'] = ai_status.mode.name
                    diag['ai_tracking_active'] = ai_status.tracking_active
                    diag['ai_target_detected'] = ai_status.target_detected
                    diag['ai_target_type'] = ai_status.target_type.name
                    diag['ai_confidence'] = f"{ai_status.target_confidence:.2f}"
                    diag['ai_fps'] = ai_status.processing_fps
            
            return diag
            
        except Exception as e:
            logger.error(f"Failed to get diagnostics: {e}")
            return {'error': str(e)}
    
    def shutdown(self):
        """Shutdown sensor and close connections"""
        try:
            self._write_register(self.REG_POWER_MODE, 0x01)
            self.bus.close()
            
            if self.serial_conn:
                self.serial_conn.close()
            
            logger.info("Caddx Infra 256CA AI Box shutdown")
        except Exception as e:
            logger.error(f"Shutdown error: {e}")


def detect_caddx_infra256_aibox(bus_number: int = 1) -> Optional[Tuple[int, bool]]:
    """
    Auto-detect Caddx Infra 256CA on I2C bus
    
    Args:
        bus_number: I2C bus to scan
    
    Returns:
        Tuple of (I2C address, has_ai_box) if found, None otherwise
    """
    if not I2C_AVAILABLE:
        return None
    
    addresses = [0x29, 0x28, 0x2A, 0x30]
    
    try:
        bus = smbus.SMBus(bus_number)
        
        for addr in addresses:
            try:
                bus.write_byte(addr, 0x00)
                time.sleep(0.01)
                product_id = bus.read_byte_data(addr, 0x00)
                
                if product_id == 0x4A:  # AI Box version
                    logger.info(f"Caddx Infra 256CA AI Box found at 0x{addr:02X}")
                    bus.close()
                    return (addr, True)
                elif product_id == 0x49:  # Standard version
                    logger.info(f"Caddx Infra 256 (standard) found at 0x{addr:02X}")
                    bus.close()
                    return (addr, False)
                    
            except:
                continue
        
        bus.close()
        
    except Exception as e:
        logger.error(f"I2C scan failed: {e}")
    
    return None


# Test function
if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    
    print("Caddx Infra 256CA AI Box Test")
    print("=" * 50)
    
    # Try to detect sensor
    print("\nScanning for sensor...")
    detection = detect_caddx_infra256_aibox()
    
    if detection:
        addr, has_ai_box = detection
        print(f"Sensor detected at address 0x{addr:02X}")
        print(f"AI Box: {'Yes' if has_ai_box else 'No'}")
        
        # Initialize sensor
        ai_config = AIBoxConfig(
            mode=AIBoxMode.AUTO_MODE,
            tracking_target=TrackingTarget.GROUND_TEXTURE,
            stabilization_strength=0.7
        )
        
        sensor = CaddxInfra256AIBox(
            address=addr,
            ai_config=ai_config
        )
        
        # Get diagnostics
        print("\nDiagnostics:")
        diag = sensor.get_diagnostics()
        for key, value in diag.items():
            print(f"  {key}: {value}")
        
        # Test AI status if available
        if sensor.ai_box_available:
            print("\nAI Box Status:")
            ai_status = sensor.get_ai_status()
            if ai_status:
                print(f"  Mode: {ai_status.mode.name}")
                print(f"  Tracking Active: {ai_status.tracking_active}")
                print(f"  Target Detected: {ai_status.target_detected}")
                print(f"  Target Type: {ai_status.target_type.name}")
                print(f"  Confidence: {ai_status.target_confidence:.2f}")
                print(f"  Processing FPS: {ai_status.processing_fps}")
        
        # Read motion for 5 seconds
        print("\nReading motion (5 seconds):")
        print("Time  | Delta X | Delta Y | Quality | AI Conf")
        print("-" * 55)
        
        start_time = time.time()
        while time.time() - start_time < 5.0:
            dx, dy = sensor.get_motion()
            squal = sensor.get_surface_quality()
            
            ai_conf = 0.0
            if sensor.ai_box_available:
                ai_st = sensor.get_ai_status()
                if ai_st:
                    ai_conf = ai_st.target_confidence
            
            elapsed = time.time() - start_time
            print(f"{elapsed:5.2f} | {dx:7d} | {dy:7d} | {squal:3d} | {ai_conf:.2f}", end='\r')
            time.sleep(0.1)
        
        print("\n\nTest complete!")
        sensor.shutdown()
        
    else:
        print("No sensor detected. Check connections:")
        print("  - I2C enabled (sudo raspi-config)")
        print("  - Sensor connected to I2C pins")
        print("  - Sensor powered (3.3V)")
