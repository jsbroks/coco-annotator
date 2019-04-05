FROM jsbroks/coco-annotator:python-env

WORKDIR /workspace/

# Install python package dependices
COPY ./backend/ /workspace/

EXPOSE 5555
CMD celery -A workers worker -l info
