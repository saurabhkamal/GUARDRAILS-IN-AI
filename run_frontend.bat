@echo off
cd /d "%~dp0frontend"
pip install -r requirements.txt
streamlit run app.py
