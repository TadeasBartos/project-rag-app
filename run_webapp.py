"""
Helper script to run the web application from the project root.
This ensures proper path resolution for imports.
"""

import sys
import os
import warnings

# Suppress Windows socket warnings on shutdown
warnings.filterwarnings("ignore", category=ResourceWarning)

# Add project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the Flask app
from web_app.app import app

if __name__ == '__main__':
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=True)
    except KeyboardInterrupt:
        print("\n\nShutting down gracefully...")
        sys.exit(0)

