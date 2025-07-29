FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONPATH=/mica

# 安装必要软件
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    nginx \
    supervisor \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 设置 python 命令指向 python3
RUN ln -sf /usr/bin/python3 /usr/bin/python

# 安装 Python 依赖
COPY requirements.txt /tmp/
RUN python3 -m pip install -r /tmp/requirements.txt --break-system-packages \
    && rm /tmp/requirements.txt

# 复制 nginx 配置和 supervisor 配置
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 复制前端静态资源和后端代码
COPY docker/dist /var/www/html/chatbot
COPY mica /mica

WORKDIR /mica

# 暴露端口
EXPOSE 80 5001 7860

# 启动 supervisor 管理多个进程（如 Nginx + Python 服务）
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
