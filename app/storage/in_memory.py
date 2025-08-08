from typing import Dict, Any, List, cast
from .file_service import FileService

class User:
    def __init__(self, phone_number: str, first_name: str = None, last_name: str = None, location: str = None, status: str = "new"):
        self.phone_number = phone_number
        self.first_name = first_name
        self.last_name = last_name
        self.location = location
        self.status = status
        
    def to_dict(self):
        return {
            "phone_number": self.phone_number,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "location": self.location,
            "status": self.status
        }
        
    def __repr__(self):
        return f"User(phone_number={self.phone_number}, status={self.status})"

class InMemoryStorage:
    # Use a class-level dictionary to ensure data persists across instances
    _store: Dict[str, Any] = {
        "conversations": {},
        "users": {}
    }
    
    def __init__(self):
        print("DEBUG: InMemoryStorage initialized. Ready to store data. 🧠")
        self._file_service = FileService()
        self._store = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        """Loads data from file and deserializes user objects."""
        data = self._file_service.read_json()
        
        if 'users' in data:
            data['users'] = {phone: User.from_dict(user_dict) for phone, user_dict in data['users'].items()}
        
        return data
    
    def _persist_data(self) -> None:
        """Serializes data and writes to file using the FileService."""
        # We need to serialize User objects to dictionaries before saving
        serializable_data = {
            "conversations": self._store["conversations"],
            "users": {
                phone: user.to_dict() 
                for phone, user in self._store["users"].items()
            }
        }
        self._file_service.write_json(serializable_data)

    def get_conversation(self, user_id: str) -> List[Dict[str, str]]:
        """Retrieves a user's conversation history."""
        history = self._store["conversations"].get(user_id, [])
        print(f"DEBUG: Retrieved conversation for user_id: {user_id}. History length: {len(history)}")
        return history

    def update_conversation(self, user_id: str, message: Dict[str, str]) -> None:
        """Appends a new message to a user's conversation history and persists it."""
        if user_id not in self._store["conversations"]:
            print(f"DEBUG: New conversation started for user_id: {user_id}. 🆕")
            self._store["conversations"][user_id] = []
        
        self._store["conversations"][user_id].append(message)
        self._persist_data()
        print(f"DEBUG: Appended message to conversation for user_id: {user_id}")
        if isinstance(message, dict):
            print(f"       Role: {message.get('role', 'N/A')}, Content: {message.get('content', 'N/A')[:50]}...")

    def get_user(self, user_id: str) -> User:
        """Retrieves a user object from the store."""
        print("DEBUG: Current state of the entire in-memory store:")
        print(self._store)
        return cast(User, self._store["users"].get(user_id))

    def set_user(self, user_id: str, user_data: Any) -> None:
        """Saves a user object to the store and persists it."""
        self._store["users"][user_id] = user_data
        self._persist_data()
        print(f"DEBUG: User {user_id} saved to InMemoryStorage.")