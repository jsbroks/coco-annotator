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

FROM python:3.6 as production-stage

RUN apt-get update && \
        apt-get install -y \
        wget \
        nano

WORKDIR /workspace

COPY --from=build-stage /workspace/client/dist /workspace/dist

# Setup flask
COPY requirements.txt requirements.txt

RUN pip install gunicorn
RUN pip install -r requirements.txt
RUN pip install pycocotools

COPY ./.git .git/
COPY ./app app/

EXPOSE 5000
CMD gunicorn -w 4 -b 0.0.0.0:5000 app:app --config app/gunicorn_config.py --log-level debug
