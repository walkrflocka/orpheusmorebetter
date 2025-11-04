# orpheusmorebetter Docker

Docker container for [orpheusmorebetter](https://github.com/CHODEUS/orpheusmorebetter) - automatic transcode uploader for Orpheus.

This is a Docker implementation of the orpheusmorebetter script.

## Features

- Based on Python 3.11 slim image
- Includes all required dependencies (mktorrent, flac, lame, sox)
- Runs as non-root user for security
- Configurable volume mounts for data, output, and torrents

## Quick Start

### 1. Create directories

```bash
mkdir -p ~/orpheus/config
mkdir -p ~/orpheus/cache
```

### 2. Generate config file

```bash
docker run --rm \
  -v ~/orpheus/config:/config \
  yourdockerhubusername/orpheusmorebetter:latest
```

### 3. Edit configuration

Edit `~/orpheus/config/.orpheusmorebetter/config` with your Orpheus credentials and paths:

```ini
[orpheus]
username = YOUR_USERNAME
password = YOUR_PASSWORD
data_dir = /data
output_dir = /output
torrent_dir = /torrents
formats = flac, v0, 320
media = cd, vinyl, web
24bit_behaviour = 0
tracker = https://home.opsfet.ch/
api = https://orpheus.network
mode = both
source = OPS
```

### 4. Run the container

```bash
docker run --rm \
  -v ~/orpheus/config:/config \
  -v ~/orpheus/cache:/cache \
  -v /path/to/your/flac/files:/data:ro \
  -v /path/to/output:/output \
  -v /path/to/watch/folder:/torrents \
  chodeus/orpheusmorebetter:latest
```

## Usage

### Scan all snatches and uploads

```bash
docker run --rm \
  -v ~/orpheus/config:/config \
  -v ~/orpheus/cache:/cache \
  -v /path/to/flacs:/data:ro \
  -v /path/to/output:/output \
  -v /path/to/watch:/torrents \
  chodeus/orpheusmorebetter:latest
```

### Transcode a specific release

```bash
docker run --rm \
  -v ~/orpheus/config:/config \
  -v ~/orpheus/cache:/cache \
  -v /path/to/flacs:/data:ro \
  -v /path/to/output:/output \
  -v /path/to/watch:/torrents \
  chodeus/orpheusmorebetter:latest \
  "https://orpheus.network/torrents.php?id=1000&torrentid=1000000"
```

### Additional options

```bash
# Use 4 threads for transcoding
docker run --rm ... chodeus/orpheusmorebetter:latest -j 4

# Don't upload (test mode)
docker run --rm ... chodeus/orpheusmorebetter:latest -U

# With 2FA TOTP
docker run --rm ... chodeus/orpheusmorebetter:latest -t 123456
```

## Unraid Setup

### 1. Add Container in Unraid Web UI

1. Go to **Docker** tab
2. Click **Add Container**
3. Configure:

**Basic:**
- **Name**: `orpheusmorebetter`
- **Repository**: `yourdockerhubusername/orpheusmorebetter:latest`
- **Network Type**: `bridge`

**Volume Mappings:**

| Container Path | Host Path | Access Mode |
|---------------|-----------|-------------|
| `/config` | `/mnt/user/appdata/orpheusmorebetter/config` | Read/Write |
| `/cache` | `/mnt/user/appdata/orpheusmorebetter/cache` | Read/Write |
| `/data` | `/mnt/user/path/to/flacs` | Read Only |
| `/output` | `/mnt/user/path/to/output` | Read/Write |
| `/torrents` | `/mnt/user/path/to/watch` | Read/Write |

### 2. Running on Unraid

Since this is a task-based container (not a daemon), you'll run it via terminal or script:

```bash
docker exec orpheusmorebetter python -m orpheusmorebetter
```

Or create a User Script in Unraid to run it on a schedule.

## Building Locally

```bash
git clone https://github.com/yourusername/orpheusmorebetter-docker.git
cd orpheusmorebetter-docker
docker build -t orpheusmorebetter:latest .
```

## Environment Variables

- `HOME=/config` - Config directory location

## Volumes

- `/config` - Configuration files
- `/cache` - Cache files for faster subsequent runs
- `/data` - Your FLAC source files (read-only recommended)
- `/output` - Transcode output directory
- `/torrents` - Torrent watch directory

## Security Notes

- Container runs as non-root user (UID 99)
- Credentials are stored in config file - keep this volume secure
- Consider using read-only mount for source FLAC directory

## Credits

- Original script: [orpheusmorebetter](https://github.com/walkrflocka/orpheusmorebetter)
- Based on whatbetter-crawler

## License

See the [original project](https://github.com/walkrflocka/orpheusmorebetter) for license information.
