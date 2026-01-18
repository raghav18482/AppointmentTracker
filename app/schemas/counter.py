from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID


class CounterCreate(BaseModel):
    """Schema for creating a counter."""
    name: str = Field(..., min_length=1, max_length=100, description="Counter name")
    is_active: bool = True


class CounterUpdate(BaseModel):
    """Schema for updating a counter."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    is_active: Optional[bool] = None


class CounterResponse(BaseModel):
    """Schema for counter response."""
    id: UUID
    name: str
    business_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

