#!/usr/bin/env python3
"""
Script to run the FastAPI Server
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server_app.main import app
import uvicorn
from dotenv import load_dotenv

load_dotenv()

if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "localhost")
    port = int(os.getenv("SERVER_PORT", "8000"))
    
    print(f"Starting FastAPI server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)