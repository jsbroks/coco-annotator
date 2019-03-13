FROM python:3.6

RUN apt-get update && \
        apt-get install -y \
        gunicorn \
        wget

WORKDIR /workspace/

# Setup flask
COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt
RUN pip install pycocotools

# Install maskrcnn
RUN git clone --single-branch --depth 1 https://github.com/matterport/Mask_RCNN.git $TEMP_MRCNN_DIR /tmp/maskrcnn && \
        cd /tmp/maskrcnn && \
        pip install -r requirements.txt && \
        python3 setup.py install

WORKDIR /models/
# Download coco model
RUN wget https://github.com/matterport/Mask_RCNN/releases/download/v2.0/mask_rcnn_coco.h5

# Create server
WORKDIR /workspace/
EXPOSE 5000
CMD python run.py