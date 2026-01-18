from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class CustomerBase(BaseModel):
    """Base customer schema."""
    firstname: str = Field(..., min_length=1, max_length=100)
    lastname: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: str = Field(..., min_length=1, max_length=20)
    whatsapp_enabled: bool = False


class CustomerCreate(CustomerBase):
    """Schema for creating a customer."""
    pass


class CustomerUpdate(BaseModel):
    """Schema for updating a customer."""
    firstname: Optional[str] = Field(None, min_length=1, max_length=100)
    lastname: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, min_length=1, max_length=20)
    whatsapp_enabled: Optional[bool] = None


class CustomerResponse(CustomerBase):
    """Schema for customer response."""
    id: UUID
    business_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
