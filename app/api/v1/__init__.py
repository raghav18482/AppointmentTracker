from fastapi import APIRouter

from app.api.v1 import auth, users, business, queue, staff, notifications, dashboard, counters

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(business.router, prefix="/business", tags=["business"])
api_router.include_router(queue.router, prefix="/queue", tags=["queue"])
api_router.include_router(staff.router, prefix="/staff", tags=["staff"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(counters.router, prefix="/counters", tags=["counters"])

