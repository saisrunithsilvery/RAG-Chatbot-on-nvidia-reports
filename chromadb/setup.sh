#!/bin/bash

# Exit on error
set -e

echo "Starting ChromaDB setup..."

# Update package lists
apt update

# Upgrade packages
apt upgrade -y

# Install required packages
apt install -y apt-transport-https ca-certificates curl software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -

# Add Docker repository
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

# Update package database with Docker packages
apt update

# Install Docker
apt install -y docker-ce docker-ce-cli containerd.io

# Verify Docker installation
docker --version

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Apply executable permissions
chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version

# Navigate to the existing ChromaDB directory
cd ~/chromadb

# Note: Using the existing docker-compose.yaml file
echo "Using existing docker-compose.yaml file"

# Start the ChromaDB container
docker-compose up -d

# Check if the container is running
docker-compose ps

echo "ChromaDB setup complete! Your instance should be running at http://localhost:8000"
echo "To check the health of your instance, run: curl http://localhost:8000/api/v1/heartbeat"