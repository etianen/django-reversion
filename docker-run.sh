#!/bin/sh

set -e

DOCKER_IMAGE_WORK_DIR='/run/host-current-dir/'
DOCKER_IMAGE_LATEST_NAME='django-reversion_as:latest'
DOCKER_IMAGE_ID=$(docker images -q "$DOCKER_IMAGE_LATEST_NAME")

if [ -z $DOCKER_IMAGE_ID ]; then
  docker-compose build --build-arg WORK_DIR=$DOCKER_IMAGE_WORK_DIR as
fi

docker-compose run --rm -v $(pwd):$DOCKER_IMAGE_WORK_DIR -p "80:80" as $@
