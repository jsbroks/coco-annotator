FROM python:3.6

WORKDIR /workspace/

# Install python package dependices
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt && \
    pip install gunicorn[eventlet]==19.9.0 && \
    pip install pycocotools

# Install maskrcnn
RUN git clone --single-branch --depth 1 https://github.com/matterport/Mask_RCNN.git /tmp/maskrcnn && \
    cd /tmp/maskrcnn && \
    pip install -r requirements.txt && \
    python3 setup.py install

# Install DEXTR
RUN git clone --single --depth 1 https://github.com/jsbroks/dextr-keras.git /tmp/dextr && \
    cd /tmp/dextr && \
    pip install -r requirements.txt && \
    python setup.py install

COPY ./.git /workspace/.git

# Create server
WORKDIR /workspace/

EXPOSE 5000
CMD gunicorn -w 1 -b 0.0.0.0:5000 app:app --worker-class eventlet --log-level debug --no-sendfile --reload
