from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from app.models.queue import QueueType, QueueItemStatus


class BookingCreate(BaseModel):
    """Schema for creating a booking."""
    firstname: str = Field(..., min_length=1, max_length=100)
    lastname: str = Field(..., min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: str = Field(..., min_length=1, max_length=20)
    whatsapp_enabled: bool = False
    queue_type: QueueType = QueueType.NORMAL
    counter_id: Optional[UUID] = None  # Optional, can be assigned later


class BookingResponse(BaseModel):
    """Schema for booking response."""
    id: UUID
    customer_id: UUID
    business_id: UUID
    counter_id: Optional[UUID]
    queue_type: QueueType
    position: int
    status: QueueItemStatus
    miss_count: int
    created_at: datetime
    updated_at: datetime
    
    # Customer details
    customer_firstname: str
    customer_lastname: str
    customer_phone: str
    customer_email: Optional[str]
    
    class Config:
        from_attributes = True


class QueueItemResponse(BaseModel):
    """Schema for queue item response."""
    id: UUID
    customer_id: UUID
    business_id: UUID
    counter_id: Optional[UUID]
    queue_type: QueueType
    position: int
    status: QueueItemStatus
    miss_count: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
