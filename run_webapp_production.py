"""
Production-ready script to run the web application.
Uses waitress server instead of Flask's development server for better stability.
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Import the Flask app
from web_app.app import app, CHROMA_PATH

if __name__ == '__main__':
    db_status = "Ready" if os.path.exists(CHROMA_PATH) else "Not found - build database first"
    print(f"🤖 ccGPT Production Mode | Database: {db_status} | Server: http://localhost:5000")
    
    try:
        # Try to use waitress for production
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000, threads=4)
    except ImportError:
        print("⚠️ Waitress not installed - using Flask dev server (install: pipenv install waitress)")
        app.run(debug=False, host='0.0.0.0', port=5000)

