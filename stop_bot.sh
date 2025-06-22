#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
CONTAINER_NAME="flatool-container" # This should match the name in run_bot.sh

# --- Stop and Remove Container ---
echo "---"
echo "Attempting to stop and remove container: $CONTAINER_NAME"

# Check if the container is running or exists
if docker ps -a --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
  echo "Container '$CONTAINER_NAME' found. Stopping..."
  docker stop "$CONTAINER_NAME"
  echo "Container '$CONTAINER_NAME' stopped. Removing..."
  docker rm "$CONTAINER_NAME"
  echo "Container '$CONTAINER_NAME' removed successfully."
else
  echo "Container '$CONTAINER_NAME' is not running or does not exist."
fi

echo "---"
echo "Bot has stopped."