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

# Copy only runtime code. Local secrets, test artifacts and virtualenvs never
# belong in the image, even if an ignore rule is accidentally changed.
COPY app ./app

# Require explicit production secrets; config fails closed without SECRET_KEY.
ENV ENVIRONMENT=production

# Expose port (Cloud Run will set $PORT)
ENV PORT=8080

# Run with gunicorn (same command from app.yaml)
CMD exec gunicorn -w 2 -k uvicorn_worker.UvicornWorker \
    --timeout 300 \
    --keep-alive 75 \
    --graceful-timeout 300 \
    --worker-tmp-dir /dev/shm \
    --bind :$PORT \
    app.main:app
