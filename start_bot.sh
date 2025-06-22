#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
IMAGE_NAME="flatool"
CONTAINER_NAME="flatool-container"
VOLUME_NAME="flatool-db"
DB_HOST_PATH="./data/flatool.db" # Path to your local SQLite DB file
DB_CONTAINER_PATH="/app/data/flatool.db" # Path where the DB will be mounted inside the container

# --- Ask for BOT_TOKEN ---
if [ -z "$BOT_TOKEN" ]; then
  read -sp "Please enter your bot token: " BOT_TOKEN
  echo "" # New line after the password input
  if [ -z "$BOT_TOKEN" ]; then
    echo "Error: Token cannot be empty. Exiting."
    exit 1
  fi
fi

# --- Ask for BOT_STATUS ---
if [ -z "$BOT_STATUS" ]; then
  read -p "Please enter bot custom status: " BOT_STATUS
  if [ -z "$BOT_STATUS" ]; then
    echo "Error: Bot status cannot be empty. Exiting."
    exit 1
  fi
fi

# --- 1. Build the Docker Image ---
echo "---"
echo "Building Docker image: $IMAGE_NAME"
docker build -t "$IMAGE_NAME" .

# --- 2. Create the Docker Volume and Populate it (if not already existing) ---
# Check if the volume exists
echo "---"
if ! docker volume inspect "$VOLUME_NAME" &> /dev/null; then
  echo "Docker volume '$VOLUME_NAME' does not exist. Creating and populating it."
  docker volume create "$VOLUME_NAME"
  # Copy the existing database file into the newly created volume
  # We'll use a temporary container to copy the file
  echo "Copying $DB_HOST_PATH to volume $VOLUME_NAME..."
  docker run --rm -v "$VOLUME_NAME":/volume_data -v "$(pwd)/data":/host_data alpine cp /host_data/flatool.db /volume_data/flatool.db
  echo "Database file copied to volume."
else
  echo "Docker volume '$VOLUME_NAME' already exists. Skipping creation and population."
  # If the volume already exists, you might want to consider if you need to update the DB file.
  # For simplicity, this script assumes the initial copy is sufficient.
  # If your DB changes frequently on the host and you want to reflect those changes,
  # you might need to manually copy it again or use a bind mount instead of a named volume.
  # However, for a bot that writes to its DB, a named volume is generally preferred for persistence.
fi

# --- 3. Run the Docker Container ---
echo "---"
echo "Running container: $CONTAINER_NAME"

# Stop and remove existing container if it's running
if docker ps -a --format '{{.Names}}' | grep -q "$CONTAINER_NAME"; then
  echo "Stopping and removing existing container '$CONTAINER_NAME'..."
  docker stop "$CONTAINER_NAME"
  docker rm "$CONTAINER_NAME"
fi

docker run -d \
  --name "$CONTAINER_NAME" \
  -e BOT_TOKEN="$BOT_TOKEN" \
  -e BOT_STATUS="$BOT_STATUS" \
  -v "$VOLUME_NAME":$(dirname "$DB_CONTAINER_PATH") \
  "$IMAGE_NAME"

echo "---"
echo "Container '$CONTAINER_NAME' is running in detached mode."
echo "You can check its logs with: docker logs -f $CONTAINER_NAME"
echo "To stop the container: docker stop $CONTAINER_NAME"
echo "To remove the container: docker rm $CONTAINER_NAME"
echo "To remove the volume (be careful, this deletes your data!): docker volume rm $VOLUME_NAME"
echo "---"