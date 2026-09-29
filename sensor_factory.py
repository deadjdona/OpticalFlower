"""
Sensor Factory for Betafly Stabilization System
Handles creation of various optical flow sensors (PMW3901, Caddx, Camera-based)
"""

import logging
from typing import Optional

from optical_flow_sensor import PMW3901
from camera_optical_flow import CameraOpticalFlow, AnalogCameraFlow, auto_detect_camera

# Try to import Caddx Infra 256
try:
    from caddx_infra256 import CaddxInfra256
    CADDX_AVAILABLE = True
except ImportError:
    CADDX_AVAILABLE = False

# Try to import Caddx Infra 256CA (AI Box)
try:
    from caddx_infra256ca import CaddxInfra256CA
    CADDX_CA_AVAILABLE = True
except ImportError:
    CADDX_CA_AVAILABLE = False

logger = logging.getLogger(__name__)

def create_sensor(config: dict):
    """
    Factory function to create the appropriate sensor based on configuration
    
    Args:
        config: Complete configuration dictionary containing 'sensor' and 'camera' keys
        
    Returns:
        Sensor instance (PMW3901, CaddxInfra256, CameraOpticalFlow, or AnalogCameraFlow)
    """
    sensor_config = config.get('sensor', {})
    camera_type = sensor_config.get('type', 'pmw3901')
    logger.info(f"Initializing sensor: {camera_type}")

    if camera_type == 'pmw3901':
        return PMW3901(
            spi_bus=sensor_config.get('spi_bus', 0),
            spi_device=sensor_config.get('spi_device', 0),
            rotation=sensor_config.get('rotation', 0)
        )
    elif camera_type == 'caddx_infra256':
        if not CADDX_AVAILABLE:
            raise RuntimeError("Caddx Infra 256 support not available. Install smbus2: pip install smbus2")
        
        return CaddxInfra256(
            bus_number=sensor_config.get('i2c_bus', 1),
            address=sensor_config.get('i2c_address', 0x29),
            rotation=sensor_config.get('rotation', 0)
        )
    elif camera_type == 'caddx_infra256ca':
        if not CADDX_CA_AVAILABLE:
            raise RuntimeError("Caddx Infra 256CA support not available. Install pyserial for AI Box streaming.")
        
        ai_box_cfg = sensor_config.get('ai_box', {})
        tcp_port = ai_box_cfg.get('tcp_port')
        if tcp_port is None:
            tcp_port = ai_box_cfg.get('port', 8899)

        return CaddxInfra256CA(
            rotation=sensor_config.get('rotation', 0),
            connection=ai_box_cfg.get('connection', 'auto'),
            serial_port=ai_box_cfg.get('serial_port', '/dev/ttyUSB0'),
            serial_baudrate=int(ai_box_cfg.get('serial_baudrate', 921600)),
            tcp_host=ai_box_cfg.get('tcp_host') or ai_box_cfg.get('host'),
            tcp_port=int(tcp_port or 8899),
            data_format=ai_box_cfg.get('data_format', 'auto'),
            data_timeout=float(ai_box_cfg.get('data_timeout', 0.25)),
            height_scale=float(ai_box_cfg.get('height_scale', 1.0)),
            height_smoothing=float(ai_box_cfg.get('height_smoothing', 0.2)),
        )
    elif camera_type in ['usb_camera', 'csi_camera', 'opencv_any']:
        camera_config = config.get('camera', {})
        camera_id = camera_config.get('device', 0)
        if camera_id == 'auto':
            camera_id = auto_detect_camera()
            if camera_id is None:
                raise RuntimeError("No camera detected")
        
        sensor = CameraOpticalFlow(
            camera_id=camera_id,
            width=camera_config.get('width', 640),
            height=camera_config.get('height', 480),
            fps=camera_config.get('fps', 30),
            method=camera_config.get('method', 'farneback')
        )
        sensor.start()
        return sensor
    elif camera_type == 'analog_usb':
        camera_config = config.get('camera', {})
        sensor = AnalogCameraFlow(
            device_path=camera_config.get('device', '/dev/video0'),
            width=camera_config.get('width', 720),
            height=camera_config.get('height', 480),
            deinterlace=camera_config.get('deinterlace', True)
        )
        sensor.start()
        return sensor
    else:
        raise ValueError(f"Unknown camera type: {camera_type}")
