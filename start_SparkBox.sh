#!/bin/bash

# Define directories
BASE_DIR="/home/sunrise/SparkBox"
LOG_DIR="$BASE_DIR/logs/runs"

# Create logs directory if it doesn't exist
if [ ! -d "$LOG_DIR" ]; then
    echo "Creating log directory: $LOG_DIR"
    mkdir -p "$LOG_DIR"
fi

# Navigate to the source directory
cd "$BASE_DIR/src"

# Start the applications in the background
echo "Starting main_arm.py..."
nohup python3 main_arm.py > "$LOG_DIR/main_arm.log" 2>&1 &

echo "Starting server.py..."
nohup python3 server.py > "$LOG_DIR/server.log" 2>&1 &

echo "SparkBox started. Logs are located in $LOG_DIR"