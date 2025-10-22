FROM mcr.microsoft.com/dotnet/sdk:8.0 AS build
WORKDIR /src

# Copy project file and restore dependencies
COPY FingerprintService.csproj .
RUN dotnet restore

# Copy source code and build
COPY . .
RUN dotnet build -c Release -o /app/build

FROM build AS publish
RUN dotnet publish -c Release -o /app/publish

# Runtime image
FROM mcr.microsoft.com/dotnet/aspnet:8.0
WORKDIR /app

# Install ffmpeg for audio processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download and install BASS library (required by SoundFingerprinting.Audio.Bass)
RUN wget http://www.un4seen.com/files/bass24-linux.zip && \
    apt-get update && apt-get install -y unzip && \
    unzip bass24-linux.zip && \
    cp bass/x64/libbass.so /usr/lib/ && \
    rm -rf bass24-linux.zip bass && \
    apt-get remove -y unzip wget && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*

COPY --from=publish /app/publish .

EXPOSE 5000

ENTRYPOINT ["dotnet", "FingerprintService.dll"]