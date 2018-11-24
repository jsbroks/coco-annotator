FROM node:9.11 as build-stage

WORKDIR /workspace/

COPY ./client /workspace/client

WORKDIR client

RUN apt-get -y update \
	&& apt-get install -y \
	    git

RUN npm install -g --quiet \
    @vue/cli@3.1.1 \
    @vue/cli-service@3.1.2

RUN npm i
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
