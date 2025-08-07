from .base import ConversationStorage
from typing import List

class InMemoryStorage(ConversationStorage):
    def __init__(self):
        super().__init__()
        self._store = {}
        print("DEBUG: InMemoryStorage initialized. Ready to store conversations. 🧠")

    def get_conversation(self, user_id: str) -> List[str]:
        history = self._store.get(user_id, [])
        print(f"DEBUG: Retrieved conversation for user_id: {user_id}. History length: {len(history)}")
        return history

    def update_conversation(self, user_id: str, message: str) -> None:
        if user_id not in self._store:
            print(f"DEBUG: New conversation started for user_id: {user_id}. 🆕")
            self._store[user_id] = []
        
        self._store[user_id].append(message)
        print(f"DEBUG: Appended message to conversation for user_id: {user_id}")
        # Assuming `message` is a dictionary, you can print the content for better visibility
        if isinstance(message, dict):
            print(f"       Role: {message.get('role', 'N/A')}, Content: {message.get('content', 'N/A')[:50]}...")