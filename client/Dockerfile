FROM node:14

RUN npm install -g --quiet \
    @vue/cli@3.12.1 \
    @vue/cli-service@3.12.1

WORKDIR /workspace/

COPY ./client/package.json /workspace/package.json
RUN npm install
ENV NODE_PATH=/workspace/node_modules

WORKDIR /workspace/client/

EXPOSE 8080
CMD npm run serve
