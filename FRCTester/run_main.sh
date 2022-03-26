#!/bin/bash

docker-compose --project-name frc_tester build --no-cache
docker-compose --project-name frc_tester up
docker container prune -f
docker image prune -f
docker volume prune -f