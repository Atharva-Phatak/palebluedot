# Based on the official mistral.rs Dockerfile.cuda
FROM nvidia/cuda:12.4.1-cudnn-devel-ubuntu22.04 AS builder

# Install essential dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install Rust (nightly)
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup update nightly
RUN rustup default nightly

# Set CUDA compute capability (change as needed for your GPU)
ARG CUDA_COMPUTE_CAP=80
ENV CUDA_COMPUTE_CAP=${CUDA_COMPUTE_CAP}

# Set CUDA paths
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="$CUDA_HOME/bin:$PATH"
ENV LD_LIBRARY_PATH="$CUDA_HOME/lib64:$LD_LIBRARY_PATH"
ENV RAYON_NUM_THREADS=4

# Clone mistral.rs repo
WORKDIR /build
RUN git clone https://github.com/EricLBuehler/mistral.rs.git
WORKDIR /build/mistral.rs

# Install maturin with patchelf for Python bindings
RUN pip install maturin[patchelf]

# Build Python bindings with CUDA and cuDNN support
WORKDIR /build/mistral.rs/mistralrs-pyo3
RUN RUSTFLAGS="-Z threads=4" maturin build --release --features "cuda"

# Create lightweight runtime image
FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

# Set environment variables
ENV HUGGINGFACE_HUB_CACHE=/data \
    PORT=80 \
    RAYON_NUM_THREADS=8 \
    LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH

# Create symlinks for CUDA libraries
RUN set -eux; \
    for lib in $(ls /usr/local/cuda/lib64); do \
        base=$(echo $lib | sed -r 's/(.+)\.so\..+/\1.so/'); \
        if [ "$lib" != "$base" ]; then \
            ln -sf "/usr/local/cuda/lib64/$lib" "/usr/local/cuda/lib64/$base"; \
        fi; \
    done

# Install runtime dependencies
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    libomp-dev \
    ca-certificates \
    libssl-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

# Create a Python virtual environment
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy and install the wheel from builder
COPY --from=builder /build/mistral.rs/target/wheels/*.whl /tmp/
RUN pip install /tmp/*.whl && rm /tmp/*.whl

# Create a simple test script
RUN echo 'import mistralrs; print("MistralRS successfully installed!")' > /test_install.py

# Test the installation
RUN python /test_install.py

# Set working directory
WORKDIR /app

# Default command
CMD ["/bin/bash"]s