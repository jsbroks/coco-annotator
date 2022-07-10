FROM node:14 as build-stage

WORKDIR /workspace/
COPY ./client /workspace/client

RUN npm install -g @vue/cli@3.12.1
RUN npm install -g @vue/cli-service@3.12.1

COPY ./client/package* /workspace/

RUN npm install
ENV NODE_PATH=/workspace/node_modules

WORKDIR /workspace/client
RUN npm run build

FROM jsbroks/coco-annotator:python-env

RUN echo "INSTALLING DETECTRON."
RUN pip3 install torch torchvision torchaudio
RUN apt-get update && apt-get install -y gcc libglib2.0-0
RUN python -m pip install detectron2 -f \
    https://dl.fbaipublicfiles.com/detectron2/wheels/cu102/torch1.10/index.html

COPY ./backend/requirements.txt /workspace/
RUN pip install -r requirements.txt && \
    pip install gunicorn[eventlet]==19.9.0 && \
    pip install pycocotools && \
    apt update && apt install -y libsm6 libxext6 && \
    apt-get install -y libxrender-dev

RUN apt-get -y -o Dpkg::Options::="--force-confmiss" install --reinstall netbase

WORKDIR /workspace/
COPY ./backend/ /workspace/
#COPY ./.git /workspace/.git
RUN python set_path.py

COPY --from=build-stage /workspace/client/dist /workspace/dist

ENV FLASK_ENV=production
ENV DEBUG=false

EXPOSE 5000
CMD gunicorn -c webserver/gunicorn_config.py webserver:app --no-sendfile --timeout 180
