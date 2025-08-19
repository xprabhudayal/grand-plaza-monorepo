# Multi-stage build for Hotel Voice AI Concierge

# Stage 1: Builder
FROM python:3.11-slim AS builder

# Install build dependencies including portaudio
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libsndfile1-dev \
    portaudio19-dev \
    libasound2-dev \
    libpulse-dev \
    ffmpeg \
    curl \
    pkg-config \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY backend/requirements-full.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-full.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Install runtime dependencies including portaudio runtime libraries
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    libportaudio2 \
    libasound2 \
    libpulse0 \
    ffmpeg \
    nginx \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app

# Copy Python dependencies from builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Switch to app user
USER app
WORKDIR /home/app

# Copy application code
COPY --chown=app:app backend/ ./backend/
COPY --chown=app:app simple-frontend/ ./frontend/

# Switch back to root to configure nginx and create directories
USER root

# Copy nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Create directory for static files and set permissions
RUN mkdir -p /var/www/html && \
    chown -R app:app /var/www/html

# Copy frontend files to nginx serving directory
COPY --chown=app:app simple-frontend/* /var/www/html/

# Create nginx log directories and set permissions
RUN mkdir -p /var/log/nginx && \
    chown -R app:app /var/log/nginx && \
    mkdir -p /var/lib/nginx && \
    chown -R app:app /var/lib/nginx

# Expose port
EXPOSE 80 8000

# Switch back to app user for runtime

USER root
CMD ["sh", "-c", "nginx && su app -c 'cd /home/app/backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000'"]