#!/bin/bash

echo "Starting static build..."

ROOT=$(pwd)

# Check if in project root
if [ ! -f "package.json" ]; then
    echo "Error: Please run from the project root"
    exit 1
fi

# Install dependencies
pnpm install

# Build SDK
pnpm --filter sdk build
if [ ! -f "${ROOT}/packages/sdk/build/sdk.js" ]; then
    echo "Error: SDK build failed"
    exit 1
fi

# Copy SDK to ava public directory
mkdir -p ${ROOT}/packages/ava/public/static/js
cp ${ROOT}/packages/sdk/build/sdk.js ${ROOT}/packages/ava/public/static/js/

# Build ava
pnpm --filter ava build
if [ ! -d "${ROOT}/packages/ava/build" ]; then
    echo "Error: ava build failed"
    exit 1
fi

# Create dist directory
rm -rf ${ROOT}/dist
mkdir -p ${ROOT}/dist
cp -R ${ROOT}/packages/ava/build/* ${ROOT}/dist/

# Place SDK in dist
mkdir -p ${ROOT}/dist/static/js
cp ${ROOT}/packages/sdk/build/sdk.js ${ROOT}/dist/static/js/

# Generate deploy info
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

# Copy to Docker dist directory
DOCKER_DIST_DIR="${ROOT}/../../../docker/dist"
mkdir -p "$(dirname "$DOCKER_DIST_DIR")"
rm -rf "$DOCKER_DIST_DIR"
cp -R ${ROOT}/dist "$DOCKER_DIST_DIR"

echo "✅ Chatbot build completed!"