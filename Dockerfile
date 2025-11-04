FROM python:3.13-alpine

# Install system dependencies
RUN apt-get update && apt-get install -y \
    mktorrent \
    flac \
    lame \
    sox \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Clone the repository from your fork
RUN git clone https://github.com/CHODEUS/orpheusmorebetter.git .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create directories for config, cache, and data
RUN mkdir -p /config /cache /data /output /torrents

# Create a non-root user (use standard UID for better compatibility)
RUN useradd -m -u 99 -U orpheus && \
    chown -R orpheus:orpheus /app /config /cache /data /output /torrents

# Switch to non-root user
USER orpheus

# Set environment variables for config locations
ENV HOME=/config

# Set the entrypoint
ENTRYPOINT ["python", "-m", "orpheusmorebetter"]
CMD ["--help"]
