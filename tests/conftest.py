"""
Pytest configuration for rktn project.
Defines test discovery patterns and fixtures.
"""
import sys
import os

# Add src directory to path for all tests
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)
