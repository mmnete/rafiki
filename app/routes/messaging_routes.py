from flask import Blueprint, request
from app.controllers.messaging_controller import MessagingController

messaging_bp = Blueprint("messaging", __name__)
messaging_controller = MessagingController()

@messaging_bp.route("/message", methods=["POST"])
def handle_twilio_message():
    """Route: Delegate to controller"""
    return messaging_controller.handle_twilio_message(request.form)

