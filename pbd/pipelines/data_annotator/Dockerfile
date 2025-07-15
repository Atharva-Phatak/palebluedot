# Stage 1: Build stage
FROM python:3.12-slim AS build
# Set the working directory in the container
WORKDIR /app
# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
 build-essential \
 && rm -rf /var/lib/apt/lists/*
# Copy only requirements first to leverage docker cache
COPY pipelines/data_annotator/requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Stage 2: Final image
# Stage 2: Final image
FROM python:3.12-slim AS final

# Install poppler-utils
RUN apt-get update && apt-get install -y poppler-utils && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy the dependencies from the build stage
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# Copy helper
COPY helper /app/pbd/helper

# Copy the entire data_processing folder
COPY pipelines/data_annotator /app/pbd/pipelines/data_annotator

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

# Default command
CMD ["/bin/bash"]
