#!/usr/bin/env python3
"""
Basic tests for Betafly Stabilization System
"""

import sys
import os
import unittest
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.controller import PIDController, PIDGains
from src.utils import pixels_to_degrees, degrees_to_pixels


class TestPIDController(unittest.TestCase):
    """Test PID controller functionality"""
    
    def setUp(self):
        """Setup test PID controller"""
        self.gains = PIDGains(kp=1.0, ki=0.1, kd=0.01)
        self.controller = PIDController(self.gains)
        
    def test_initialization(self):
        """Test controller initialization"""
        self.assertEqual(self.controller.gains.kp, 1.0)
        self.assertEqual(self.controller.gains.ki, 0.1)
        self.assertEqual(self.controller.gains.kd, 0.01)
        self.assertTrue(self.controller.enabled)
        
    def test_compute(self):
        """Test PID computation"""
        self.controller.setpoint = 10.0
        
        # First computation
        output = self.controller.compute(5.0, dt=0.1)
        self.assertIsNotNone(output)
        
        # Output should be positive (error is positive)
        self.assertGreater(output, 0)
        
    def test_limits(self):
        """Test output limiting"""
        self.controller.setpoint = 100.0  # Large setpoint
        output = self.controller.compute(0.0, dt=0.1)
        
        # Should be limited to max output
        self.assertLessEqual(output, self.controller.output_max)
        self.assertGreaterEqual(output, self.controller.output_min)
        
    def test_reset(self):
        """Test controller reset"""
        self.controller.setpoint = 10.0
        self.controller.compute(5.0, dt=0.1)
        
        # Reset should clear state
        self.controller.reset()
        self.assertEqual(self.controller.state.integral, 0.0)
        self.assertEqual(self.controller.state.last_error, 0.0)


class TestUtils(unittest.TestCase):
    """Test utility functions"""
    
    def test_pixels_to_degrees(self):
        """Test pixel to degree conversion"""
        # 100 pixels displacement in 640 pixel width image with 60° FOV
        degrees = pixels_to_degrees(100, 640, 60)
        expected = (100 / 640) * 60
        self.assertAlmostEqual(degrees, expected, places=2)
        
    def test_degrees_to_pixels(self):
        """Test degree to pixel conversion"""
        # 10 degrees displacement with 60° FOV in 640 pixel image
        pixels = degrees_to_pixels(10, 640, 60)
        expected = (10 / 60) * 640
        self.assertAlmostEqual(pixels, expected, places=2)
        
    def test_conversion_symmetry(self):
        """Test that conversions are symmetric"""
        original_pixels = 150
        degrees = pixels_to_degrees(original_pixels, 640, 60)
        recovered_pixels = degrees_to_pixels(degrees, 640, 60)
        self.assertAlmostEqual(original_pixels, recovered_pixels, places=1)


class TestSystemIntegration(unittest.TestCase):
    """Test system integration"""
    
    def test_import_modules(self):
        """Test that all modules can be imported"""
        try:
            from src.camera import Camera
            from src.tracker import OpticalTracker
            from src.servo import ServoController
            from src.stabilizer import Stabilizer
            self.assertTrue(True)
        except ImportError as e:
            self.fail(f"Failed to import module: {e}")
            
    def test_config_loading(self):
        """Test configuration loading"""
        from src.stabilizer import StabilizerConfig
        
        # Test default config
        config = StabilizerConfig()
        self.assertEqual(config.camera_resolution, (320, 240))
        self.assertEqual(config.camera_framerate, 20)
        self.assertIsInstance(config.pan_kp, float)


class TestPositionStabilizerModule(unittest.TestCase):
    """Test position_stabilizer module classes"""
    
    def test_pid_controller(self):
        from position_stabilizer import PIDController, PIDGains
        gains = PIDGains(kp=1.0, ki=0.1, kd=0.05)
        pid = PIDController(gains, output_limits=(-1.0, 1.0))
        
        # First call returns 0
        out0 = pid.update(10.0, 0.0, current_time=1.0)
        self.assertEqual(out0, 0.0)
        
        # Subsequent call computes output
        out1 = pid.update(10.0, 0.0, current_time=1.05)
        self.assertGreater(out1, 0.0)
        self.assertLessEqual(out1, 1.0)
        
        # dt <= 0 should return 0.0 safely
        out2 = pid.update(10.0, 0.0, current_time=1.05)
        self.assertEqual(out2, 0.0)
        
        # Reset clears state
        pid.reset()
        self.assertEqual(pid.integral, 0.0)
        self.assertIsNone(pid.prev_time)

    def test_position_stabilizer(self):
        from position_stabilizer import PositionStabilizer
        stab = PositionStabilizer()
        
        # When disabled, corrections are 0.0
        corr_x, corr_y = stab.update(1.0, 2.0)
        self.assertEqual(corr_x, 0.0)
        self.assertEqual(corr_y, 0.0)
        
        # When enabled, calculates corrections
        stab.enable()
        corr_x, corr_y = stab.update(1.0, 2.0)
        self.assertIsNotNone(corr_x)
        self.assertIsNotNone(corr_y)
        
    def test_stabilization_controller_clamping(self):
        from position_stabilizer import StabilizationController, PIDGains
        max_tilt = 15.0
        controller = StabilizationController(
            position_gains_x=PIDGains(kp=5.0, ki=1.0, kd=1.0),
            position_gains_y=PIDGains(kp=5.0, ki=1.0, kd=1.0),
            velocity_damping=2.0,
            max_tilt=max_tilt
        )
        controller.set_mode("position_hold")
        # Massive velocity and position error should be clamped to max_tilt
        pitch, roll = controller.update(current_x=100.0, current_y=100.0, vel_x=50.0, vel_y=50.0)
        self.assertLessEqual(abs(pitch), max_tilt)
        self.assertLessEqual(abs(roll), max_tilt)


class TestStickInputScaling(unittest.TestCase):
    """Test RC stick input conversion calculations"""
    
    def test_sbus_range_mapping(self):
        # 172 -> 1000 us, 1811 -> 2000 us, 992 -> 1500 us
        val_min = int((172 - 172) * 1000 / 1639 + 1000)
        val_max = int((1811 - 172) * 1000 / 1639 + 1000)
        val_mid = int((991.5 - 172) * 1000 / 1639 + 1000)
        self.assertEqual(val_min, 1000)
        self.assertEqual(val_max, 2000)
        self.assertAlmostEqual(val_mid, 1500, delta=2)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], exit=False, verbosity=2)


if __name__ == '__main__':
    run_tests()