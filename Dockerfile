FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    lirc \
    v4l-utils \
    libopencv-dev \
    python3-opencv \
    ffmpeg \
    usbutils \
    alsa-utils \
    portaudio19-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Dejavu from GitHub (Python 3 compatible)
RUN pip install --no-cache-dir git+https://github.com/worldveil/dejavu.git#egg=PyDejavu

# Copy application files
COPY commute.py .
COPY config/ config/

# Create necessary directories
RUN mkdir -p /app/logs /app/config /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port for optional web interface (future)
EXPOSE 8080

# Run the application
CMD ["python", "commute.py"]