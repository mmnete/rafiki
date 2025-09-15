import logging
import sys
from app import create_app
from dotenv import load_dotenv
from flask_cors import CORS

# --- Configure logging globally ---
logging.basicConfig(
    level=logging.DEBUG,  # use INFO if DEBUG is too noisy
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

# --- Load environment variables ---
load_dotenv(dotenv_path='.env')

# --- Create and configure Flask app ---
app = create_app()
CORS(app)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
