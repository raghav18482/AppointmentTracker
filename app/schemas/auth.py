from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from app.models.business import UserRole


class UserBase(BaseModel):
    """Base user schema."""
    email: EmailStr


class UserCreate(UserBase):
    """Schema for user registration."""
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")


class UserLogin(BaseModel):
    """Schema for user login."""
    email: EmailStr
    password: str


class UserResponse(UserBase):
    """Schema for user response."""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for access token response."""
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    business_id: Optional[UUID] = None  # First business if user has businesses


class TokenData(BaseModel):
    """Schema for token data."""
    email: Optional[str] = None
    user_id: Optional[UUID] = None


class LogoutResponse(BaseModel):
    """Schema for logout response."""
    message: str = "Successfully logged out"


class UserRoleResponse(BaseModel):
    """Schema for user role response."""
    user_id: UUID
    business_id: UUID
    role: UserRole
    business_name: Optional[str] = None
    
    class Config:
        from_attributes = True

