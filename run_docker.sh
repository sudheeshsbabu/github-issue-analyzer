#!/bin/bash

# Ensure we have a fresh start
echo "Stopping any running containers..."
docker compose down

# Build and start the container
echo "Building and starting the application..."
docker compose up --build
