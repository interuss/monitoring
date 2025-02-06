# Dockerfile to apply isort
#
# `docker build` should be run from this folder

FROM python:3.8
ADD ./requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt
RUN rm -rf __pycache__
ADD . /app
WORKDIR /app

ENTRYPOINT ["isort"]
