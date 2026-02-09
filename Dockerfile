FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY code/ ./code/
COPY data/ ./data/

# Create data directory for SQLite
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DB_PATH=/app/data/smart_money_tracker.db

# Default command (can be overridden)
CMD ["python", "code/smart_money_monitor.py"]