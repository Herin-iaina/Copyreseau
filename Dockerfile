# Use Python 3.9 as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir numpy==1.24.3 && \
    pip install --no-cache-dir -r requirements.txt

# Copy all necessary files
COPY macos_installer_server.py .
COPY templates/ templates/

# Create necessary directories
RUN mkdir -p /data/files \
    /data/system_info \
    /data/templates \
    /data/apps

# Set environment variables
ENV BASE_DIR=/data \
    FILES_FOLDER=/data/files \
    LOG_FILE=/data/macos_installer.log \
    SERVER_PORT=5001 \
    SCAN_RESULTS_FILE=/data/scan_results.csv \
    DB_FILE=/data/system_info.db \
    SYSTEM_INFO_DIR=/data/system_info \
    TEMPLATES_DIR=/data/templates \
    APPS_DIR=/data/apps \
    PYTHONUNBUFFERED=1 \
    FLASK_ENV=production \
    FLASK_DEBUG=0 \
    PYTHONWARNINGS="ignore::DeprecationWarning:cryptography.*:"

# Expose the server port
EXPOSE 5001

# Run the server with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "4", "--timeout", "120", "--log-level", "info", "macos_installer_server:app"] 