FROM node:10

RUN apt-get -y update \
	&& apt-get install -y git

RUN npm install -g --quiet \
    @vue/cli@3.3.0 \
    @vue/cli-service@3.3.0

WORKDIR /workspace/

COPY ./client/package.json /workspace/package.json
RUN npm install
ENV NODE_PATH=/workspace/node_modules

WORKDIR client/

EXPOSE 8080
CMD npm run serve