import sys
import os

# Add the subfolder to Python path so we can import the app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'iptv-vercel-flask'))

from api.index import app

# Expose app for Vercel
__all__ = ['app']
