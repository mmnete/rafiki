from flask import Flask
from flask.json.provider import DefaultJSONProvider
from enum import Enum

class CustomJSONProvider(DefaultJSONProvider):
    def default(self, obj):
        if isinstance(obj, Enum):
            return obj.value
        return super().default(obj)

def create_app():
    """
    Creates, configures, and returns the Flask application.
    This is the application factory.
    """
    app = Flask(__name__)
    
    # Set custom JSON provider to handle enums
    app.json = CustomJSONProvider(app)

    # With the app instance created, we can now register our blueprints.
    # Imports are placed here to avoid circular dependencies.
    from .routes import register_blueprints
    register_blueprints(app)
    
    return app