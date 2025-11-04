# ---- Base image ----
FROM python:3.13-alpine

# ---- Build arguments ----
ARG REPO_URL=https://github.com/CHODEUS/orpheusmorebetter.git
ARG BRANCH=main

# ---- Install system dependencies ----
RUN apk add --no-cache \
    git \
    gcc \
    musl-dev \
    linux-headers \
    mktorrent \
    flac \
    lame \
    sox

# ---- App setup ----
WORKDIR /app

# Clone the latest repo version at build time
RUN git clone --depth=1 -b ${BRANCH} ${REPO_URL} .

# Install Python dependencies & your package
RUN pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir .

# ---- Create standard Unraid folders & non-root user ----
RUN mkdir -p /config /cache /data /output /torrents \
 && adduser -D -u 99 -h /config orpheus \
 && chown -R orpheus:orpheus /app /config /cache /data /output /torrents

USER orpheus
ENV HOME=/config

# ---- Entrypoint ----
ENTRYPOINT ["python", "-m", "orpheusmorebetter"]
CMD ["--help"]
