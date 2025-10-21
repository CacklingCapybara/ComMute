# ComMute

Detects commercial breaks during live TV and automatically mutes the audio via IR blaster.

## Features

- **Real-time Commercial Detection**: Analyzes video feed for commercial patterns
- **Automatic Mute Control**: Uses IR blaster to mute/unmute TV
- **Docker Containerized**: Easy deployment and isolation
- **Comprehensive Logging**: Track all detection events and mute commands
- **Configurable Detection**: Adjust sensitivity and thresholds

## Architecture

ComMute uses multiple heuristics to detect commercials:

1. **Scene Change Detection**: Commercials have more rapid scene changes than regular programming
2. **Cut Rate Analysis**: Measures editing pace (cuts per second)
3. **Black Frame Detection**: Identifies transitions between program and commercials

## Prerequisites

- Docker and Docker Compose installed
- USB HDMI capture card (e.g., Elgato HD60, generic USB capture device)
- USB IR blaster compatible with LIRC
- LIRC configured for your TV model

## Hardware Setup

### Video Capture Device

1. Connect your TV output (HDMI) to the USB capture device
2. Connect the capture device to your host system
3. Verify the device appears as `/dev/video0` (or note the actual device path)

```bash
# List video devices
v4l2-ctl --list-devices
```

### IR Blaster Setup

1. Connect USB IR blaster to host system
2. Configure LIRC with your TV's remote codes

```bash
# Test IR blaster
irsend SEND_ONCE tv KEY_MUTE
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/CacklingCapybara/ComMute.git
cd ComMute
```

2. Configure settings in `config/config.json`:
```json
{
  "video_device": "/dev/video0",
  "remote_name": "tv",
  "mute_button": "KEY_MUTE",
  "scene_change_threshold": 0.3,
  "min_commercial_duration": 5,
  "fps": 30
}
```

3. Update `docker-compose.yml` device paths if needed:
```yaml
devices:
  - /dev/video0:/dev/video0  # Your capture device
  - /dev/lirc0:/dev/lirc0    # Your IR blaster
```

4. Build and run:
```bash
docker-compose up -d
```

## Usage

### Start ComMute
```bash
docker-compose up -d
```

### View Logs
```bash
docker-compose logs -f
# Or check the logs directory
tail -f logs/commute.log
```

### Stop ComMute
```bash
docker-compose down
```

### Restart After Config Changes
```bash
docker-compose restart
```

## Configuration

Edit `config/config.json` to adjust detection parameters:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `video_device` | Video capture device path | `/dev/video0` |
| `remote_name` | LIRC remote name for your TV | `tv` |
| `mute_button` | IR command for mute button | `KEY_MUTE` |
| `scene_change_threshold` | Sensitivity for scene changes (0.0-1.0) | `0.3` |
| `min_commercial_duration` | Minimum seconds before muting | `5` |
| `fps` | Frames per second to process | `30` |

### Tuning Detection

- **Higher `scene_change_threshold`**: Less sensitive (fewer false positives)
- **Lower `scene_change_threshold`**: More sensitive (may mute regular programming)
- **Higher `min_commercial_duration`**: Wait longer before muting (more conservative)
- **Lower `min_commercial_duration`**: Mute sooner (more aggressive)

## Troubleshooting

### No Video Capture

```bash
# Check if device exists
ls -l /dev/video*

# Verify permissions
sudo usermod -aG video $USER

# Test capture
ffmpeg -f v4l2 -i /dev/video0 -frames:v 1 test.jpg
```

### IR Blaster Not Working

```bash
# Verify LIRC is running
sudo systemctl status lircd

# Test IR transmission
irsend SEND_ONCE tv KEY_MUTE

# Record IR codes if needed
irrecord -d /dev/lirc0 ~/lircd.conf
```

### Permission Issues

The container runs in privileged mode to access hardware devices. Ensure:
- Docker has permissions to access `/dev/video*` and `/dev/lirc*`
- LIRC configuration files are readable

### High CPU Usage

- Reduce `fps` in config (try 15 or 20)
- Increase frame skip rate
- Lower video resolution in capture device settings

## Logging

Logs are stored in `./logs/commute.log` and include:
- Commercial detection events with timestamps
- Mute/unmute commands sent
- Detection confidence scores
- Error messages and warnings

## Statistics

ComMute tracks operational statistics:
- Total commercials detected
- Mute/unmute commands sent
- Uptime
- Detection accuracy metrics

View stats in the logs (printed every minute).

## Project Status

### ✅ Completed (v1.0)
- [x] Video capture integration
- [x] Basic mute/unmute via IR blaster
- [x] Commercial detection logic (scene change + cut rate analysis)
- [x] Docker containerization
- [x] Logging and monitoring

### 🔄 Future Enhancements
- [ ] Audio analysis integration
- [ ] Machine learning model for detection
- [ ] Web interface for monitoring and control
- [ ] Commercial fingerprint database
- [ ] Manual override controls
- [ ] Multi-channel support
- [ ] Detection accuracy reporting dashboard

## Technical Details

### Detection Algorithm

1. **Frame Analysis**: Each frame is converted to grayscale and compared to previous frame
2. **Scene Change Detection**: Calculates pixel difference ratio above threshold
3. **Cut Rate Calculation**: Tracks scene changes per second over 5-second window
4. **Commercial Classification**: If cut rate > 2.0 cuts/second for 5+ seconds, classified as commercial
5. **Mute Trigger**: After sustained commercial detection, sends IR mute command
6. **Unmute Trigger**: When cut rate drops below threshold, sends IR unmute command

### Performance

- **Processing**: ~30 FPS on modest hardware (Raspberry Pi 4 capable)
- **Latency**: <1 second from detection to mute command
- **Memory**: ~200MB typical usage
- **CPU**: 10-30% on modern quad-core processors

## Contributing

This is a personal project, but suggestions and improvements are welcome! Open an issue or submit a pull request.

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Uses OpenCV for video processing
- LIRC for IR control
- Built with Python and Docker