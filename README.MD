# ComMute - Commercial Detection & Mute System

A Docker-based application that detects and automatically mutes TV commercials in real-time using audio fingerprinting powered by Emy (soundfingerprinting.emy).

## Features

- **Real-time commercial detection** using Emy's audio fingerprinting API
- **Automatic audio muting** when commercials are detected
- **Web-based UI** accessible at http://localhost:8080
- **15-second audio recording** capability for fingerprint collection
- **Activity logging** and performance statistics
- **Configurable detection** thresholds and settings
- **Docker-based** deployment for easy setup

## Architecture

```
[Audio Input] → [Audio Capture] → [10s Buffer] → [Emy API Query] 
                                                       ↓
[System Audio] ← [Mute Control] ← [Match Detection] ←─┘
```

## Requirements

- Docker and Docker Compose
- Audio input device (HDMI audio capture, line-in, or microphone)
- Linux system with ALSA support (or macOS/Windows with appropriate audio APIs)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/CacklingCapybara/ComMute.git
cd ComMute
```

### 2. Create Directory Structure

```bash
mkdir -p recordings data fingerprints templates
```

### 3. Place Files

Ensure all files are in the correct locations:

```
ComMute/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── requirements.txt
├── app.py
├── audio_manager.py
├── fingerprint_client.py
├── mute_controller.py
├── templates/
│   └── index.html
├── recordings/          # Created automatically
├── data/               # Created automatically
└── fingerprints/       # Created automatically
```

### 4. Build and Start

```bash
# Pull the Emy Docker image
docker pull addictedcs/soundfingerprinting.emy:latest

# Build and start all containers
docker-compose up -d

# View logs
docker-compose logs -f commute
```

## Usage

### Web Interface

1. Open your browser to **http://localhost:8080**
2. Click **"Start Monitoring"** to begin detecting commercials
3. Click **"Record"** to capture 15 seconds of audio for adding to the fingerprint database

### Emy Dashboard

Access the Emy management interface at **http://localhost:3340** to:
- View stored fingerprints
- Manually add commercial tracks
- Monitor matching statistics

### Adding Commercial Fingerprints

**Method 1: Using ComMute UI**
1. Play a commercial you want to mute
2. Click the "Record" button (captures 15 seconds)
3. Use the API to add it to Emy (see API section below)

**Method 2: Using Emy Dashboard**
1. Go to http://localhost:3340
2. Upload audio files directly through the web interface
3. Add metadata (title, artist, etc.)

## Configuration

Click the settings icon in the ComMute UI to configure:

- **Audio Device**: Select input device (default, HDMI, line-in, microphone)
- **Matching Threshold**: Detection sensitivity (0.7-0.95, default 0.85)
- **Docker Endpoint**: Emy API endpoint (default: http://soundfingerprinting:3340)
- **Recording Duration**: Length of audio captures (default: 15 seconds)
- **Query Chunk Duration**: Buffer size before querying (default: 10 seconds)
- **Recording Path**: Where to save recorded audio files

## API Endpoints

### ComMute API (Port 8080)

- `GET /` - Web UI
- `GET /api/status` - Get current system status
- `POST /api/start` - Start monitoring
- `POST /api/stop` - Stop monitoring
- `POST /api/record` - Record 15 seconds of audio
- `POST /api/test-docker` - Test Emy connection
- `POST /api/clear-data` - Clear logs and statistics
- `GET /api/config` - Get configuration
- `POST /api/config` - Update configuration
- `POST /api/add-commercial` - Add recorded audio as commercial fingerprint

### Example: Add Commercial via API

```bash
curl -X POST http://localhost:8080/api/add-commercial \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "/recordings/recording_20250101_120000.wav",
    "title": "Car Commercial",
    "track_id": "commercial_car_001"
  }'
