from pydantic import BaseModel, Field, EmailStr
from datetime import datetime
from typing import Optional
from uuid import UUID
from app.models.business import UserRole


class StaffCreate(BaseModel):
    """Schema for adding existing staff to a business."""
    user_id: UUID
    role: UserRole = UserRole.COUNTER


class StaffCreateNew(BaseModel):
    """Schema for creating a new staff member (creates user and adds to business)."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    role: UserRole = UserRole.COUNTER


class StaffUpdate(BaseModel):
    """Schema for updating staff role."""
    role: UserRole


class StaffResponse(BaseModel):
    """Schema for staff response."""
    id: UUID
    user_id: UUID
    business_id: UUID
    role: UserRole
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class StaffDetailResponse(StaffResponse):
    """Staff response with user details."""
    user_email: str
    user_is_active: bool
    
    class Config:
        from_attributes = True

