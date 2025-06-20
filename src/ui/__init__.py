"""
UI module for MonsterC application.

This module contains the user interface components, currently featuring
a Gradio-based web interface that follows the Strangler Fig pattern.
"""

from .gradio_app import launch_app, demo

__all__ = ['launch_app', 'demo']