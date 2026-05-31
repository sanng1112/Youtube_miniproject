# YouTube Audiobook Pipeline - Docker Image
# ============================================

FROM python:3.11-slim

LABEL org.opencontainers.image.title="YouTube Audiobook Pipeline"
LABEL org.opencontainers.image.description="Automated audiobook production pipeline for YouTube"

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu-core \
    fonts-liberation \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/stories data/audio data/video data/thumbnails data/mukbang_library data/voice_samples

# Environment
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command: show help
CMD ["python", "-m", "orchestrator.run", "--help"]
