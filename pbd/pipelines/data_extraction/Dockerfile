# Stage 1: Build dependencies with Python
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime AS build

# Install Python 3.12 and venv
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        software-properties-common \
        curl && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3.12 \
        python3.12-venv && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12 && \
    ln -s /usr/bin/python3.12 /usr/bin/python && \
    ln -s /usr/local/bin/pip /usr/bin/pip && \
    rm -rf /var/lib/apt/lists/*

# Create and activate virtualenv
RUN python3.12 -m venv /venv
ENV PATH="/venv/bin:$PATH"

# Copy requirements and install
COPY pipelines/data_extraction/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir torch  --index-url https://download.pytorch.org/whl/cu124

# Stage 2: Final runtime image
FROM pytorch/pytorch:2.6.0-cuda12.4-cudnn9-runtime

# Install Python 3.12 again (needed to use the venv)
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        software-properties-common \
        curl && \
    add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        python3.12 \
        python3.12-venv && \
    curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12 && \
    ln -s /usr/bin/python3.12 /usr/bin/python && \
    ln -s /usr/local/bin/pip /usr/bin/pip && \
    rm -rf /var/lib/apt/lists/*

# Copy the virtualenv from build
COPY --from=build /venv /venv

# Set up workdir and app files
WORKDIR /app
COPY helper /app/pbd/helper
COPY pipelines/data_extraction /app/pbd/pipelines/data_extraction

# Use virtualenv
ENV PATH="/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

CMD ["/bin/bash"]
