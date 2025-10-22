# Hybrid Architecture Guide

ComMute uses a hybrid architecture combining Python and .NET for optimal performance and functionality.

## Architecture Overview

```
┌─────────────────────────────────────────────┐
│         ComMute (Python Container)          │
│                                             │
│  ┌─────────────┐      ┌─────────────┐     │
│  │   Video     │      │    Audio    │     │
│  │ Processing  │      │  Capture    │     │
│  │  (OpenCV)   │      │  (FFmpeg)   │     │
│  └─────────────┘      └─────────────┘     │
│         │                     │            │
│         └──────────┬──────────┘            │
│                    │                       │
│         ┌──────────▼──────────┐            │
│         │  Detection Engine   │            │
│         │  - Scene Changes    │            │
│         │  - Cut Rate         │            │
│         └──────────┬──────────┘            │
│                    │                       │
│         HTTP POST  │                       │
└────────────────────┼───────────────────────┘
                     │ (Audio Samples)
                     ▼
┌─────────────────────────────────────────────┐
│   Fingerprint Service (.NET Container)      │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │    SoundFingerprinting Library       │  │
│  │                                      │  │
│  │  ┌────────────┐   ┌──────────────┐ │  │
│  │  │ Fingerprint│   │   In-Memory  │ │  │
│  │  │  Generator │   │   Database   │ │  │
│  │  └────────────┘   └──────────────┘ │  │
│  │                                      │  │
│  │  ┌────────────┐   ┌──────────────┐ │  │
│  │  │   Query    │   │    Match     │ │  │
│  │  │   Engine   │   │   Results    │ │  │
│  │  └────────────┘   └──────────────┘ │  │
│  └──────────────────────────────────────┘  │
│                                             │
│         REST API (Port 5000)                │
└─────────────────────────────────────────────┘
                     │
                     ▼
              Match Result
              (JSON Response)
```

## Why Hybrid?

### Python Side (ComMute)
**Strengths:**
- Excellent for video processing (OpenCV)
- Simple hardware interfacing (ALSA, V4L2, LIRC)
- Easy to prototype and modify
- Great for system integration

**Handles:**
- Video capture and scene analysis
- Audio capture from HDMI
- IR blaster control
- Overall orchestration

### .NET Side (Fingerprint Service)
**Strengths:**
- SoundFingerprinting is production-grade
- Specifically designed for broadcast ad detection
- High performance audio processing
- Battle-tested by radio stations

**Handles:**
- Audio fingerprint generation
- Fingerprint database management
- Audio matching queries
- Commercial recognition

## Communication Flow

1. **ComMute captures audio** from HDMI device (FFmpeg → PCM data)
2. **Buffers 3 seconds** of audio samples
3. **Converts to WAV** file format
4. **HTTP POST** to fingerprint service at `/query`
5. **Fingerprint service processes** audio and checks database
6. **Returns JSON** with match result and confidence
7. **ComMute updates** commercial probability
8. **Triggers mute** if threshold exceeded

## API Endpoints

The fingerprint service exposes these endpoints:

### Health Check
```
GET /health
Response: { "status": "healthy", "service": "fingerprint" }
```

### Fingerprint Commercial
```
POST /fingerprint
Form Data:
  - file: audio file (WAV, MP3, etc.)
  - name: commercial name
Response: {
  "success": true,
  "name": "Geico Insurance",
  "trackId": "abc-123",
  "hashesCount": 1234
}
```

### Query Audio
```
POST /query
Form Data:
  - file: audio file to match
  - seconds: how many seconds to analyze (default: 10)
Response: {
  "match": true,
  "name": "Progressive Commercial",
  "confidence": 0.85,
  "matchedAt": 5.2,
  "queryLength": 3.0
}
```

### List Commercials
```
GET /commercials
Response: {
  "count": 15,
  "commercials": [
    { "id": "abc-123", "name": "Geico", "artist": "Commercial" }
  ]
}
```

