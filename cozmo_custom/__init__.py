import os
import sys

# Add the current directory (cozmo_custom) to Python's search path
# This allows modules inside this package (like cozmo) to find other
# modules at this level (like cozmoclad).
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))