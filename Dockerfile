FROM python:3.13-alpine

RUN apk add --no-cache \
    mktorrent flac lame sox git gcc musl-dev linux-headers

WORKDIR /app

# Clone and install
RUN git clone https://github.com/CHODEUS/orpheusmorebetter.git . \
 && pip install --no-cache-dir -r requirements.txt \
 && pip install --no-cache-dir .

RUN mkdir -p /config /cache /data /output /torrents \
 && adduser -D -u 99 -h /config orpheus \
 && chown -R orpheus:orpheus /app /config /cache /data /output /torrents

USER orpheus
ENV HOME=/config

ENTRYPOINT ["python", "-m", "orpheusmorebetter"]
CMD ["--help"]