### Statistics
```
GET /stats
Response: {
  "totalCommercials": 15,
  "service": "SoundFingerprinting",
  "storage": "InMemory"
}
```

## Project Structure

```
ComMute/
├── commute.py              # Python main application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Python container
├── config/
│   └── config.json        # Configuration
├── logs/                  # Application logs
├── FingerprintService/
│   ├── Program.cs         # .NET API service
│   ├── FingerprintService.csproj
│   └── Dockerfile         # .NET container
└── docker-compose.yml     # Orchestration
```

## Building and Running

### Build Both Services
```bash
# Build everything
docker-compose build

# Or build individually
docker-compose build fingerprint
docker-compose build commute
```

### Start Services
```bash
# Start both containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Verify Communication
```bash
# Check fingerprint service
curl http://localhost:5000/health

# Check from inside ComMute container
docker exec commute curl http://fingerprint:5000/health
```

## Development Workflow

### Modifying Python Code
1. Edit `commute.py`
2. Rebuild: `docker-compose build commute`
3. Restart: `docker-compose restart commute`

### Modifying .NET Code
1. Edit `FingerprintService/Program.cs`
2. Rebuild: `docker-compose build fingerprint`
3. Restart: `docker-compose restart fingerprint`

### Testing Fingerprinting
```bash
# Record audio
arecord -D hw:1,0 -f S16_LE -r 44100 -c 1 -d 30 test.wav

# Copy to container
docker cp test.wav commute:/tmp/

# Fingerprint it
docker exec commute python commute.py \
  --fingerprint /tmp/test.wav \
  --name "Test Commercial"

# Verify it was added
curl http://localhost:5000/commercials
```

## Troubleshooting

### Fingerprint Service Won't Start

Check .NET runtime:
```bash
docker-compose logs fingerprint
```

Common issues:
- Missing audio libraries (BASS)
- Port 5000 already in use
- Insufficient memory

### ComMute Can't Reach Fingerprint Service

Verify network:
```bash
docker exec commute ping fingerprint
docker exec commute curl http://fingerprint:5000/health
```

Check docker-compose network configuration.

### Audio Files Won't Fingerprint

Supported formats:
- WAV (recommended)
- MP3
- FLAC
- OGG

Convert if needed:
```bash
ffmpeg -i input.mp4 -vn -acodec pcm_s16le -ar 44100 -ac 1 output.wav
```

## Performance Tuning

### Reduce CPU Usage

**Python side:**
- Lower FPS: `"fps": 15`
- Increase audio check interval: `"audio_check_interval": 5`

**.NET side:**
- Runs efficiently by default
- In-memory storage is fast

### Memory Management

**In-Memory Limits:**
- ~100 hours of content = ~5GB RAM
- For 50 commercials @ 30 seconds each = ~50MB

To monitor:
```bash
docker stats
```

## Production Considerations

### Persistent Storage

In-memory storage is lost on restart. For production:

1. **Option 1:** Implement database persistence in .NET service
2. **Option 2:** Export/import fingerprints via API
3. **Option 3:** Use Emy storage (commercial option from SoundFingerprinting)

### Scaling

Single instance is sufficient for one TV, but for multiple:
- Run multiple ComMute instances
- Share one fingerprint service
- Or run dedicated fingerprint service per instance

### Monitoring

Add health checks:
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
```

## Benefits of This Architecture

✅ **Best-in-class libraries**: Python for video, .NET for audio
✅ **Separation of concerns**: Each service does what it's best at
✅ **Maintainability**: Update services independently
✅ **Performance**: Optimized for each task
✅ **Scalability**: Services can be scaled separately
✅ **Technology flexibility**: Use the right tool for each job

## Limitations

⚠️ **In-memory storage**: Fingerprints lost on restart (can be mitigated)
⚠️ **Additional container**: Slightly more complex than monolithic
⚠️ **Network overhead**: Small latency for API calls (negligible)

## Future Enhancements

- Persistent storage backend for fingerprints
- Fingerprint sharing/marketplace
- Real-time streaming recognition
- Multi-channel support
- Cloud deployment options