# 🐳 SCDL Docker Examples

This file contains practical Docker examples for using SCDL in containers.

## Quick Start

### Download Featured Track
```bash
# Pull and run in one command
docker run --rm -v $(pwd)/downloads:/downloads \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/ghostxkitty3/view-of-andromeda \
  --original-art --name-format "{artist} - {title}"
```

## Docker Compose Examples

### 1. Quick Demo
```bash
# Download the featured track
docker-compose --profile demo up
```

### 2. Interactive Session
```bash
# Start container for multiple downloads
docker-compose run --rm scdl bash

# Then inside container:
scdl -l https://soundcloud.com/ghostxkitty3/view-of-andromeda
scdl -l https://soundcloud.com/ghostxkitty3 -t
```

### 3. Batch Processing
```bash
# Create urls file
cat > batch-urls.txt << 'EOF'
https://soundcloud.com/ghostxkitty3/view-of-andromeda
https://soundcloud.com/artist2/track2
https://soundcloud.com/artist3/track3
EOF

# Process all URLs
docker-compose --profile batch up
```

### 4. Scheduled Downloads
```bash
# Add to crontab for daily downloads
0 2 * * * cd /path/to/scdl && docker-compose run --rm scdl -l https://soundcloud.com/favorite-artist -t --download-archive archive.txt
```

## Environment Variables

### Authentication
```bash
# Set your SoundCloud token
export AUTH_TOKEN=your_soundcloud_token_here

# Run with authentication
docker run --rm -v $(pwd)/downloads:/downloads \
  -e AUTH_TOKEN=$AUTH_TOKEN \
  ghcr.io/scdl-org/scdl:latest \
  me -f
```

### Custom Configuration
```bash
# Mount config directory
docker run --rm \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/config:/home/scdl/.config/scdl \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/ghostxkitty3/view-of-andromeda
```

## Advanced Examples

### 1. Archive Management
```bash
# Persistent archive across container runs
docker run --rm \
  -v $(pwd)/downloads:/downloads \
  -v $(pwd)/archive.txt:/app/archive.txt \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/ghostxkitty3 -a \
  --download-archive /app/archive.txt
```

### 2. Custom Output Format
```bash
# Download with specific naming and organization
docker run --rm \
  -v $(pwd)/music:/downloads \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/ghostxkitty3/view-of-andromeda \
  --name-format "{artist}/{album}/{track_number:02d} - {title}" \
  --original-art \
  --flac
```

### 3. Sync Playlists
```bash
# Sync a playlist daily
docker run --rm \
  -v $(pwd)/playlists:/downloads \
  -v $(pwd)/sync.txt:/app/sync.txt \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/user/sets/daily-mix \
  --sync /app/sync.txt
```

### 4. Multiple Quality Downloads
```bash
# Download both original and MP3 versions
docker run --rm -v $(pwd)/downloads:/downloads \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/ghostxkitty3/view-of-andromeda \
  --only-original \
  --name-format "{artist} - {title} [ORIGINAL]"

docker run --rm -v $(pwd)/downloads:/downloads \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/ghostxkitty3/view-of-andromeda \
  --onlymp3 \
  --name-format "{artist} - {title} [MP3]"
```

## Docker Swarm / Kubernetes

### Docker Swarm Service
```yaml
version: '3.8'
services:
  scdl-worker:
    image: ghcr.io/scdl-org/scdl:latest
    deploy:
      replicas: 2
      restart_policy:
        condition: on-failure
    volumes:
      - nfs-storage:/downloads
    environment:
      - AUTH_TOKEN=${AUTH_TOKEN}
    command: ["tail", "-f", "/dev/null"]  # Keep alive for job processing
```

### Kubernetes Job
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: scdl-download
spec:
  template:
    spec:
      containers:
      - name: scdl
        image: ghcr.io/scdl-org/scdl:latest
        command: ["scdl"]
        args: ["-l", "https://soundcloud.com/ghostxkitty3/view-of-andromeda"]
        volumeMounts:
        - name: downloads
          mountPath: /downloads
        env:
        - name: AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              name: scdl-secrets
              key: auth-token
      volumes:
      - name: downloads
        persistentVolumeClaim:
          claimName: scdl-storage
      restartPolicy: Never
```

## Performance Optimization

### 1. Parallel Downloads
```bash
# Process multiple URLs in parallel
cat urls.txt | xargs -P 4 -I {} docker run --rm \
  -v $(pwd)/downloads:/downloads \
  ghcr.io/scdl-org/scdl:latest \
  -l {} --download-archive archive.txt
```

### 2. Resource Limits
```bash
# Limit CPU and memory usage
docker run --rm \
  --cpus="1.0" \
  --memory="512m" \
  -v $(pwd)/downloads:/downloads \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/ghostxkitty3/view-of-andromeda
```

### 3. Tmpfs for Temporary Files
```bash
# Use RAM for temporary files (faster processing)
docker run --rm \
  --tmpfs /tmp:rw,size=1G \
  -v $(pwd)/downloads:/downloads \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/ghostxkitty3/view-of-andromeda
```

## Troubleshooting

### Debug Mode
```bash
# Run with debug output
docker run --rm -v $(pwd)/downloads:/downloads \
  ghcr.io/scdl-org/scdl:latest \
  -l https://soundcloud.com/ghostxkitty3/view-of-andromeda \
  --debug
```

### Shell Access
```bash
# Get shell in container for debugging
docker run -it --rm \
  -v $(pwd)/downloads:/downloads \
  ghcr.io/scdl-org/scdl:latest \
  bash
```

### Check Container Logs
```bash
# For docker-compose
docker-compose logs scdl

# For standalone container
docker logs container_name
```

## 🎵 Featured Content

All examples use the amazing track **"View of Andromeda"** by **[GhostxKitty3](https://soundcloud.com/ghostxkitty3)**! 

Perfect ambient electronic music for coding sessions. Support independent artists! 🌌

---

*Happy downloading! 🎶*
