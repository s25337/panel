#!/usr/bin/env python3
# run.py - Development server launcher
"""
Run Leafcore IoT Backend - Simplified version
"""
import logging
from app import create_app


def main():
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    host = "0.0.0.0"
    port = 5000
    
    print(f"Starting Leafcore IoT Backend")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print()
    
    app = create_app()
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
