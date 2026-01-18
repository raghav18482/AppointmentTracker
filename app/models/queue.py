from sqlalchemy import Column, String, ForeignKey, Integer, Boolean, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.models.base import BaseModel


class QueueType(str, enum.Enum):
    """Queue type enumeration."""
    NORMAL = "normal"
    EMERGENCY = "emergency"


class QueueItemStatus(str, enum.Enum):
    """Queue item status enumeration."""
    WAITING = "waiting"
    NOTIFIED = "notified"
    SERVED = "served"
    MISSED = "missed"
    CANCELLED = "cancelled"


class Counter(BaseModel):
    """Counter model for queue management."""
    
    __tablename__ = "counters"
    
    name = Column(String, nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    business = relationship("Business", back_populates="counters")
    queue_items = relationship("QueueItem", back_populates="counter")


class QueueItem(BaseModel):
    """Queue item model for managing bookings in queue."""
    
    __tablename__ = "queue_items"
    
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    counter_id = Column(UUID(as_uuid=True), ForeignKey("counters.id", ondelete="SET NULL"), nullable=True, index=True)
    queue_type = Column(SQLEnum(QueueType, native_enum=False), nullable=False, default=QueueType.NORMAL, index=True)
    position = Column(Integer, nullable=False, index=True)
    status = Column(SQLEnum(QueueItemStatus, native_enum=False), nullable=False, default=QueueItemStatus.WAITING, index=True)
    miss_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    customer = relationship("Customer", back_populates="queue_items")
    business = relationship("Business", back_populates="queue_items")
    counter = relationship("Counter", back_populates="queue_items")
    notifications = relationship("Notification", back_populates="queue_item", cascade="all, delete-orphan")
