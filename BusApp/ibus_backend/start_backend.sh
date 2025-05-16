#!/bin/bash
echo "👉 Starting FastAPI server from main.py..."
cd "$(dirname "$0")"
uvicorn main:app --reload
