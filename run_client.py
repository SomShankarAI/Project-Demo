#!/usr/bin/env python3
"""
Script to run the Streamlit Client
"""
import sys
import os
import subprocess

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("CLIENT_HOST", "localhost")
    port = int(os.getenv("CLIENT_PORT", "8501"))
    
    print(f"Starting Streamlit client on {host}:{port}")
    subprocess.run([
        "streamlit", "run", "client_app/main.py",
        "--server.address", host,
        "--server.port", str(port)
    ])