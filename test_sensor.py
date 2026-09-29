#!/usr/bin/env python3
"""
Test script for optical flow sensors and cameras
Verifies sensor/camera connection and displays real-time optical flow data
Supports: Camera (CSI/USB/Analog), PMW3901 (SPI), Caddx Infra 256 (I2C)
"""

import time
import sys
import argparse
import logging
from camera_optical_flow import CameraOpticalFlow, AnalogCameraFlow, OpticalFlowTracker, auto_detect_camera

try:
    from optical_flow_sensor import PMW3901, OpticalFlowTracker as SPIFlowTracker
    SPI_AVAILABLE = True
except ImportError:
    SPI_AVAILABLE = False

try:
    from caddx_infra256 import CaddxInfra256, detect_caddx_infra256
    CADDX_AVAILABLE = True
except ImportError:
    CADDX_AVAILABLE = False

logger = logging.getLogger(__name__)


def test_camera_detection():
    """Test camera detection"""
    print("Detecting cameras...")
    try:
        camera_id = auto_detect_camera()
        if camera_id is not None:
            print(f"[OK] Camera detected at ID: {camera_id}")
            return camera_id
        else:
            print("[FAIL] No camera detected")
            print("\nTroubleshooting:")
            print("  - Check camera cable connection")
            print("  - Run: vcgencmd get_camera")
            print("  - Run: ls /dev/video*")
            sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Failed to detect camera: {e}")
        sys.exit(1)


def test_camera_initialization(camera_id=0):
    """Test camera initialization"""
    print(f"\nInitializing camera {camera_id}...")
    try:
        sensor = CameraOpticalFlow(
            camera_id=camera_id,
            width=320,
            height=240,
            fps=30,
            method='lucas_kanade'  # Faster for testing
        )
        sensor.start()
        time.sleep(1)  # Let camera warm up
        print("[OK] Camera initialized successfully")
        return sensor
    except Exception as e:
        print(f"[FAIL] Failed to initialize camera: {e}")
        sys.exit(1)


def test_pmw3901_initialization():
    """Test PMW3901 SPI sensor initialization"""
    print("\nInitializing PMW3901 SPI sensor...")
    if not SPI_AVAILABLE:
        print("[FAIL] optical_flow_sensor module not available")
        sys.exit(1)
    try:
        sensor = PMW3901()
        print("[OK] PMW3901 initialized successfully")
        print(f"[OK] Product ID: {hex(sensor.PRODUCT_ID)}")
        return sensor
    except Exception as e:
        print(f"[FAIL] Failed to initialize PMW3901: {e}")
        sys.exit(1)


def test_caddx_initialization():
    """Test Caddx Infra 256 I2C sensor initialization"""
    print("\nInitializing Caddx Infra 256 I2C sensor...")
    if not CADDX_AVAILABLE:
        print("[FAIL] Caddx Infra 256 module not available (install smbus2)")
        sys.exit(1)
    try:
        addr = detect_caddx_infra256() or 0x29
        sensor = CaddxInfra256(address=addr)
        print(f"[OK] Caddx Infra 256 initialized at address 0x{addr:02X}")
        return sensor
    except Exception as e:
        print(f"[FAIL] Failed to initialize Caddx sensor: {e}")
        sys.exit(1)


def test_motion_reading(sensor, duration=5):
    """Test optical flow motion reading"""
    print(f"\nReading optical flow for {duration} seconds...")
    print("Move the sensor/camera (or object below) to see motion values\n")
    print("Time(s) | Flow X  | Flow Y  | Quality")
    print("-" * 45)
    
    start_time = time.time()
    while time.time() - start_time < duration:
        flow_x, flow_y = sensor.get_motion()
        quality = sensor.get_surface_quality()
        elapsed = time.time() - start_time
        
        print(f"{elapsed:6.2f}  | {flow_x:7.2f} | {flow_y:7.2f} | {quality:3d}    ", end='\r')
        time.sleep(0.1)
    
    print("\n[OK] Motion reading test complete")


def test_position_tracking(sensor, duration=10):
    """Test position tracking with integration"""
    print(f"\nTesting position tracking for {duration} seconds...")
    print("Move the sensor/camera to track position\n")
    
    if isinstance(sensor, (CameraOpticalFlow, AnalogCameraFlow)):
        tracker = OpticalFlowTracker(sensor, scale_factor=0.001, height_m=0.5)
    else:
        tracker = SPIFlowTracker(sensor, scale_factor=0.001, height_m=0.5)
    
    print("Time(s) | Pos X(m) | Pos Y(m) | Vel X(m/s) | Vel Y(m/s) | Quality")
    print("-" * 65)
    
    start_time = time.time()
    pos_x, pos_y = 0.0, 0.0
    while time.time() - start_time < duration:
        pos_x, pos_y = tracker.update()
        vel_x, vel_y = tracker.get_velocity()
        quality = tracker.get_surface_quality()
        elapsed = time.time() - start_time
        
        print(
            f"{elapsed:6.2f}  | {pos_x:8.4f} | {pos_y:8.4f} | "
            f"{vel_x:10.4f} | {vel_y:10.4f} | {quality:3d}    ",
            end='\r'
        )
        time.sleep(0.05)
    
    print("\n[OK] Position tracking test complete")
    print(f"\nFinal position: ({pos_x:.4f}, {pos_y:.4f}) meters")


