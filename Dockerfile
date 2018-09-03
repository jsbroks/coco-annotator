ARG python_version=3.6

FROM python:${python_version}

WORKDIR /workspace

ADD requirements.txt requirements.txt

RUN pip install -r requirements.txt
RUN pip install pycocotools

