import logging
import sys
from app import create_app
from dotenv import load_dotenv
from flask_cors import CORS

# --- Configure logging globally ---
logging.basicConfig(
    level=logging.DEBUG,  # or INFO in production
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]  # ensures logs go to stdout for Docker
)

# --- Load environment variables ---
load_dotenv(dotenv_path=".env")

# --- Create and configure Flask app ---
app = create_app()
CORS(app)

if __name__ == "__main__":
    # Don’t use debug=True inside Docker in production (Flask debugger isn't safe)
    app.run(host="0.0.0.0", port=5000, debug=False)
