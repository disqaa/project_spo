from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()
    waiting_for_first_name = State()
    waiting_for_age = State()
    waiting_for_interests = State()
    waiting_for_about = State()
    waiting_for_photo = State()
    confirmation = State()

class LoginStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()

class SearchStates(StatesGroup):
    browsing = State()
    viewing_profile = State()
    setting_filters = State()

class ActivityStates(StatesGroup):
    choosing_interest = State()
    entering_location = State()
    entering_time = State()
    entering_description = State()
    confirmation = State()

class ProfileEditStates(StatesGroup):
    editing_interests = State()
    editing_about = State()
    editing_activity = State()

class MatchStates(StatesGroup):
    waiting_confirmation = State()