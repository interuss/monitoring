# Dockerfile to expose pip-tools using the Python version the project relies on

FROM python:3.11-slim

RUN apt-get update && apt-get install -y openssl curl libgeos-dev gcc && apt-get install ca-certificates

# required for pip-compile to work with our dependencies (at least on an ARM environment)
RUN apt-get update && apt-get install -y libxml2-dev libxslt-dev

RUN pip install pip-tools
