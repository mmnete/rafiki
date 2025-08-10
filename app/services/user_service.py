import re
from typing import Optional, Tuple
from app.storage.db_service import StorageService, User

class FakeUserService:
    def __init__(self, storage: StorageService):
        # We no longer need an internal dictionary. We use the shared storage.
        self._storage = storage

    def is_valid_supported_number(self, phone_number: str) -> bool:
        tz_pattern = r"^(?:\+255|0)(6|7)\d{8}$"
        us_pattern = r"^\+1\d{10}$"
        return re.match(tz_pattern, phone_number) is not None or re.match(us_pattern, phone_number) is not None

    def get_or_create_user(self, phone_number: str) -> Tuple[Optional[User], Optional[str]]:
        if not self.is_valid_supported_number(phone_number):
            error_message = f"""Sorry :( We do not support your phone number ({phone_number}) for now. Please stay in the loop for our services expansions rolling out soon!"""
            return None, error_message

        # The core change: get the user from the shared storage
        user = self._storage.get_or_create_user(phone_number)
        
        if user == None:
            return None, "No user returned. Likely a database error!"
        
        return user, None

    def update_user_status(self, phone_number: str, new_status: str) -> User:
        user = self._storage.get_or_create_user(phone_number)
        self._storage.update_user_profile(user.id, status=new_status)
        return self._storage.get_or_create_user(phone_number)

    def update_user_details(self, phone_number: str, first_name: str = None, middle_name : str = None, last_name: str = None, location: str = None) -> User:
        user = self._storage.get_or_create_user(phone_number)
        self._storage.update_user_profile(user.id, first_name=first_name, middle_name=middle_name, last_name=last_name, location=location)
        return self._storage.get_or_create_user(phone_number)
    
    def delete_all_users(self):
        return self._storage.delete_all_users()

