#!/usr/bin/env python3
"""
Test script for search and replace fallback logic
"""
import os
import sys
import logging
from dotenv import load_dotenv

# Add the code directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'code'))

from helper import ImageHelper

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

def test_fallback_logic():
    """Test the search and replace fallback logic with a mock scenario"""

    # Create a mock image helper
    helper = ImageHelper()

    # Use the proper test image
    test_image_path = '/tmp/test_image.png'

    try:
        # Test the search and replace method
        result = helper.search_and_replace(
            image_path=test_image_path,
            search_prompt="test search",
            replace_prompt="test replace",
            output_format="png"
        )
        print(f"Result: {result}")

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Clean up
        if os.path.exists(test_image_path):
            os.remove(test_image_path)

if __name__ == "__main__":
    test_fallback_logic()
