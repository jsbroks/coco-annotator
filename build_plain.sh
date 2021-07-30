#!/bin/bash
if [[ "$1" == regi* ]];then

docker build -t docker-registry.it.csiro.au/trike/uwer/coco-annotator:python-env -f ./backend/Dockerfile .
docker build -t docker-registry.it.csiro.au/trike/uwer/annotator_webclient -f Dockerfile .
docker build -t docker-registry.it.csiro.au/trike/uwer/annotator_workers -f ./backend/workers/Dockerfile .

docker push docker-registry.it.csiro.au/trike/uwer/coco-annotator:python-env
docker push docker-registry.it.csiro.au/trike/uwer/annotator_webclient
docker push docker-registry.it.csiro.au/trike/uwer/annotator_workers
else
docker build -f ./backend/Dockerfile . -t uwer/coco-annotator:python-env 
docker build . -t uwer/annotator_webclient --no-cache
docker build -f ./backend/workers/Dockerfile . -t uwer/annotator_workers 

fi 