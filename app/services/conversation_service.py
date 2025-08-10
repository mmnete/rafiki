from app.storage.db_service import StorageService # Import the new storage class

class ConversationService:
    def __init__(self, storage: StorageService):
        self._storage = storage
    
    def get_conversation(self, phone_number, limit=10):
        user = self._storage.get_or_create_user(phone_number)
        return self._storage.load_user_conversation_history(user.id, limit)

    def update_conversation(self, phone_number, message):
        return self._storage.update_conversation(phone_number, message)
