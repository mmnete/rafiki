from flask import Blueprint

def register_blueprints(app):
    """Register all route blueprints with the Flask app"""
    from .messaging_routes import messaging_bp
    from .test_routes import testing_bp
    from .web_app_routes import web_search_bp
    
    app.register_blueprint(messaging_bp)
    app.register_blueprint(testing_bp)
    app.register_blueprint(web_search_bp)
