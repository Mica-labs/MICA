#!/bin/bash

echo "开始构建静态版本..."

ROOT=$(pwd)

# 检查是否在项目根目录
if [ ! -f "package.json" ]; then
    echo "错误：请在项目根目录运行此脚本"
    exit 1
fi

# 安装依赖
echo "安装依赖..."
pnpm install

# 1. 构建SDK
echo "构建SDK..."
pnpm --filter sdk build

if [ ! -f "${ROOT}/packages/sdk/build/sdk.js" ]; then
    echo "错误：SDK 构建失败"
    exit 1
fi

# 2. 将SDK复制到ava的public目录
echo "复制SDK到ava..."
mkdir -p ${ROOT}/packages/ava/public/static/js
cp ${ROOT}/packages/sdk/build/sdk.js ${ROOT}/packages/ava/public/static/js/

# 3. 构建ava
echo "构建ava..."
pnpm --filter ava build

if [ ! -d "${ROOT}/packages/ava/build" ]; then
    echo "错误：ava 构建失败"
    exit 1
fi

# 4. 创建最终的部署目录
echo "创建部署目录..."
rm -rf ${ROOT}/dist
mkdir -p ${ROOT}/dist
cp -R ${ROOT}/packages/ava/build/* ${ROOT}/dist/

# 5. 确保SDK文件在正确位置
mkdir -p ${ROOT}/dist/static/js
cp ${ROOT}/packages/sdk/build/sdk.js ${ROOT}/dist/static/js/

# 6. 创建部署信息文件
echo "创建部署信息..."
cat > ${ROOT}/dist/deploy-info.json << EOF
{
  "buildTime": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
  "version": "static",
  "components": {
    "sdk": "$(cd packages/sdk && npm version --json | jq -r '.sdk // "unknown"')",
    "ava": "$(cd packages/ava && npm version --json | jq -r '.ava // "unknown"')"
  }
}
EOF

# 7. 复制到Docker部署目录
echo "复制到Docker部署目录..."
DOCKER_DIST_DIR="${ROOT}/../../../docker/dist"
mkdir -p "$(dirname "$DOCKER_DIST_DIR")"
rm -rf "$DOCKER_DIST_DIR"
cp -R ${ROOT}/dist "$DOCKER_DIST_DIR"

echo "✅ 静态构建完成！"
echo "📁 部署文件在 ./dist 目录中"
echo "📁 Docker部署文件已复制到 docker/dist 目录"
echo "🚀 可以直接将 dist 目录部署到任何静态服务器"
echo ""
echo "部署方式示例："
echo "  - Nginx: 将 dist 目录内容复制到 web 根目录"
echo "  - Apache: 将 dist 目录内容复制到 htdocs"
echo "  - CDN: 上传 dist 目录到对象存储"
echo "  - GitHub Pages: 推送 dist 内容到 gh-pages 分支"
echo "  - Docker: 使用 docker build 构建包含chatbot前端的镜像"