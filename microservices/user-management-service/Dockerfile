FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Change ownership
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables
ENV FLASK_APP=app.main:app
ENV FLASK_ENV=development
ENV PYTHONPATH=/app

# Expose port
EXPOSE 5001

# Run the application
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "app.main:app"]