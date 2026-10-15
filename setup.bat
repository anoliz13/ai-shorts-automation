@echo off
REM Setup script for Windows

python -m venv venv
call venv\Scripts\activate.bat
pip install -r requirements.txt
mkdir data logs output 2>nul
playwright install chromium
copy .env.example .env

echo Setup complete. Edit .env with your API keys, then run: python backend/app.py
