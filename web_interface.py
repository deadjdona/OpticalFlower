#!/usr/bin/env python3
"""
Web Interface for Betafly Stabilization System
Provides GUI for configuration and real-time monitoring
"""

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
import json
import os
import copy
import threading
import time
from typing import Optional, Tuple, Dict, Any
import logging
from queue import Queue

logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Global state
system_state = {
    'running': False,
    'mode': 'off',
    'position': {'x': 0.0, 'y': 0.0},
    'velocity': {'x': 0.0, 'y': 0.0},
    'corrections': {'pitch': 0.0, 'roll': 0.0},
    'surface_quality': 0,
    'height': 0.5,
    'stick_inputs': {'pitch': 0, 'roll': 0, 'throttle': 0, 'yaw': 0},
    'camera_type': 'pmw3901',
    'last_update': time.time()
}

config_lock = threading.Lock()
state_lock = threading.Lock()
command_queue = Queue()

CONFIG_FILE = 'config.json'


@app.route('/')
def index():
    """Serve main dashboard"""
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        with config_lock:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        return jsonify({'success': True, 'config': config})
    except Exception as e:
        logger.error(f"Error reading config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """Update configuration"""
    try:
        new_config = request.json
        
        # Validate config
        is_valid, err_msg = validate_config(new_config)
        if not is_valid:
            return jsonify({'success': False, 'error': f'Invalid configuration: {err_msg}'}), 400
        
        # Save to file atomically to prevent corruption on sudden power loss
        with config_lock:
            temp_file = f"{CONFIG_FILE}.tmp"
            with open(temp_file, 'w') as f:
                json.dump(new_config, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_file, CONFIG_FILE)
        
        logger.info("Configuration updated via web interface")
        return jsonify({'success': True, 'message': 'Configuration saved'})
    
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current system state"""
    with state_lock:
        state_snapshot = copy.deepcopy(system_state)
    return jsonify({
        'success': True,
        'state': state_snapshot
    })


@app.route('/api/command', methods=['POST'])
def send_command():
    """Send command to system"""
    try:
        payload = request.json or {}
        cmd = payload.get('command')
        params = payload.get('params', {}) or {}

        if not cmd:
            return jsonify({'success': False, 'error': 'Missing command'}), 400
        
        if cmd == 'set_mode':
            mode = params.get('mode')
            if mode in ['off', 'velocity_damping', 'position_hold']:
                with state_lock:
                    system_state['mode'] = mode
                command_queue.put({'command': cmd, 'params': params})
                return jsonify({'success': True, 'message': f'Mode set to {mode}'})
            else:
                return jsonify({'success': False, 'error': 'Invalid mode'}), 400
        
        elif cmd == 'reset_position':
            with state_lock:
                system_state['position'] = {'x': 0.0, 'y': 0.0}
            command_queue.put({'command': cmd, 'params': params})
            return jsonify({'success': True, 'message': 'Position reset'})
        
        elif cmd == 'set_height':
            height = float(params.get('height', 0.5))
            if 0.1 <= height <= 5.0:
                with state_lock:
                    system_state['height'] = height
                command_queue.put({'command': cmd, 'params': {'height': height}})
                return jsonify({'success': True, 'message': f'Height set to {height}m'})
            else:
                return jsonify({'success': False, 'error': 'Height out of range'}), 400
        
        elif cmd == 'hold_position':
            with state_lock:
                system_state['mode'] = 'position_hold'
            command_queue.put({'command': cmd, 'params': params})
            return jsonify({'success': True, 'message': 'Position hold activated'})
        
        else:
            return jsonify({'success': False, 'error': 'Unknown command'}), 400
    
    except Exception as e:
        logger.error(f"Error processing command: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/camera_types', methods=['GET'])
def get_camera_types():
    """Get available camera types"""
    camera_types = [
        {'id': 'pmw3901', 'name': 'PMW3901 Optical Flow Sensor (SPI)'},
        {'id': 'caddx_infra256', 'name': 'Caddx Infra 256 (I2C)'},
        {'id': 'caddx_infra256ca', 'name': 'Caddx Infra 256CA + AI Box'},
        {'id': 'usb_camera', 'name': 'USB Camera (OpenCV)'},
        {'id': 'csi_camera', 'name': 'Raspberry Pi Camera (CSI)'},
        {'id': 'analog_usb', 'name': 'Analog Camera via USB Capture'},
        {'id': 'opencv_any', 'name': 'Any OpenCV Compatible Camera'}
    ]
    return jsonify({'success': True, 'cameras': camera_types})


def validate_config(config: Any) -> Tuple[bool, str]:
    """
    Validate configuration structure, data types, and value bounds.
    
    Args:
        config: Configuration dictionary to validate
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not isinstance(config, dict):
        return False, "Configuration must be a JSON object"
        
    required_keys = ['sensor', 'tracker', 'pid', 'stabilizer', 'control']
    for key in required_keys:
        if key not in config:
            return False, f"Missing required configuration section: '{key}'"
        if not isinstance(config[key], dict):
            return False, f"Section '{key}' must be an object"
            
    # Sensor checks
    sensor_cfg = config['sensor']
    valid_sensors = {
        'pmw3901', 'caddx_infra256', 'caddx_infra256ca',
        'usb_camera', 'csi_camera', 'analog_usb', 'opencv_any'
    }
    sensor_type = sensor_cfg.get('type')
    if not sensor_type or sensor_type not in valid_sensors:
        return False, f"Invalid or missing sensor type: {sensor_type}. Must be one of {sorted(valid_sensors)}"
        
    # Tracker checks
    tracker_cfg = config['tracker']
    scale_factor = tracker_cfg.get('scale_factor', 0.001)
    if not isinstance(scale_factor, (int, float)) or scale_factor <= 0:
        return False, "tracker.scale_factor must be a positive number"
        
    initial_height = tracker_cfg.get('initial_height', 0.5)
    if not isinstance(initial_height, (int, float)) or initial_height <= 0:
        return False, "tracker.initial_height must be a positive number"
        
    # Control checks
    control_cfg = config['control']
    update_rate = control_cfg.get('update_rate_hz', 50)
    if not isinstance(update_rate, (int, float)) or update_rate <= 0 or update_rate > 500:
        return False, "control.update_rate_hz must be between 1 and 500 Hz"
        
    # PID checks
    pid_cfg = config['pid']
    for axis in ['position_x', 'position_y']:
        if axis in pid_cfg:
            axis_cfg = pid_cfg[axis]
            if not isinstance(axis_cfg, dict):
                return False, f"pid.{axis} must be an object"
            for gain in ['kp', 'ki', 'kd']:
                if gain in axis_cfg and not isinstance(axis_cfg[gain], (int, float)):
                    return False, f"pid.{axis}.{gain} must be a number"
                    
    return True, "Valid configuration"


def update_system_state(stabilizer_instance):
    """Update system state from stabilizer instance (called by main system)"""
    global system_state
    # This function will be called by the main stabilizer to update state
    pass


def start_web_server(host='0.0.0.0', port=8080, debug=False):
    """Start the web server"""
    logger.info(f"Starting web interface on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    start_web_server(debug=True)
