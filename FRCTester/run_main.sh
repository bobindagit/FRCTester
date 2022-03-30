#!/bin/bash

docker-compose build --no-cache
docker-compose run python_app
docker container prune -f
docker image prune -f
docker volume prune -f
docker image rm frctester_python_app