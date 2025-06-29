FROM python:3.12-slim

WORKDIR /app

# Copy only requirements first to leverage docker cache
COPY pipelines/webhooks/metaflow_webhook/requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy helper
COPY helper /app/pbd/helper

# Copy the entire data_processing folder
COPY webhooks/metaflow_webhook /app/pbd/webhooks/metaflow_webhook

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
