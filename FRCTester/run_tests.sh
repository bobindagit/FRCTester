#!/bin/bash

docker build --file "Dockerfile_Tests" --tag frc_unit_tests .
docker run -it --rm --env-file ".env" --name frc_unit_tests frc_unit_tests
docker image prune -f
docker container prune -f