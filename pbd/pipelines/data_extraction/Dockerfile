# Stage 1: Build dependencies with Python
FROM nvidia/cuda:12.9.0-cudnn-runtime-ubuntu24.04 AS build

# Install Python 3.12 and venv
# Upgrade pip
RUN pip install --upgrade pip

# Copy and install project requirements
COPY pipelines/data_extraction/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# Stage 2: Final runtime image
FROM nvidia/cuda:12.9.0-cudnn-runtime-ubuntu24.04


# Copy the virtualenv from build
COPY --from=build /opt/conda /opt/conda

# Set up workdir and app files
WORKDIR /app
COPY helper /app/pbd/helper
COPY pipelines/data_extraction /app/pbd/pipelines/data_extraction

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

CMD ["/bin/bash"]
