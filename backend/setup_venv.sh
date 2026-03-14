#!/bin/bash
# Fix architecture mismatch: ensures venv uses native Apple Silicon (arm64) Python
# Run this from the backend directory: ./setup_venv.sh

set -e
cd "$(dirname "$0")"

echo "Removing existing venv..."
rm -rf venv

echo "Creating fresh venv with native arm64 Python..."
arch -arm64 python3 -m venv venv

echo "Activating venv and installing dependencies..."
source venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo ""
echo "Verifying numpy import..."
python3 -c "import numpy; print('numpy OK')"
echo "Done! Run: python3 app.py"