def test_surface_quality(sensor, duration=5):
    """Monitor surface quality over time"""
    print(f"\nMonitoring surface quality for {duration} seconds...")
    print("Quality values: <100 (poor), 100-200 (good), >200 (excellent)\n")
    
    qualities = []
    start_time = time.time()
    
    while time.time() - start_time < duration:
        quality = sensor.get_surface_quality()
        qualities.append(quality)
        elapsed = time.time() - start_time
        
        bar_length = min(quality // 5, 50)
        print(f"Time: {elapsed:5.2f}s | Quality: {quality:3d} {'#' * bar_length}    ", end='\r')
        time.sleep(0.1)
    
    print("\n")
    avg_quality = sum(qualities) / len(qualities) if qualities else 0
    min_quality = min(qualities) if qualities else 0
    max_quality = max(qualities) if qualities else 0
    
    print(f"Average quality: {avg_quality:.1f}")
    print(f"Range: {min_quality} - {max_quality}")
    
    if avg_quality < 100:
        print("[WARN] Low quality - improve lighting or surface texture")
        print("    Tips:")
        print("    - Ensure surface has visible texture (not blank)")
        print("    - Check lighting conditions")
        print("    - Clean sensor / camera lens")
    elif avg_quality < 200:
        print("[OK] Good quality - suitable for tracking")
    else:
        print("[OK] Excellent quality - optimal for tracking")


def test_camera_capture(sensor):
    """Test camera frame capture"""
    print("\nTesting camera frame capture...")
    try:
        frame = sensor.get_current_frame()
        if frame is not None:
            print("[OK] Frame captured successfully")
            print(f"  Resolution: {frame.shape[1]}x{frame.shape[0]}")
            print(f"  Channels: {frame.shape[2] if len(frame.shape) > 2 else 1}")
        else:
            print("[FAIL] Failed to capture frame")
    except Exception as e:
        print(f"[FAIL] Frame capture error: {e}")


def close_sensor(sensor):
    """Clean up sensor resources safely"""
    if hasattr(sensor, 'stop'):
        sensor.stop()
    elif hasattr(sensor, 'shutdown'):
        sensor.shutdown()
    elif hasattr(sensor, 'close'):
        sensor.close()


def main():
    parser = argparse.ArgumentParser(description='Test optical flow sensors and cameras')
    parser.add_argument(
        '-s', '--sensor',
        choices=['camera', 'pmw3901', 'caddx'],
        default='camera',
        help='Sensor type to test (default: camera)'
    )
    parser.add_argument(
        '-t', '--test',
        choices=['detection', 'motion', 'tracking', 'quality', 'capture', 'all'],
        default='all',
        help='Test to run'
    )
    parser.add_argument(
        '-d', '--duration',
        type=int,
        default=5,
        help='Test duration in seconds'
    )
    parser.add_argument(
        '-c', '--camera',
        type=int,
        default=None,
        help='Camera ID (auto-detect if not specified, only for camera sensor)'
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print(f"Optical Flow Test ({args.sensor.upper()})")
    print("=" * 50)
    print()
    
    sensor = None
    try:
        if args.sensor == 'pmw3901':
            sensor = test_pmw3901_initialization()
        elif args.sensor == 'caddx':
            sensor = test_caddx_initialization()
        else:
            # Camera sensor
            if args.camera is None:
                if args.test in ['detection', 'all']:
                    camera_id = test_camera_detection()
                else:
                    camera_id = auto_detect_camera()
                    if camera_id is None:
                        print("[FAIL] No camera detected. Specify with -c option.")
                        sys.exit(1)
            else:
                camera_id = args.camera
                print(f"Using specified camera ID: {camera_id}")
            
            if args.test != 'detection':
                sensor = test_camera_initialization(camera_id)
        
        # Run tests
        if sensor is not None:
            if args.test in ['capture', 'all'] and hasattr(sensor, 'get_current_frame'):
                test_camera_capture(sensor)
            
            if args.test in ['motion', 'all']:
                test_motion_reading(sensor, args.duration)
            
            if args.test in ['quality', 'all']:
                test_surface_quality(sensor, args.duration)
            
            if args.test in ['tracking', 'all']:
                test_position_tracking(sensor, args.duration * 2)
        
        print("\n" + "=" * 50)
        print("All tests completed successfully!")
        print("=" * 50)
        
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if sensor is not None:
            close_sensor(sensor)


if __name__ == '__main__':
    main()
