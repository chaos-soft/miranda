FROM python:3.13-alpine

RUN apk -U upgrade; \
    apk add --no-cache git; \
    pip install --no-cache-dir --upgrade pip; \
    pip install --no-cache-dir --upgrade git+https://github.com/chaos-soft/miranda.git; \
