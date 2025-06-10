FROM python:3.10-bookworm

ENV PYTHONUNBUFFERED 1
ENV DJANGO_SETTINGS_MODULE=weather.settings

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
