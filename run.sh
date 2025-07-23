#!/bin/bash

# Define necessary paths
PROJECT_DIR="$(dirname "$(realpath "$0")")"

VENV_PATH="$PROJECT_DIR/venv"

echo "Virtual environment path: $VENV_PATH"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Run the Python script and capture exit code
python -m app.main
EXIT_CODE=$?

# Deactivate virtual environment
deactivate

# Output the exit code for visibility (optional)
echo "main.py exited with code: $EXIT_CODE"

# Exit with the same code as Python script to propagate it
exit $EXIT_CODE