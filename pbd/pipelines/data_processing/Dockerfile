# Stage 1: Build stage
FROM python:3.12-slim AS build
# Set the working directory in the container
WORKDIR /app
# Install system dependencies if needed
RUN apt-get update && apt-get install -y \
 build-essential \
 && rm -rf /var/lib/apt/lists/*
# Copy only requirements first to leverage docker cache
COPY requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Stage 2: Final image
FROM python:3.12-slim AS final
# Set the working directory in the container
WORKDIR /app
# Copy the dependencies from the build stage
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
# Copy the entire data_processing folder
COPY . .
# Optional: Set environment variables if needed
ENV PYTHONUNBUFFERED=1
# Command to run bash interactively
CMD ["/bin/bash"]
