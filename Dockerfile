FROM node:10 as build-stage

WORKDIR /workspace/
COPY ./client /workspace/client

# fails with http://registry.npmjs.org
RUN npm config set registry http://skimdb.npmjs.com/registry
RUN npm install -g @vue/cli@3.3.0
RUN npm install -g @vue/cli-service@3.3.0

COPY ./client/package* /workspace/

# npm install will fail with http://skimdb.npmjs.com/registry on paper@0.11.8
RUN npm config set registry https://registry.npm.taobao.org
RUN npm install -g paper@0.11.8
RUN npm config set registry http://skimdb.npmjs.com/registry

RUN npm install
ENV NODE_PATH=/workspace/node_modules

WORKDIR /workspace/client
RUN npm run build

RUN npm config set registry http://registry.npmjs.org

FROM jsbroks/coco-annotator:python-env

WORKDIR /workspace/
COPY ./backend/ /workspace/
COPY ./.git /workspace/.git
RUN python set_path.py

COPY --from=build-stage /workspace/client/dist /workspace/dist

ENV FLASK_ENV=production
ENV DEBUG=false

EXPOSE 5000
CMD gunicorn -c webserver/gunicorn_config.py webserver:app --no-sendfile --timeout 180
