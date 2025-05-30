# Use Python 3.9 as base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the server code
COPY macos_installer_server.py .

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
    APPS_DIR=/data/apps

# Expose the server port
EXPOSE 5001

# Run the server
CMD ["python", "macos_installer_server.py"] 