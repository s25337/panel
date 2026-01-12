#!/usr/bin/env python3
# run.py - Development server launcher
"""
Run Leafcore IoT Backend development server
"""
import os
import sys
import logging
from app import create_app


def main():
    # Configure logging to show all INFO and above messages
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check if running in development or production mode
    use_hardware = os.getenv("USE_HARDWARE", "0").lower() in ["1", "true", "yes"]
    # Disable Flask debug mode (it interferes with background threads and logging)
    debug = False  
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    print(f"Starting Leafcore IoT Backend")
    print(f"  Hardware mode: {use_hardware}")
    print(f"  Debug mode: {debug}")
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print()
    
    app = create_app(use_hardware=use_hardware)
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    main()
