# syntax=docker/dockerfile:1
#
# Targets:
#   webserver  (default)  Flask API + built web client
#   workers               Celery worker (scans, imports, exports, thumbnails)
#
# Build args:
#   SAM=none|cpu|cuda     install PyTorch, Segment Anything and Ultralytics
#                         (SAM tool and pre-annotation with your YOLO models)
#   MEDIAPIPE=1|0         MediaPipe pre-annotation models (webserver; default on)
#   VERSION               version string shown in the UI

############################ web client ############################
# Base images are pinned by digest: when the "22-alpine" / "3.12-slim" tags move
# upstream, an unpinned FROM makes Docker rebuild every layer after it (all
# pip installs, PyTorch included). Bump these on purpose, e.g. with
#   docker pull python:3.12-slim && docker inspect --format '{{index .RepoDigests 0}}' python:3.12-slim
FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS client
WORKDIR /workspace/client
COPY client/package.json client/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY client/ ./
RUN npm run build

############################ python base ###########################
FROM python:3.12-slim@sha256:05cda9777409a9c3ffddd94a4c476b79f0769a0b4857f0c7ed9226b6800b0d6f AS python-base
ARG SAM=none
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PYTHONPATH=/workspace
WORKDIR /workspace

RUN apt-get update \
 && apt-get install -y --no-install-recommends libglib2.0-0 libgomp1 \
 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-sam.txt ./
RUN pip install -r requirements.txt
# ultralytics pulls in the GUI build of OpenCV (needs libGL); keep only the
# headless one, which provides the same cv2 module.
RUN if [ "$SAM" = "cpu" ]; then \
      pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision \
      && pip install -r requirements-sam.txt; \
    elif [ "$SAM" = "cuda" ]; then \
      pip install -r requirements-sam.txt; \
    fi \
 && if [ "$SAM" != "none" ]; then \
      pip uninstall -y opencv-python opencv-python-headless \
      && pip install "opencv-python-headless==4.*"; \
    fi
# Ultralytics settings/cache in a writable place, no online checks
ENV YOLO_CONFIG_DIR=/tmp/Ultralytics YOLO_OFFLINE=1
# (Ultralytics checks a subfolder it does not create: make it, no warning at start)
RUN mkdir -p /tmp/Ultralytics/Ultralytics

############################ workers ###############################
FROM python-base AS workers
COPY backend/ /workspace/
CMD ["celery", "-A", "workers", "worker", "-l", "info"]

############################ webserver #############################
FROM python-base AS webserver
# MediaPipe models for pre-annotation (MEDIAPIPE=0 leaves them out). It pulls
# in the GUI build of OpenCV: swapped for the headless one, as above.
ARG MEDIAPIPE=1
COPY backend/requirements-mediapipe.txt ./
RUN if [ "$MEDIAPIPE" = "1" ]; then \
      apt-get update \
      && apt-get install -y --no-install-recommends libegl1 libgles2 \
      && rm -rf /var/lib/apt/lists/* \
      && pip install -r requirements-mediapipe.txt \
      && pip uninstall -y opencv-contrib-python opencv-python opencv-python-headless \
      && pip install "opencv-python-headless==4.*"; \
    fi
ARG VERSION=v1.0.0
ENV VERSION=${VERSION} DEBUG=false
COPY backend/ /workspace/
COPY --from=client /workspace/client/dist /workspace/dist
EXPOSE 5000
CMD ["gunicorn", "-c", "webserver/gunicorn_config.py", "webserver:app", "--no-sendfile"]
