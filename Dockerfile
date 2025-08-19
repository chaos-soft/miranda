FROM python:3.13-slim-bookworm

COPY requirements.txt .

RUN apt-get update; \
    pip install --no-cache-dir --upgrade pip; \
    pip install --no-cache-dir --upgrade -r requirements.txt; \
    python -m playwright install --with-deps firefox; \
    rm -rf /var/lib/apt/lists/*; \
    rm requirements.txt
