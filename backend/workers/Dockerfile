FROM python:3.6

WORKDIR /workspace/

# Install python package dependices
COPY ./backend/ /workspace/
COPY ./.git /workspace/.git

RUN pip install -r requirements.txt


EXPOSE 5000
CMD celery -A workers -l info
