from app.storage.in_memory import InMemoryStorage # Import the new storage class

class ConversationService:
    def __init__(self, storage: InMemoryStorage):
        self._storage = storage
    
    def get_conversation(self, phone_number):
        return self._storage.get_conversation(phone_number)

    def update_conversation(self, phone_number, message):
        return self._storage.update_conversation(phone_number, message)
