import sys
import os

# Add the subfolder to Python path so we can import the Flask app
subfolder_path = os.path.join(os.path.dirname(__file__), '..', 'iptv-vercel-flask')
sys.path.insert(0, subfolder_path)

# Import the Flask app from the subfolder (not from api.index, but directly execute the file)
import importlib.util
spec = importlib.util.spec_from_file_location("iptv_app", os.path.join(subfolder_path, "api", "index.py"))
iptv_app_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(iptv_app_module)

# Expose the app for Vercel
app = iptv_app_module.app

__all__ = ['app']
