FROM node:10 as build-stage

WORKDIR /workspace/
COPY ./client /workspace/client

RUN npm install -g --quiet \
    @vue/cli@3.3.0 \
    @vue/cli-service@3.3.0

COPY ./client/package.json /workspace/package.json
RUN npm install
ENV NODE_PATH=/workspace/node_modules

WORKDIR client
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

EXPOSE 5000
CMD gunicorn -w 4 -b 0.0.0.0:5000 app:app --config app/gunicorn_config.py