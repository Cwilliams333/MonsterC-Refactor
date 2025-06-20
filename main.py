#!/usr/bin/env python3
"""
Main entry point for the MonsterC CSV analysis application.

This serves as the new application entry point that uses the modular architecture
while maintaining 100% compatibility with the original functionality.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path so we can import our modules
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

def main():
    """Main application entry point."""
    try:
        # Initialize logging first
        from common.logging_config import configure_logging
        logger = configure_logging(
            app_name="MonsterC",
            log_level="INFO",  # Change to "DEBUG" for development
            log_dir="logs"
        )
        
        logger.info("Starting MonsterC CSV Analysis Application")
        logger.info(f"Project root: {project_root}")
        logger.info(f"Source path: {src_path}")
        
        # Import and launch the Gradio app
        from ui.gradio_app import demo
        
        logger.info("Launching Gradio interface...")
        
        # Launch the application
        demo.launch(
            share=False,
            server_name="127.0.0.1",  # Bind to localhost only for security
            server_port=7860,         # Default Gradio port
            show_error=True,          # Show detailed errors in development
            quiet=False               # Show startup messages
        )
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure you've installed all dependencies: pip install -r requirements.txt")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()