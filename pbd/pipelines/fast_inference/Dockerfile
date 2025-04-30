# -------- Stage 1: Build stage --------
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04 AS builder

# Install Python 3.12, Rust, and build dependencies
RUN apt-get update && apt-get install -y \
        software-properties-common \
        curl \
        git \
        build-essential \
        python3.12 \
        python3.12-venv \
        python3-pip \
        libssl-dev \
        pkg-config \
        && rm -rf /var/lib/apt/lists/*
    
# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1
    
# Install Rust
RUN curl https://sh.rustup.rs -sSf | bash -s -- -y
ENV PATH="/root/.cargo/bin:$PATH"
    
# Install maturin with patchelf for building Python bindings
RUN pip install maturin[patchelf]
    
# Clone mistral.rs repo and build with CUDA
WORKDIR /build
RUN git clone https://github.com/EricLBuehler/mistral.rs.git
WORKDIR /build/mistral.rs/mistralrs-pyo3
    
# Build wheel with CUDA support
RUN maturin build --release --features "cuda"
    
# -------- Stage 2: Runtime stage --------
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04
    
# Install Python 3.12 and minimal dependencies
RUN apt-get update && apt-get install -y \
        software-properties-common \
        python3.12 \
        python3-pip \
        && rm -rf /var/lib/apt/lists/*
    
# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1
    
# Copy built wheel from builder stage
COPY --from=builder /build/mistral.rs/mistralrs-pyo3/target/wheels/*.whl /tmp/mistralrs_cuda.whl
    
# Install the wheel
RUN pip install /tmp/mistralrs_cuda.whl && rm /tmp/mistralrs_cuda.whl


# Copy helper
COPY helper /app/pbd/helper

# Copy the entire data_processing folder
COPY pipelines/fast_inference /app/pbd/pipelines/fast_inference

# Create working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"
    
# Default command
CMD ["/bin/bash"]
    