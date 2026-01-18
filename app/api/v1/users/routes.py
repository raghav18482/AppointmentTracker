from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def users_root():
    """Users module root endpoint."""
    return {"message": "Users module"}

