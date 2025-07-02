#!/usr/bin/env python3
"""
Main entry point for the MonsterC CSV analysis application.

This serves as the new application entry point that uses the modular architecture
while maintaining 100% compatibility with the original functionality.
"""

import signal
import sys
import time
from pathlib import Path

# Add src directory to Python path so we can import our modules
project_root = Path(__file__).parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))


# Global variables for graceful shutdown
ctrl_c_count = 0
last_ctrl_c_time = 0
demo_instance = None
logger = None


def signal_handler(signum, frame):
    """Handle Ctrl+C with grace - require double press to exit."""
    global ctrl_c_count, last_ctrl_c_time, demo_instance, logger

    current_time = time.time()

    # Reset counter if more than 2 seconds have passed
    if current_time - last_ctrl_c_time > 2:
        ctrl_c_count = 0

    ctrl_c_count += 1
    last_ctrl_c_time = current_time

    if ctrl_c_count == 1:
        print("\n\n⚠️  Press Ctrl+C again within 2 seconds to exit...")
        if logger:
            logger.info("First Ctrl+C received - waiting for confirmation")
    elif ctrl_c_count >= 2:
        print("\n👋 Shutting down gracefully...")
        if logger:
            logger.info("Shutting down MonsterC application")

        # Clean shutdown of Gradio
        if demo_instance:
            try:
                demo_instance.close()
            except Exception:
                pass

        sys.exit(0)


def main():
    """Main application entry point."""
    global demo_instance, logger

    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Initialize logging first
        from common.logging_config import configure_logging

        logger = configure_logging(
            app_name="MonsterC",
            log_level="INFO",  # Change to "DEBUG" for development
            log_dir="logs",
        )

        logger.info("Starting MonsterC CSV Analysis Application")
        logger.info(f"Project root: {project_root}")
        logger.info(f"Source path: {src_path}")

        # Import and launch the Gradio app
        from ui.gradio_app import demo

        demo_instance = demo

        logger.info("Launching Gradio interface...")
        print("\n🚀 MonsterC is starting up...")
        print("Press Ctrl+C twice to exit gracefully\n")

        # Launch the application
        demo.launch(
            share=False,
            server_name="127.0.0.1",  # Bind to localhost only for security
            server_port=7860,  # Default Gradio port
            show_error=True,  # Show detailed errors in development
            quiet=False,  # Show startup messages
        )

    except ImportError as e:
        print(f"Import error: {e}")
        print(
            "Make sure you've installed all dependencies: "
            "pip install -r requirements.txt"
        )
        sys.exit(1)
    except Exception as e:
        print(f"Error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
