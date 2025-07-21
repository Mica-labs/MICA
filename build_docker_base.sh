#!/bin/bash

IMAGE="micalabs/micabase:v1"

# Build Docker image
echo "Building Docker image: $IMAGE"
if docker build -t "$IMAGE" -f docker/Dockerfile.base .; then
    echo "Docker image built successfully: $IMAGE"
else
    echo "Failed to build Docker image, please check Dockerfile.base and the build environment"
    exit 1
fi
