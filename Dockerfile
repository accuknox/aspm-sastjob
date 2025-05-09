# syntax = docker/dockerfile:1.6

FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt-get update

COPY . .

RUN pip install -e .

CMD ["accuknox-sq-sast"]
