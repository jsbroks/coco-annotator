FROM node:10 as build-stage

WORKDIR /workspace/
COPY ./client /workspace/client

RUN npm install -g --quiet \
        @vue/cli@3.3.0 \
        @vue/cli-service@3.3.0

COPY ./client/package* /workspace/

RUN npm install
ENV NODE_PATH=/workspace/node_modules

WORKDIR /workspace/client
RUN npm run build

# Setup flask

FROM python:3.6

WORKDIR /workspace/

# Install python package dependices
COPY ./backend/ /workspace/
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
RUN python set_path.py

COPY --from=build-stage /workspace/client/dist /workspace/dist

ENV FLASK_ENV=production
ENV DEBUG=false

EXPOSE 5000
CMD gunicorn -c webserver/gunicorn_config.py webserver:app --no-sendfile --timeout 180

