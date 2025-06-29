FROM python:3.12-slim

WORKDIR /app

# Copy only requirements first to leverage docker cache
COPY webhooks/metaflow_webhook/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Ensure uvicorn is installed (in case it's not in requirements.txt)
RUN pip install --no-cache-dir uvicorn

# Create the package structure
RUN mkdir -p pbd/webhooks/metaflow_webhook pbd/helper

# Create __init__.py files for Python packages
RUN touch pbd/__init__.py pbd/webhooks/__init__.py pbd/webhooks/metaflow_webhook/__init__.py

# Copy helper
COPY helper /app/pbd/helper

# Copy the entire metaflow_webhook folder
COPY webhooks/metaflow_webhook /app/pbd/webhooks/metaflow_webhook

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

EXPOSE 8000

# Run with uvicorn instead of fastapi-cli for better reliability
CMD ["uvicorn", "pbd.webhooks.metaflow_webhook.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
