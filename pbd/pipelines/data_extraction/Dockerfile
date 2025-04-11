# Stage 1: Build stage
FROM ghcr.io/atharva-phatak/mistralrs:latest AS build

# Install Python and dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage docker cache
COPY pipelines/data_extraction/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final image
FROM ghcr.io/atharva-phatak/mistralrs:latest

# Copy your application
WORKDIR /app

# Copy the dependencies from the build stage (the build stage is now named 'build')
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy helper and other necessary files
COPY helper /app/pbd/helper
COPY pipelines/data_extraction /app/pbd/pipelines/data_extraction

# Optional: Set environment variables if needed
ENV PYTHONUNBUFFERED=1

# Set Python path
ENV PYTHONPATH="/app"

# Default command
CMD ["/bin/bash"]
