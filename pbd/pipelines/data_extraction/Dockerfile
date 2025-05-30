# -----------------------------
# Stage 1: Base CUDA Runtime
# -----------------------------
FROM nvidia/cuda:12.6.3-cudnn-runtime-ubuntu22.04

# Install Python 3.10 and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3.10-venv \
    python3.10-distutils \
    curl \
 && ln -s /usr/bin/python3.10 /usr/bin/python \
 && curl -sS https://bootstrap.pypa.io/get-pip.py | python \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN pip install --upgrade pip

# Copy requirements.txt and remove any torch version to avoid overwrite
COPY pipelines/data_extraction/requirements.txt /tmp/requirements.txt

# Install remaining requirements (e.g., accelerate, transformers, etc.)
RUN pip install --no-cache-dir -r /tmp/stripped-requirements.txt

# Set up your codebase
WORKDIR /app
COPY helper /app/pbd/helper
COPY pipelines/data_extraction /app/pbd/pipelines/data_extraction

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

CMD ["/bin/bash"]
