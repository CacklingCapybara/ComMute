#!/bin/bash
# ComMute Setup Script

set -e

echo "=== ComMute Setup ==="
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check for Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: Docker Compose is not installed"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✓ Docker found"
echo "✓ Docker Compose found"
echo ""

# Create necessary directories
echo "Creating directories..."
mkdir -p logs config

# Check for config file
if [ ! -f "config/config.json" ]; then
    echo "Creating default config file..."
    cat > config/config.json <<EOF
{
  "video_device": "/dev/video0",
  "remote_name": "tv",
  "mute_button": "KEY_MUTE",
  "scene_change_threshold": 0.3,
  "volume_spike_threshold": 1.5,
  "min_commercial_duration": 5,
  "detection_buffer": 2,
  "fps": 30,
  "detection_sensitivity": "medium",
  "log_level": "INFO"
}
EOF
    echo "✓ Default config created at config/config.json"
else
    echo "✓ Config file exists"
fi

# Check for video devices
echo ""
echo "Checking for video capture devices..."
if ls /dev/video* &> /dev/null; then
    echo "Found video devices:"
    ls -l /dev/video*
    echo ""
    echo "Make sure your HDMI capture device is one of these."
    echo "Update config/config.json if it's not /dev/video0"
else
    echo "WARNING: No video devices found at /dev/video*"
    echo "Please connect your USB HDMI capture device"
fi

# Check for LIRC
echo ""
echo "Checking for LIRC (IR blaster)..."
if command -v irsend &> /dev/null; then
    echo "✓ LIRC is installed"
    
    # Check for LIRC device
    if ls /dev/lirc* &> /dev/null; then
        echo "✓ Found LIRC device:"
        ls -l /dev/lirc*
    else
        echo "WARNING: No LIRC device found at /dev/lirc*"
        echo "Please connect and configure your USB IR blaster"
    fi
else
    echo "WARNING: LIRC not installed on host system"
    echo "Install LIRC: sudo apt-get install lirc"
    echo ""
    echo "After installing LIRC:"
    echo "1. Configure /etc/lirc/lircd.conf with your TV's IR codes"
    echo "2. Test with: irsend SEND_ONCE tv KEY_MUTE"
fi

# Check for required files
echo ""
echo "Checking project files..."
required_files=("commute.py" "Dockerfile" "requirements.txt" "docker-compose.yml")
all_present=true

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "✗ $file missing"
        all_present=false
    fi
done

if [ "$all_present" = false ]; then
    echo ""
    echo "ERROR: Some required files are missing"
    exit 1
fi

# Final instructions
echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Configure your hardware:"
echo "   - Connect USB HDMI capture device"
echo "   - Connect USB IR blaster"
echo "   - Configure LIRC for your TV model"
echo ""
echo "2. Test your hardware:"
echo "   - Video: ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 test.jpg"
echo "   - IR: irsend SEND_ONCE tv KEY_MUTE"
echo ""
echo "3. Customize config/config.json if needed"
echo ""
echo "4. Start ComMute:"
echo "   docker-compose up -d"
echo ""
echo "5. View logs:"
echo "   docker-compose logs -f"
echo "   # or"
echo "   tail -f logs/commute.log"
echo ""
echo "6. Stop ComMute:"
echo "   docker-compose down"
echo ""