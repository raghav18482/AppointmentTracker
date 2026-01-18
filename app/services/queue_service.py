from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, select
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy import update
import logging

from app.models.queue import QueueItem, QueueType, QueueItemStatus, Counter
from app.models.customer import Customer

logger = logging.getLogger(__name__)

# Import notification service (avoid circular import)
try:
    from app.services.notification_service import NotificationService
    NOTIFICATION_AVAILABLE = True
except ImportError:
    NOTIFICATION_AVAILABLE = False


class QueueService:
    """Service class for managing queue operations with smart serving logic."""
    
    # Serving pattern: 2 emergency, then 1 normal
    EMERGENCY_SERVE_COUNT = 2
    NORMAL_SERVE_COUNT = 1
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_next_customer(
        self,
        business_id: UUID,
        counter_id: Optional[UUID] = None
    ) -> Optional[QueueItem]:
        """
        Get the next customer to serve based on the pattern:
        - Serve 2 emergency customers, then 1 normal customer
        - Uses row-level locking for safe concurrency
        
        Args:
            business_id: Business ID
            counter_id: Optional counter ID to filter by
        
        Returns:
            Next QueueItem to serve, or None if queue is empty
        """
        # Count recent serves to determine pattern
        recent_serves = self._get_recent_serve_pattern(business_id, counter_id)
        
        # Determine which queue type to serve next
        emergency_count = sum(1 for q_type in recent_serves if q_type == QueueType.EMERGENCY)
        normal_count = sum(1 for q_type in recent_serves if q_type == QueueType.NORMAL)
        
        # Check if we need to serve emergency (if less than 2 emergency served)
        if emergency_count < self.EMERGENCY_SERVE_COUNT:
            next_item = self._get_next_emergency(business_id, counter_id)
            if next_item:
                return next_item
        
        # Check if we need to serve normal (if we've served 2 emergency)
        if emergency_count >= self.EMERGENCY_SERVE_COUNT and normal_count < self.NORMAL_SERVE_COUNT:
            next_item = self._get_next_normal(business_id, counter_id)
            if next_item:
                return next_item
        
        # If pattern is complete, start over with emergency
        if emergency_count >= self.EMERGENCY_SERVE_COUNT and normal_count >= self.NORMAL_SERVE_COUNT:
            next_item = self._get_next_emergency(business_id, counter_id)
            if next_item:
                return next_item
        
        # Fallback: serve whatever is available
        next_item = self._get_next_emergency(business_id, counter_id)
        if next_item:
            return next_item
        
        return self._get_next_normal(business_id, counter_id)
    
    def _get_recent_serve_pattern(
        self,
        business_id: UUID,
        counter_id: Optional[UUID] = None
    ) -> List[QueueType]:
        """
        Get the recent serving pattern to determine what to serve next.
        Looks at the last few served items.
        
        Args:
            business_id: Business ID
            counter_id: Optional counter ID
        
        Returns:
            List of QueueTypes from recent serves
        """
        query = self.db.query(QueueItem).filter(
            QueueItem.business_id == business_id,
            QueueItem.status == QueueItemStatus.SERVED
        )
        
        if counter_id:
            query = query.filter(QueueItem.counter_id == counter_id)
        
        # Get last few served items (enough to determine pattern)
        recent_items = query.order_by(QueueItem.updated_at.desc()).limit(
            self.EMERGENCY_SERVE_COUNT + self.NORMAL_SERVE_COUNT
        ).all()
        
        # Return queue types in reverse order (most recent first)
        return [item.queue_type for item in reversed(recent_items)]
    
    def _get_next_emergency(
        self,
        business_id: UUID,
        counter_id: Optional[UUID] = None
    ) -> Optional[QueueItem]:
        """
        Get the next emergency customer with row-level locking.
        
        Args:
            business_id: Business ID
            counter_id: Optional counter ID
        
        Returns:
            Next emergency QueueItem, or None
        """
        query = self.db.query(QueueItem).filter(
            QueueItem.business_id == business_id,
            QueueItem.queue_type == QueueType.EMERGENCY,
            QueueItem.status == QueueItemStatus.WAITING
        )
        
        if counter_id:
            query = query.filter(
                or_(
                    QueueItem.counter_id == counter_id,
                    QueueItem.counter_id.is_(None)
                )
            )
        
        # Use FOR UPDATE SKIP LOCKED for safe concurrency
        # This ensures only one process can lock a row at a time
        next_item = query.order_by(QueueItem.position.asc()).with_for_update(nowait=False, skip_locked=True).first()
        
        return next_item
    
    def _get_next_normal(
        self,
        business_id: UUID,
        counter_id: Optional[UUID] = None
    ) -> Optional[QueueItem]:
        """
        Get the next normal customer with row-level locking.
        
        Args:
            business_id: Business ID
            counter_id: Optional counter ID
        
        Returns:
            Next normal QueueItem, or None
        """
        query = self.db.query(QueueItem).filter(
            QueueItem.business_id == business_id,
            QueueItem.queue_type == QueueType.NORMAL,
            QueueItem.status == QueueItemStatus.WAITING
        )
        
        if counter_id:
            query = query.filter(
                or_(
                    QueueItem.counter_id == counter_id,
                    QueueItem.counter_id.is_(None)
                )
            )
        
        # Use FOR UPDATE SKIP LOCKED for safe concurrency
        next_item = query.order_by(QueueItem.position.asc()).with_for_update(nowait=False, skip_locked=True).first()
        
        return next_item
    
    def serve_customer(
        self,
        queue_item_id: UUID,
        counter_id: Optional[UUID] = None
    ) -> Optional[QueueItem]:
        """
        Mark a customer as served (atomic operation).
        
        Args:
            queue_item_id: Queue item ID
            counter_id: Optional counter ID to assign
        
        Returns:
            Updated QueueItem, or None if not found
        """
        try:
            # Lock the row for update
            queue_item = self.db.query(QueueItem).filter(
                QueueItem.id == queue_item_id,
                QueueItem.status == QueueItemStatus.WAITING
            ).with_for_update().first()
            
            if not queue_item:
                return None
            
            # Update status to SERVED
            queue_item.status = QueueItemStatus.SERVED
            
            if counter_id:
                queue_item.counter_id = counter_id
            
            self.db.commit()
            self.db.refresh(queue_item)
            
            logger.info(f"Served customer {queue_item.customer_id} from queue {queue_item_id}")
            return queue_item
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error serving customer: {e}")
            raise
    
    def notify_customer(
        self,
        queue_item_id: UUID
    ) -> Optional[QueueItem]:
        """
        Mark a customer as notified (state transition).
        
        Args:
            queue_item_id: Queue item ID
        
        Returns:
            Updated QueueItem, or None if not found
        """
        try:
            queue_item = self.db.query(QueueItem).filter(
                QueueItem.id == queue_item_id,
                QueueItem.status == QueueItemStatus.WAITING
            ).with_for_update().first()
            
            if not queue_item:
                return None
            
            # Transition: WAITING -> NOTIFIED
            queue_item.status = QueueItemStatus.NOTIFIED
            
            self.db.commit()
            self.db.refresh(queue_item)
            
            # Send WhatsApp notification if enabled
            if NOTIFICATION_AVAILABLE and queue_item.customer.whatsapp_enabled:
                try:
                    notification_service = NotificationService(self.db)
                    notification_service.send_queue_notification(
                        queue_item_id=queue_item_id
                    )
                    logger.info(f"Sent WhatsApp notification for queue item {queue_item_id}")
                except Exception as e:
                    logger.error(f"Failed to send notification: {e}")
                    # Don't fail the notify operation if notification fails
            
            logger.info(f"Notified customer {queue_item.customer_id} from queue {queue_item_id}")
            return queue_item
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error notifying customer: {e}")
            raise
    
    def handle_miss(
        self,
        queue_item_id: UUID
    ) -> Optional[QueueItem]:
        """
        Handle a missed customer appointment.
        - First miss: move to bottom of queue
        - Second miss: cancel the booking
        
        Args:
            queue_item_id: Queue item ID
        
        Returns:
            Updated QueueItem, or None if not found
        """
        try:
            queue_item = self.db.query(QueueItem).filter(
                QueueItem.id == queue_item_id,
                QueueItem.status.in_([QueueItemStatus.WAITING, QueueItemStatus.NOTIFIED])
            ).with_for_update().first()
            
            if not queue_item:
                return None
            
            # Increment miss count
            queue_item.miss_count += 1
            
            if queue_item.miss_count == 1:
                # First miss: move to bottom of queue
                new_position = self._get_max_position(
                    queue_item.business_id,
                    queue_item.queue_type
                ) + 1
                queue_item.position = new_position
                queue_item.status = QueueItemStatus.WAITING  # Reset to waiting
                
                logger.info(f"First miss for customer {queue_item.customer_id}, moved to position {new_position}")
                
            elif queue_item.miss_count >= 2:
                # Second miss: cancel
                queue_item.status = QueueItemStatus.CANCELLED
                
                logger.info(f"Second miss for customer {queue_item.customer_id}, cancelled booking")
            
            self.db.commit()
            self.db.refresh(queue_item)
            
            return queue_item
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error handling miss: {e}")
            raise
    
    def cancel_booking(
        self,
        queue_item_id: UUID
    ) -> Optional[QueueItem]:
        """
        Cancel a booking (manual cancellation).
        
        Args:
            queue_item_id: Queue item ID
        
        Returns:
            Updated QueueItem, or None if not found
        """
        try:
            queue_item = self.db.query(QueueItem).filter(
                QueueItem.id == queue_item_id,
                QueueItem.status.in_([
                    QueueItemStatus.WAITING,
                    QueueItemStatus.NOTIFIED
                ])
            ).with_for_update().first()
            
            if not queue_item:
                return None
            
            # Transition: WAITING/NOTIFIED -> CANCELLED
            queue_item.status = QueueItemStatus.CANCELLED
            
            self.db.commit()
            self.db.refresh(queue_item)
            
            logger.info(f"Cancelled booking {queue_item_id}")
            return queue_item
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error cancelling booking: {e}")
            raise
    
    def _get_max_position(
        self,
        business_id: UUID,
        queue_type: QueueType
    ) -> int:
        """
        Get the maximum position in a queue type.
        
        Args:
            business_id: Business ID
            queue_type: Queue type
        
        Returns:
            Maximum position (0 if queue is empty)
        """
        max_pos = self.db.query(func.max(QueueItem.position)).filter(
            QueueItem.business_id == business_id,
            QueueItem.queue_type == queue_type,
            QueueItem.status.in_([
                QueueItemStatus.WAITING,
                QueueItemStatus.NOTIFIED
            ])
        ).scalar()
        
        return max_pos if max_pos is not None else 0
    
    def get_queue_stats(
        self,
        business_id: UUID,
        counter_id: Optional[UUID] = None
    ) -> dict:
        """
        Get queue statistics.
        
        Args:
            business_id: Business ID
            counter_id: Optional counter ID
        
        Returns:
            Dictionary with queue statistics
        """
        query = self.db.query(QueueItem).filter(
            QueueItem.business_id == business_id
        )
        
        if counter_id:
            query = query.filter(
                or_(
                    QueueItem.counter_id == counter_id,
                    QueueItem.counter_id.is_(None)
                )
            )
        
        total_waiting = query.filter(QueueItem.status == QueueItemStatus.WAITING).count()
        total_notified = query.filter(QueueItem.status == QueueItemStatus.NOTIFIED).count()
        total_served = query.filter(QueueItem.status == QueueItemStatus.SERVED).count()
        
        emergency_waiting = query.filter(
            QueueItem.status == QueueItemStatus.WAITING,
            QueueItem.queue_type == QueueType.EMERGENCY
        ).count()
        
        normal_waiting = query.filter(
            QueueItem.status == QueueItemStatus.WAITING,
            QueueItem.queue_type == QueueType.NORMAL
        ).count()
        
        return {
            "total_waiting": total_waiting,
            "total_notified": total_notified,
            "total_served": total_served,
            "emergency_waiting": emergency_waiting,
            "normal_waiting": normal_waiting
        }

