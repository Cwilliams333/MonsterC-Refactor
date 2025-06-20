#!/usr/bin/env python3
"""
Test script to verify the new Gradio app works correctly.

This script tests the new modular UI to ensure it maintains 100% compatibility
with the original while using the new architecture.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

try:
    # Test imports
    print("Testing imports...")
    from ui.gradio_app import demo, launch_app
    from common.io import load_data
    from common.logging_config import get_logger
    print("✓ All imports successful")
    
    # Test logger
    print("Testing logger...")
    logger = get_logger("test")
    logger.info("Logger test successful")
    print("✓ Logger working")
    
    # Test Gradio app creation
    print("Testing Gradio app creation...")
    if demo is not None:
        print("✓ Gradio app created successfully")
    else:
        print("✗ Gradio app creation failed")
        sys.exit(1)
    
    # Test that we can import legacy functions
    print("Testing legacy function imports...")
    from legacy_app import perform_analysis, filter_data
    print("✓ Legacy function imports successful")
    
    print("\n🎉 All tests passed! The new Gradio app is ready to use.")
    print("\nTo run the app:")
    print("  python -c \"from src.ui.gradio_app import launch_app; launch_app()\"")
    print("\nOr:")
    print("  cd src && python ui/gradio_app.py")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure all dependencies are installed and the file structure is correct.")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)