import re

class User:
    def __init__(self, phone_number: str, first_name: str = None, last_name: str = None, location: str = None, status: str = "new"):
        self.phone_number = phone_number
        self.first_name = first_name
        self.last_name = last_name
        self.location = location
        self.status = status  # 'new', 'onboarding_greet', 'onboarding_name', ..., 'active'

    def to_dict(self):
        return {
            "phone_number": self.phone_number,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "location": self.location,
            "status": self.status
        }

class FakeUserService:
    def __init__(self):
        self._users = {}

    def is_valid_tanzanian_number(self, phone_number: str) -> bool:
        # Accepts: +2557XXXXXXXX, +2556XXXXXXXX, 07XXXXXXXX, 06XXXXXXXX
        # The regex is slightly adjusted to be more explicit and robust
        pattern = r"^(?:\+255|0)(6|7)\d{8}$"
        return re.match(pattern, phone_number) is not None

    def get_or_create_user(self, phone_number: str):
        # First, validate the phone number before anything else.
        if not self.is_valid_tanzanian_number(phone_number):
            error_message = (
                """Oops! Kuna hitilafu kidogo 😅
Kwa sasa tunahudumia tu namba za simu za Kitanzania zinazoanza na +255 📞🇹🇿
Lakini usijali! Huduma yetu inakua kwa kasi 🌱✨ na tutakutaarifu mara tu tutakapoanza kutoa huduma kwenye nchi yako! 🌍🎉
---
Oops! There’s a small issue 😅
Currently, we only support Tanzanian phone numbers starting with +255 📞🇹🇿
But don’t worry! Our service is growing fast 🌱✨ and we’ll notify you as soon as we launch in your country! 🌍🎉"""
            )
            return None, error_message

        # If the number is valid, proceed to get or create the user.
        user = self._users.get(phone_number)
        if user is None:
            user = User(phone_number, status="onboarding_greet")
            self._users[phone_number] = user
            print(f"FakeUserService: New user {phone_number} created with status 'onboarding_greet'.")
        
        return user, None

    def update_user_status(self, phone_number: str, new_status: str):
        # Now, `get_or_create_user` returns a tuple. We need to handle both parts.
        user, _ = self.get_or_create_user(phone_number)
        if user:
            user.status = new_status
            print(f"FakeUserService: User {phone_number} status updated to '{new_status}'.")

    def update_user_details(self, phone_number: str, first_name: str = None, last_name: str = None, location: str = None):
        # This also needs to handle the tuple return
        user, _ = self.get_or_create_user(phone_number)
        if user:
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            if location:
                user.location = location
            print(f"FakeUserService: User {phone_number} details updated.")