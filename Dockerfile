# Dockerfile
FROM python:3.11-slim

#Add apt-cacher-ng source
RUN echo 'Acquire::HTTP::Proxy "http://10.68.92.10:3142";' >> /etc/apt/apt.conf.d/01proxy \
 && echo 'Acquire::HTTPS::Proxy "false";' >> /etc/apt/apt.conf.d/01proxy

# Install system dependencies
RUN apt-get update && apt-get install -y \
    alsa-utils \
    portaudio19-dev \
    python3-dev \
    build-essential \
    libportaudio2 \
    libportaudiocpp0 \
    libasound2-dev \
    portaudio19-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Expose web UI port
EXPOSE 8080

# Run the application
CMD ["python", "app.py"]