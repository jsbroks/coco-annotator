# Backend environment docker image
FROM tensorflow/tensorflow:1.14.0-gpu-py3

RUN apt-get update
RUN apt-get install -y git

WORKDIR /workspace/

# Copy backend
COPY ./backend/requirements.txt /workspace/

# Install python package dependices
RUN pip install -r requirements.txt && \
    pip install gunicorn[eventlet]==19.9.0 && \
    pip install pycocotools

# Install maskrcnn
RUN git clone --single-branch --depth 1 https://github.com/matterport/Mask_RCNN.git /tmp/maskrcnn
#RUN cd /tmp/maskrcnn && pip install -r requirements.txt
RUN cd /tmp/maskrcnn && python3 setup.py install

# Install DEXTR
RUN git clone --single --depth 1 https://github.com/jsbroks/dextr-keras.git /tmp/dextr && \
    cd /tmp/dextr && \
    python setup.py install

# Install detectron
RUN echo "INSTALLING DETECTRON."
FROM pytorch/pytorch:1.9.0-cuda10.2-cudnn7-runtime
RUN apt-get update && apt-get install -y gcc libglib2.0-0
RUN python3 -m pip install detectron2 -f \
    https://dl.fbaipublicfiles.com/detectron2/wheels/cu102/torch1.9/index.html

RUN apt-get -y -o Dpkg::Options::="--force-confmiss" install --reinstall netbase
