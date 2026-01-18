from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from app.models.queue import QueueType, QueueItemStatus
from app.models.notification import NotificationStatus


class QueueItemSummary(BaseModel):
    """Summary of a queue item for dashboard."""
    id: UUID
    position: int
    queue_type: QueueType
    status: QueueItemStatus
    customer_name: str
    customer_phone: str
    counter_name: Optional[str]
    wait_time_minutes: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class MissedCustomerSummary(BaseModel):
    """Summary of missed customers."""
    id: UUID
    queue_item_id: UUID
    customer_name: str
    customer_phone: str
    miss_count: int
    last_missed_at: datetime
    queue_type: QueueType
    position: int
    
    class Config:
        from_attributes = True


class FailedNotificationSummary(BaseModel):
    """Summary of failed notifications."""
    id: UUID
    queue_item_id: UUID
    customer_name: str
    customer_phone: str
    retry_count: int
    max_retries: int
    error_message: Optional[str]
    failed_at: datetime
    last_retry_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CounterActivitySummary(BaseModel):
    """Summary of counter activity."""
    counter_id: UUID
    counter_name: str
    total_served_today: int
    currently_serving: Optional[UUID]  # Queue item ID
    waiting_count: int
    last_served_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    """Overall dashboard statistics."""
    total_waiting: int
    total_notified: int
    total_served_today: int
    total_missed_today: int
    total_failed_notifications: int
    emergency_waiting: int
    normal_waiting: int
    active_counters: int


class LiveQueueView(BaseModel):
    """Live queue view response."""
    stats: DashboardStats
    queue_items: List[QueueItemSummary]
    missed_customers: List[MissedCustomerSummary]
    failed_notifications: List[FailedNotificationSummary]
    counter_activity: List[CounterActivitySummary]

