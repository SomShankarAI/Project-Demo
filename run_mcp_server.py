#!/usr/bin/env python3
"""
Script to run the MCP Tools Server
"""
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mcp_server.main import main

if __name__ == "__main__":
    print("Starting MCP Tools Server...")
    main()