# Use the official Python slim image for a smaller footprint
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies (needed for compiling some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file first to leverage Docker cache
COPY server/requirements.txt /app/server/requirements.txt

# Install python dependencies
RUN pip install --no-cache-dir -r server/requirements.txt

# Copy the entire project (server and client)
COPY . /app/

# Expose port 8000 for FastAPI
EXPOSE 8000

# Set Python path to find modules
ENV PYTHONPATH=/app/server

# Create a non-root user and change ownership of the /app directory
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Start FastAPI using uvicorn
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]

