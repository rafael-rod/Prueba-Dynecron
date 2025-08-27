import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
try:
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, continue without it

# Database configuration
DB_PATH = os.path.join(os.path.dirname(__file__), 'app.db')

# API configuration
def get_google_api_key():
    """Get Google API key from environment variable or config file."""
    # First try environment variable
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        return api_key
    
    # If not in environment, try to read from a local config file
    config_file = os.path.join(os.path.dirname(__file__), "api_config.txt")
    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                api_key = f.read().strip()
                if api_key and api_key != "your_google_api_key_here":
                    return api_key
        except Exception:
            pass
    
    return None

def set_google_api_key(api_key: str):
    """Set Google API key in a local config file."""
    try:
        config_file = os.path.join(os.path.dirname(__file__), "api_config.txt")
        with open(config_file, "w") as f:
            f.write(api_key)
        return True
    except Exception:
        return False

# Search configuration
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
TOP_K_RESULTS = 5
SIMILARITY_THRESHOLD = 0.1
