#  docker build -t jobhunter && docker run --rm -it jobhunter

FROM python:3.9


WORKDIR /app
COPY . /app

RUN pip install -e .