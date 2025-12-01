# Use PyTorch 2.9.1 with CUDA 13 as base image
FROM pytorch/pytorch:2.8.0-cuda12.6-cudnn9-devel

# Set working directory
WORKDIR /app

# Copy only your source code
COPY helper /app/pbd/helper
COPY pipelines/pretrain /app/pbd/pipelines/pretrain
COPY configs /app/pbd/configs


# Install dependencies first (for better layer caching)
RUN pip install --no-cache-dir -r /app/pbd/pipelines/pretrain/requirements.txt


# Install Flash Attention
RUN pip install https://github.com/mjun0812/flash-attention-prebuild-wheels/releases/download/v0.5.4/flash_attn-2.6.3+cu124torch2.8-cp311-cp311-linux_x86_64.whl

# Install accelerate
RUN pip install accelerate

# Set env variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

# Start shell by default
CMD ["/bin/bash"]
