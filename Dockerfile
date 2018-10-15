ARG python_version=3.6

FROM python:${python_version}

RUN apt-get update && \
    apt-get install -y \
        gunicorn

WORKDIR /workspace

# Setup flask
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt
RUN pip install pycocotools