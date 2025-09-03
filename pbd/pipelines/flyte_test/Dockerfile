FROM python:3.10-slim

WORKDIR /app

COPY helper /app/pbd/helper
COPY pipelines/flyte_test /app/pbd/pipelines/flyte_test

RUN pip install --no-cache-dir -r /app/pbd/pipelines/flyte_test/requirements.txt

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/app"

CMD ["/bin/bash"]
