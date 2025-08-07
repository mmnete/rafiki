from .base import ConversationStorage
from typing import List

class FirestoreStorage(ConversationStorage):
    def __init__(self):
        # TODO: Initialize your Firestore client here
        pass

    def get_conversation(self, user_id: str) -> List[str]:
        # TODO: Implement Firestore fetch logic here
        return []  # For now, just return empty list

    def update_conversation(self, user_id: str, message: str) -> None:
        # TODO: Implement Firestore write logic here
        pass
