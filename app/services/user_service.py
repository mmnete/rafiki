import re
from typing import Optional, Tuple
from app.storage.in_memory import InMemoryStorage, User

class FakeUserService:
    def __init__(self, storage: InMemoryStorage):
        # We no longer need an internal dictionary. We use the shared storage.
        self._storage = storage

    def is_valid_supported_number(self, phone_number: str) -> bool:
        tz_pattern = r"^(?:\+255|0)(6|7)\d{8}$"
        us_pattern = r"^\+1\d{10}$"
        return re.match(tz_pattern, phone_number) is not None or re.match(us_pattern, phone_number) is not None

    def get_or_create_user(self, phone_number: str) -> Tuple[Optional[User], Optional[str]]:
        if not self.is_valid_supported_number(phone_number):
            error_message = """... (your existing error message) ..."""
            return None, error_message

        # The core change: get the user from the shared storage
        user = self._storage.get_user(phone_number)
        
        if user is None:
            print(f"FakeUserService: User not found. Creating new user for {phone_number}.")
            user = User(phone_number, status="onboarding_greet")
            self._storage.set_user(phone_number, user) # Save the new user to storage
            print(f"FakeUserService: New user {phone_number} created with status '{user.status}'.")
        
        return user, None

    def update_user_status(self, phone_number: str, new_status: str) -> User:
        user = self._storage.get_user(phone_number)
        if user:
            user.status = new_status
            self._storage.set_user(phone_number, user) # Save the change
            print(f"FakeUserService: User {phone_number} status updated to '{new_status}'.")
        return user

    def update_user_details(self, phone_number: str, first_name: str = None, middle_name : str = None, last_name: str = None, location: str = None) -> User:
        user = self._storage.get_user(phone_number)
        if user:
            user.first_name = first_name if first_name is not None else user.first_name
            user.middle_name = middle_name if middle_name is not None else user.middle_name
            user.last_name = last_name if last_name is not None else user.last_name
            user.location = location if location is not None else user.location
            self._storage.set_user(phone_number, user)
            print(f"FakeUserService: User {phone_number} details updated.")
        return user
