from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from uuid import UUID
from app.models.notification import NotificationStatus, NotificationType


class NotificationResponse(BaseModel):
    """Schema for notification response."""
    id: UUID
    queue_item_id: UUID
    customer_id: UUID
    business_id: UUID
    notification_type: str
    recipient_phone: str
    recipient_email: Optional[str]
    message_template: Optional[str]
    message_body: str
    status: str
    retry_count: int
    max_retries: int
    external_id: Optional[str]
    error_message: Optional[str]
    sent_at: Optional[datetime]
    delivered_at: Optional[datetime]
    read_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class NotificationCreate(BaseModel):
    """Schema for creating a notification."""
    queue_item_id: UUID
    message_template: Optional[str] = None
    custom_message: Optional[str] = Field(None, max_length=1000)


class NotificationResend(BaseModel):
    """Schema for resending a notification."""
    notification_id: UUID

