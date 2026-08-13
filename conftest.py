"""
Pytest configuration and PYTHONPATH root registration.
"""

import sys
import os

# Register workspace root in sys.path
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
