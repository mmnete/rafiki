from abc import ABC, abstractmethod
from typing import List

class ConversationStorage(ABC):
    @abstractmethod
    def get_conversation(self, user_id: str) -> List[str]:
        pass

    @abstractmethod
    def update_conversation(self, user_id: str, message: str) -> None:
        pass
