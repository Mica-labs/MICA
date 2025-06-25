#!/bin/bash


# 定义镜像名称和标签
IMAGE="registry.cn-chengdu.aliyuncs.com/zpcloud/zbot-aichat:local"

# 构建 Docker 镜像
echo "正在构建镜像: $IMAGE"
if docker build -t "$IMAGE" -f docker/Dockerfile .; then
    echo "镜像构建成功: $IMAGE"
else
    echo "镜像构建失败，请检查 Dockerfile 和构建环境"
    exit 1
fi

# 停止并删除已存在的容器
if docker ps -a --format '{{.Names}}' | grep -q '^chat$'; then
    echo "正在停止并删除已存在的容器: chat"
    docker rm -f chat
fi

# 启动新的容器
echo "正在启动新容器: chat  "$IMAGE""
if docker run -d -v /Users/chenchen/IdeaProjects/MICA/logs:/mica/logs -v /Users/chenchen/IdeaProjects/MICA/bots:/mica/deployed_bots -p 5001:5001 -p 80:80 -p 7860:7860 --name chat $IMAGE; then
    echo "容器启动成功: chat"
else
    echo "容器启动失败，请检查镜像或运行参数"
    exit 1
fi

# 实时查看容器日志
echo "正在查看容器日志: chat"
docker logs -f chat