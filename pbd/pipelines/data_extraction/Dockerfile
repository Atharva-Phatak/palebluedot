# -----------------------------
# Stage 1: Build dependencies
# -----------------------------
FROM python:3.12-slim as build

WORKDIR /build
RUN apt-get update && apt-get install -y build-essential
RUN pip install --upgrade pip
COPY pipelines/data_extraction/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# -----------------------------
# Stage 2: Runtime with CUDA
# -----------------------------
FROM nvidia/cuda:12.9.0-cudnn-runtime-ubuntu22.04

# Install Python (Ubuntu 22.04 has apt support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-venv \
    python3-distutils \
    curl \
 && ln -s /usr/bin/python3 /usr/bin/python \
 && curl -sS https://bootstrap.pypa.io/get-pip.py | python \
 && rm -rf /var/lib/apt/lists/*

COPY --from=build /install /usr/local

WORKDIR /app
COPY helper /app/pbd/helper
COPY pipelines/data_extraction /app/pbd/pipelines/data_extraction

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

CMD ["/bin/bash"]
