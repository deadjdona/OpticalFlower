#!/bin/bash
# Setup script for Betafly Position Stabilization System
# Run this script on your Raspberry Pi Zero / Zero 2 W / Pi 4

set -e

echo "================================================"
echo "Betafly Stabilization System - Setup Script"
echo "================================================"
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ]; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "[1/6] Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "[2/6] Installing system dependencies..."
sudo apt-get install -y \
    python3 \
    python3-full \
    python3-pip \
    python3-dev \
    git

# venv setup
echo "[2.5/6] Setting up Python virtual environment..."
if [ ! -d "optic" ]; then
    python3 -m venv --system-site-packages optic
fi
source optic/bin/activate

# Enable hardware interfaces (SPI and Camera)
echo "[3/6] Enabling hardware interfaces (SPI and Camera)..."
REBOOT_REQUIRED=0

# Enable SPI for PMW3901
if ! grep -q "^dtparam=spi=on" /boot/config.txt 2>/dev/null; then
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    echo "SPI enabled (reboot required)"
    REBOOT_REQUIRED=1
else
    echo "SPI already enabled"
fi

# Enable I2C for Caddx Infra 256
if ! grep -q "^dtparam=i2c_arm=on" /boot/config.txt 2>/dev/null; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    echo "I2C enabled (reboot required)"
    REBOOT_REQUIRED=1
else
    echo "I2C already enabled"
fi

# Enable Camera for CSI/USB cameras
if ! grep -q "^start_x=1" /boot/config.txt 2>/dev/null; then
    echo "start_x=1" | sudo tee -a /boot/config.txt
    echo "gpu_mem=128" | sudo tee -a /boot/config.txt
    echo "Camera enabled (reboot required)"
    REBOOT_REQUIRED=1
else
    echo "Camera already enabled"
fi

# Install Python dependencies
echo "[4/6] Installing Python packages..."
pip3 install --upgrade pip
pip3 install -r requirements.txt

# Make scripts executable
echo "[5/6] Setting file permissions..."
chmod +x betafly_stabilizer.py betafly_stabilizer_advanced.py main.py calibrate.py calibrate_thermal.py test_sensor.py setup.sh 2>/dev/null || true

# Test installation
echo "[6/6] Testing installation..."
python3 -c "import cv2; print('✓ OpenCV installed')" 2>/dev/null || echo "⚠️ OpenCV not installed (optional, needed for camera flow)"
python3 -c "from camera_optical_flow import CameraOpticalFlow; print('✓ camera_optical_flow OK')" 2>/dev/null || true
python3 -c "from position_stabilizer import PositionStabilizer; print('✓ position_stabilizer OK')" 2>/dev/null || true

echo ""
echo "================================================"
echo "Setup Complete!"
echo "================================================"
echo ""

if [ "$REBOOT_REQUIRED" = "1" ]; then
    echo "⚠️  REBOOT REQUIRED to enable hardware interfaces"
    echo ""
    read -p "Reboot now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo reboot
    fi
else
    echo "✓ All set! You can now run:"
    echo "  ./betafly_stabilizer.py --help"
    echo "  or"
    echo "  ./betafly_stabilizer_advanced.py"
    echo "  or"
    echo "  python main.py"
fi

echo ""
