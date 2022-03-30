#!/bin/bash

docker build -f "Dockerfile_Tests" -t frc_unit_tests .
docker run -it --rm --env-file ".env" --name frc_unit_tests frc_unit_tests
docker image rm frc_unit_tests
docker image prune -f
docker container prune -f