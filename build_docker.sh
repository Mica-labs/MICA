#!/bin/bash

IMAGE_LATEST="micalabs/mica:latest"

CURRENT_DIR=$(pwd)

echo "Packaging frontend resources..."
cd mica/connector/website || { echo "Failed to enter directory mica/connector/website"; exit 1; }
if sh scripts/build-static.sh; then
    echo "Frontend resources packaged successfully"
else
    echo "Frontend resources packaging failed, please check build-static.sh and the environment"
    exit 1
fi

cd "$CURRENT_DIR" || { echo "Failed to return to original directory"; exit 1; }

echo "Building Docker image: $IMAGE_LATEST"
if docker build -t "$IMAGE_LATEST" -f docker/Dockerfile .; then
    echo "Docker image built successfully: $IMAGE_LATEST"
else
    echo "Docker image build failed, please check Dockerfile and build environment"
    exit 1
fi
