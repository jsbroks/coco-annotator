FROM node:9.11

RUN apt-get -y update \
	&& apt-get install -y git

RUN npm install -g --quiet \
    @vue/cli@3.1.1 \
    @vue/cli-service@3.1.2

WORKDIR /workspace/


COPY ./client/package.json /workspace/package.json
RUN npm install
ENV NODE_PATH=/workspace/node_modules

WORKDIR client/