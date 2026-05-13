"""v1 API package — combines all v1 routers."""
from fastapi import APIRouter

from app.api.v1 import auth, books, borrow

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(books.router)
api_router.include_router(borrow.router)
