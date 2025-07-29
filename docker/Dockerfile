FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/mica

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    nginx \
    supervisor \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/bin/python3 /usr/bin/python

COPY requirements.txt /tmp/
RUN python3 -m pip install -r /tmp/requirements.txt --break-system-packages \
    && rm /tmp/requirements.txt

COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY docker/dist /var/www/html/chatbot
COPY mica /mica

RUN mkdir /mica/logs

WORKDIR /mica

EXPOSE 80 5001 7860

CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
