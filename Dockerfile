# Use a slim Python image for smaller size
FROM python:3.10-slim-bullseye

WORKDIR /app

# Copy only requirements.txt first to leverage Docker's build cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
# This should happen after installing dependencies to maximize cache hits
COPY . .

RUN mkdir -p /app/data

# The BOT_TOKEN will be passed in as an environment variable at runtime
CMD ["python", "flatool.py"]