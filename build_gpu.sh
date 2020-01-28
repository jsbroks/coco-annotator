docker build -f ./backend/Dockerfile . -t jsbroks/coco-annotator:python-env --no-cache
docker build . -t annotator_webclient_gpu --no-cache
docker build -f ./backend/workers/Dockerfile . -t annotator_workers_gpu --no-cache