```

## Emy API Integration

ComMute uses the Emy JSON API (v1.1):

- **Authentication**: HTTP Basic Auth (Admin:)
- **Query Endpoint**: `POST /api/v1.1/tracks/query`
- **Insert Endpoint**: `POST /api/v1.1/tracks`
- **Matches Endpoint**: `GET /api/v1.1/matches`

See [Emy API Documentation](https://emysound.readme.io/reference/json-api) for details.

## Audio Device Setup

### Linux (ALSA)

List available audio devices:
```bash
arecord -l
```

Test audio capture:
```bash
arecord -d 5 -f cd test.wav
```

### Docker Audio Access

The docker-compose.yml mounts `/dev/snd` for audio device access. Ensure the Docker user has permissions:

```bash
# Add user to audio group
sudo usermod -aG audio $USER

# Check device permissions
ls -l /dev/snd/
```

## Troubleshooting

### Audio Device Not Found

**Issue**: "Failed to initialize audio"

**Solution**:
```bash
# Check if audio devices are accessible
docker exec -it commute arecord -l

# Verify device permissions
ls -l /dev/snd/
```

### Cannot Connect to Emy

**Issue**: "Connection failed - Check Docker container is running"

**Solution**:
```bash
# Check if Emy container is running
docker ps | grep soundfingerprinting

# View Emy logs
docker logs soundfingerprinting

# Test connection manually
curl http://localhost:3340/api/v1.1/tracks \
  -u Admin: \
  -H "Accept: application/json"
```

### No Commercials Detected

**Reasons**:
1. No commercial fingerprints in database
2. Threshold too high
3. Audio quality issues

**Solutions**:
- Add commercial fingerprints using the Record button
- Lower matching threshold in settings (try 0.75)
- Check audio input levels and quality

### High CPU Usage

**Solution**:
- Increase `chunk_duration` to reduce query frequency
- Ensure Emy container has sufficient resources

## Performance Metrics

- **Detection Latency**: ≤3 seconds (configurable)
- **CPU Usage**: <10% on standard hardware
- **Memory Usage**: ~200MB for ComMute, ~500MB for Emy
- **Detection Accuracy**: ≥90% with proper fingerprint database

## File Structure

```
ComMute/
├── Dockerfile                # Container build configuration
├── docker-compose.yml        # Multi-container orchestration
├── .dockerignore            # Files to exclude from build
├── requirements.txt          # Python dependencies
├── app.py                   # Flask application & API
├── audio_manager.py         # Audio capture and recording
├── fingerprint_client.py    # Emy API integration
├── mute_controller.py       # System audio mute control
├── templates/
│   └── index.html          # Web UI
├── recordings/             # Recorded audio files
├── data/                   # Application data
└── fingerprints/           # Emy fingerprint database
```

## Development

### Running Locally (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Start Emy separately
docker run -p 3340:3340 -p 3399:3399 addictedcs/soundfingerprinting.emy:latest

# Run ComMute
python app.py
```

### Environment Variables

```bash
# Override Emy endpoint
export EMY_ENDPOINT="http://localhost:3340"

# Set custom recording path
export RECORDING_PATH="/custom/path"
```

## Security Considerations

- **Default Credentials**: Emy Community Edition uses `Admin:` (empty password)
- **Network Exposure**: Only expose ports on localhost in production
- **Audio Privacy**: Recorded audio contains potentially sensitive content
- **Docker Privileges**: Container requires privileged mode for audio access

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [Emy by AddictedCS](https://emysound.com/)
- Uses [soundfingerprinting](https://github.com/AddictedCS/soundfingerprinting) audio fingerprinting library
- Inspired by commercial-skipping DVR technology

## Support

For issues and questions:
- GitHub Issues: https://github.com/CacklingCapybara/ComMute/issues
- Emy Documentation: https://emysound.readme.io/
- Product Requirements: See PRD.md in repository

## Roadmap

- [ ] Video-based commercial detection
- [ ] Machine learning enhancement
- [ ] Cloud-based fingerprint database
- [ ] Mobile app integration
- [ ] Multi-room audio support
- [ ] Smart TV integration