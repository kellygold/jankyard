# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (Cloud Run will set $PORT)
ENV PORT=8080

# Run with gunicorn (same command from app.yaml)
CMD exec gunicorn -w 2 -k uvicorn.workers.UvicornWorker \
    --timeout 300 \
    --keep-alive 75 \
    --graceful-timeout 300 \
    --worker-tmp-dir /dev/shm \
    --bind :$PORT \
    app.main:app
