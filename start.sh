#!/bin/bash
# Start script for the application

export PATH="$HOME/.local/bin:$PATH"

# Activate poetry environment and run uvicorn
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

