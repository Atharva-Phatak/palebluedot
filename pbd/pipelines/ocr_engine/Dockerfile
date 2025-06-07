FROM pytorch/pytorch:2.7.0-cuda12.6-cudnn9-devel

# Set workdir
WORKDIR /app

# Copy only your source code
COPY pbd/helper /app/pbd/helper
COPY pbd/pipelines/ocr_engine /app/pbd/pipelines/ocr_engine

# Install from the copied location
RUN pip install --no-cache-dir -r /app/pbd/pipelines/ocr_engine/requirements.txt


# Set env variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

# Start shell by default
CMD ["/bin/bash"]
