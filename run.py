from app import create_app
from dotenv import load_dotenv
from flask_cors import CORS, cross_origin

load_dotenv(dotenv_path='.env')

app = create_app()

CORS(app)

if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
    
