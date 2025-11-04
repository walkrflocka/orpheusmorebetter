FROM python:3.13-alpine

# Install system and Python dependencies
RUN apk add --no-cache \
    git \
    gcc \
    musl-dev \
    linux-headers \
    mktorrent \
    flac \
    lame \
    sox \
    py3-lxml \
    py3-packaging \
    py3-pip

WORKDIR /app

# Copy your repo into the container
COPY . /app

# Install Python dependencies and your package
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir .

# Optional build-time metadata
ARG VERSION=dev
ARG GIT_BRANCH=main
RUN echo "v${VERSION}" > /app/version.txt \
 && echo "${GIT_BRANCH}" > /app/branch.txt

# Create required directories and user for Unraid
RUN mkdir -p /config /cache /data /output /torrents \
 && adduser -D -u 99 -h /config orpheus \
 && chown -R orpheus:orpheus /app /config /cache /data /output /torrents

# Copy in the startup script
COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

USER orpheus
ENV HOME=/config

# Use the startup script as the entrypoint
ENTRYPOINT ["/usr/local/bin/start.sh"]
