# handlers/__init__.py

from .start import router as start_router
from .auth import router as auth_router
from .profile import router as profile_router
from .search import router as search_router
from .activity import router as activity_router
from .matches import router as matches_router
from .map import router as map_router  # Добавляем новый роутер

__all__ = [
    "start_router",
    "auth_router",
    "profile_router",
    "search_router",
    "activity_router",
    "matches_router",
    "map_router"  # Добавляем в экспорт
]