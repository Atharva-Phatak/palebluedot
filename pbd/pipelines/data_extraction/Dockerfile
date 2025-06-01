FROM huggingface/accelerate:gpu-nightly-2025-05-05

# Set workdir
WORKDIR /app

# Copy only your source code
COPY helper /app/pbd/helper
COPY pipelines/data_extraction /app/pbd/pipelines/data_extraction
COPY pipelines/data_extraction/requirements.txt /tmp/full-requirements.txt

# Strip existing packages (torch, accelerate, bitsandbytes) from requirements.txt
RUN grep -vE '^(torch|accelerate|bitsandbytes)' /tmp/full-requirements.txt > /tmp/stripped-requirements.txt && \
    pip install --no-cache-dir -r /tmp/stripped-requirements.txt

# Set env variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

# Start shell by default
CMD ["/bin/bash"]
