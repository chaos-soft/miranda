FROM python:3-slim

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt \
    && rm requirements.txt
