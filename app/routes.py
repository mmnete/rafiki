from flask import Blueprint, request, jsonify
from app.controllers.conversation_manager import ConversationManager
from twilio.twiml.messaging_response import MessagingResponse

main = Blueprint("main", __name__)
conv_manager = ConversationManager()

@main.route("/message", methods=["POST"])
def message():
    # Twilio sends form-encoded data
    phone_number = request.form.get("From")       # e.g. whatsapp:+1234567890
    user_message = request.form.get("Body")       # The message sent by the user

    if not phone_number or not user_message:
        return "Missing phone number or message", 400

    reply = conv_manager.handle_message(phone_number, user_message)

    response = MessagingResponse()
    response.message(reply)

    return str(response)
