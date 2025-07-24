FROM pytorch/pytorch:2.7.1-cuda12.6-cudnn9-devel

# Set workdir
WORKDIR /app

# Copy only your source code
COPY helper /app/pbd/helper
COPY pipelines/ocr /app/pbd/pipelines/ocr

# Install from the copied location
RUN pip install --no-cache-dir -r /app/pbd/pipelines/ocr/requirements.txt


# Set env variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

# Start shell by default
CMD ["/bin/bash"]
