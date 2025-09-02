from flask import Flask

def create_app():
    """
    Creates, configures, and returns the Flask application.
    This is the application factory.
    """
    app = Flask(__name__)

    # With the app instance created, we can now register our blueprints.
    # Imports are placed here to avoid circular dependencies.
    from .routes import register_blueprints
    register_blueprints(app)
    
    

    return app
