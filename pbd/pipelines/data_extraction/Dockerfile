# -----------------------------
# Stage 1: Build dependencies
# -----------------------------
FROM python:3.12-slim as build

# Set work directory
WORKDIR /build

# Install required system packages (if any needed for builds)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
COPY pipelines/data_extraction/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# -----------------------------
# Stage 2: Runtime with CUDA
# -----------------------------
FROM nvidia/cuda:12.9.0-cudnn-runtime-ubuntu24.04

# Install Python manually (since CUDA image doesn't have Python)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3.12-distutils \
    curl \
    && ln -s /usr/bin/python3.12 /usr/bin/python3 \
    && curl -sS https://bootstrap.pypa.io/get-pip.py | python3 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=build /install /usr/local

# Set up app directory and copy code
WORKDIR /app
COPY helper /app/pbd/helper
COPY pipelines/data_extraction /app/pbd/pipelines/data_extraction

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

CMD ["/bin/bash"]
