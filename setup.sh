#!/bin/bash
# Setup script for Linux/Mac

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p data logs output
playwright install chromium
cp .env.example .env

echo "Setup complete. Edit .env with your API keys, then run: python backend/app.py"
