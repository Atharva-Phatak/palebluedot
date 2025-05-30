# -----------------------------
# Stage 1: Base CUDA Runtime
# -----------------------------
FROM nvidia/cuda:12.8.0-cudnn-runtime-ubuntu22.04

# Install Python 3.11 and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-distutils \
    curl \
    gcc \
    g++ \
    make \
    build-essential \
 && ln -s /usr/bin/python3.11 /usr/bin/python \
 && curl -sS https://bootstrap.pypa.io/get-pip.py | python \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements.txt
COPY pipelines/data_extraction/requirements.txt /tmp/requirements.txt

# Install remaining requirements (e.g., accelerate, transformers, etc.)
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Set up your codebase
WORKDIR /app
COPY helper /app/pbd/helper
COPY pipelines/data_extraction /app/pbd/pipelines/data_extraction

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

CMD ["/bin/bash"]
