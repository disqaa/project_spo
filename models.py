from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class User:
    id: Optional[int] = None
    telegram_id: Optional[int] = None
    username: str = ""
    password: str = ""
    first_name: str = ""
    age: int = 0
    photo_path: Optional[str] = None
    photo_id: Optional[str] = None
    is_active: bool = True
    is_authenticated: bool = False
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    @classmethod
    def from_record(cls, record):
        """Create User from database record"""
        if not record:
            return None

        return cls(
            id=record['id'],
            telegram_id=record['telegram_id'],
            username=record['username'],
            password=record['password'],
            first_name=record['first_name'],
            age=record['age'],
            photo_path=record['photo_path'],
            photo_id=record['photo_id'],
            is_active=record['is_active'],
            is_authenticated=record['is_authenticated'],
            created_at=record['created_at'],
            last_login=record['last_login']
        )