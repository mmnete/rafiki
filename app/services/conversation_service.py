class ConversationService:
    def __init__(self):
        self._store = {}

    def get_conversation(self, user_id: str):
        return self._store.get(user_id, [])

    def update_conversation(self, user_id: str, message: dict):
        if user_id not in self._store:
            self._store[user_id] = []
        self._store[user_id].append(message)
