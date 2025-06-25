# 使用Ubuntu 24.04官方镜像
FROM ubuntu:24.04

# 设置非交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 更新包列表并安装必要的系统依赖
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python3-venv \
    nginx \
    supervisor \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 创建Python软链接（如果需要python命令）
RUN ln -sf /usr/bin/python3 /usr/bin/python

# 复制requirements.txt并安装Python依赖（添加--break-system-packages参数）
COPY requirements.txt /tmp/
RUN python3 -m pip install -r /tmp/requirements.txt --break-system-packages && rm /tmp/requirements.txt

# 复制Nginx配置
COPY docker/nginx.conf /etc/nginx/nginx.conf

# 复制Supervisor配置
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# 复制应用代码
COPY ../mica /mica

# 设置工作目录
WORKDIR /mica

# 设置环境变量
ENV PYTHONPATH=/mica

# 暴露端口
EXPOSE 80 5001 7860

# 启动Supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]