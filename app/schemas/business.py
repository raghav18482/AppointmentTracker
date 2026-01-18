from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from app.models.business import BusinessType, UserRole


class BusinessBase(BaseModel):
    """Base business schema."""
    name: str = Field(..., min_length=1, max_length=255)
    type: BusinessType = BusinessType.OTHER
    timezone: str = Field(default="UTC", max_length=50)


class BusinessCreate(BusinessBase):
    """Schema for creating a business."""
    pass


class BusinessUpdate(BaseModel):
    """Schema for updating a business."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[BusinessType] = None
    timezone: Optional[str] = Field(None, max_length=50)


class BusinessResponse(BusinessBase):
    """Schema for business response."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UserBusinessCreate(BaseModel):
    """Schema for adding a user to a business."""
    user_id: UUID
    role: UserRole = UserRole.COUNTER


class UserBusinessResponse(BaseModel):
    """Schema for user-business relationship response."""
    id: UUID
    user_id: UUID
    business_id: UUID
    role: UserRole
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BusinessWithRoleResponse(BusinessResponse):
    """Business response with user's role in that business."""
    role: UserRole

