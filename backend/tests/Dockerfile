# Runs the backend test-suite. No MongoDB / RabbitMQ needed: tests use an
# in-memory database and execute Celery tasks eagerly (see tests/conftest.py).
FROM python:3.12-slim
WORKDIR /workspace
RUN apt-get update && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
 && rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt mongomock
COPY backend/ /workspace/
CMD ["pytest", "-q"]
