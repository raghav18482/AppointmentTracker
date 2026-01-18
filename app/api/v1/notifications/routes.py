from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.business_dependencies import get_current_business
from app.models.user import User
from app.models.business import Business
from app.models.notification import Notification, NotificationStatus
from app.services.notification_service import NotificationService
from app.schemas.notification import (
    NotificationResponse,
    NotificationCreate,
    NotificationResend
)

router = APIRouter()


def retry_failed_notifications_background(
    db: Session,
    business_id: UUID
):
    """
    Background task to retry failed notifications.
    
    Args:
        db: Database session
        business_id: Business ID
    """
    notification_service = NotificationService(db)
    try:
        retried_count = notification_service.retry_all_failed_notifications(business_id)
        print(f"Retried {retried_count} failed notifications for business {business_id}")
    except Exception as e:
        print(f"Error in background retry task: {e}")
    finally:
        db.close()


@router.post("/send", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def send_notification(
    notification_data: NotificationCreate,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Send a notification for a queue item.
    
    Args:
        notification_data: Notification creation data
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Created notification
    """
    # Verify user has access
    from app.models.business import UserBusiness
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business"
        )
    
    # Verify queue item belongs to business
    from app.models.queue import QueueItem
    queue_item = db.query(QueueItem).filter(
        QueueItem.id == notification_data.queue_item_id,
        QueueItem.business_id == current_business.id
    ).first()
    
    if not queue_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue item not found"
        )
    
    # Send notification
    notification_service = NotificationService(db)
    notification = notification_service.send_queue_notification(
        queue_item_id=notification_data.queue_item_id,
        message_template=notification_data.message_template,
        custom_message=notification_data.custom_message
    )
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to send notification (customer may not have WhatsApp enabled)"
        )
    
    return NotificationResponse(
        id=notification.id,
        queue_item_id=notification.queue_item_id,
        customer_id=notification.customer_id,
        business_id=notification.business_id,
        notification_type=notification.notification_type,
        recipient_phone=notification.recipient_phone,
        recipient_email=notification.recipient_email,
        message_template=notification.message_template,
        message_body=notification.message_body,
        status=notification.status,
        retry_count=notification.retry_count,
        max_retries=notification.max_retries,
        external_id=notification.external_id,
        error_message=notification.error_message,
        sent_at=notification.sent_at,
        delivered_at=notification.delivered_at,
        read_at=notification.read_at,
        created_at=notification.created_at,
        updated_at=notification.updated_at
    )


@router.post("/resend", response_model=NotificationResponse)
async def resend_notification(
    resend_data: NotificationResend,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Manually resend a failed notification.
    
    Args:
        resend_data: Notification resend data
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Updated notification
    """
    # Verify user has access
    from app.models.business import UserBusiness
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business"
        )
    
    # Verify notification belongs to business
    notification = db.query(Notification).filter(
        Notification.id == resend_data.notification_id,
        Notification.business_id == current_business.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Check if notification is in a retryable state
    if notification.status != NotificationStatus.FAILED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot resend notification with status: {notification.status}"
        )
    
    # Retry notification
    notification_service = NotificationService(db)
    updated_notification = notification_service.retry_failed_notification(
        resend_data.notification_id
    )
    
    if not updated_notification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot resend notification (max retries reached or invalid status)"
        )
    
    return NotificationResponse(
        id=updated_notification.id,
        queue_item_id=updated_notification.queue_item_id,
        customer_id=updated_notification.customer_id,
        business_id=updated_notification.business_id,
        notification_type=updated_notification.notification_type,
        recipient_phone=updated_notification.recipient_phone,
        recipient_email=updated_notification.recipient_email,
        message_template=updated_notification.message_template,
        message_body=updated_notification.message_body,
        status=updated_notification.status,
        retry_count=updated_notification.retry_count,
        max_retries=updated_notification.max_retries,
        external_id=updated_notification.external_id,
        error_message=updated_notification.error_message,
        sent_at=updated_notification.sent_at,
        delivered_at=updated_notification.delivered_at,
        read_at=updated_notification.read_at,
        created_at=updated_notification.created_at,
        updated_at=updated_notification.updated_at
    )


@router.post("/retry-failed", status_code=status.HTTP_202_ACCEPTED)
async def retry_all_failed_notifications(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Retry all failed notifications (runs in background).
    
    Args:
        background_tasks: FastAPI background tasks
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Confirmation message
    """
    # Verify user has access
    from app.models.business import UserBusiness
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business"
        )
    
    # Add background task
    background_tasks.add_task(
        retry_failed_notifications_background,
        db,
        current_business.id
    )
    
    return {
        "message": "Retry task started in background",
        "business_id": str(current_business.id)
    }


@router.get("/", response_model=List[NotificationResponse])
async def list_notifications(
    queue_item_id: Optional[UUID] = None,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    List notifications for the business.
    
    Args:
        queue_item_id: Optional filter by queue item
        status_filter: Optional filter by status
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        List of notifications
    """
    # Verify user has access
    from app.models.business import UserBusiness
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business"
        )
    
    # Build query
    query = db.query(Notification).filter(
        Notification.business_id == current_business.id
    )
    
    if queue_item_id:
        query = query.filter(Notification.queue_item_id == queue_item_id)
    
    if status_filter:
        query = query.filter(Notification.status == status_filter)
    
    notifications = query.order_by(Notification.created_at.desc()).all()
    
    return [
        NotificationResponse(
            id=n.id,
            queue_item_id=n.queue_item_id,
            customer_id=n.customer_id,
            business_id=n.business_id,
            notification_type=n.notification_type,
            recipient_phone=n.recipient_phone,
            recipient_email=n.recipient_email,
            message_template=n.message_template,
            message_body=n.message_body,
            status=n.status,
            retry_count=n.retry_count,
            max_retries=n.max_retries,
            external_id=n.external_id,
            error_message=n.error_message,
            sent_at=n.sent_at,
            delivered_at=n.delivered_at,
            read_at=n.read_at,
            created_at=n.created_at,
            updated_at=n.updated_at
        )
        for n in notifications
    ]


@router.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Get a specific notification.
    
    Args:
        notification_id: Notification ID
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Notification details
    """
    # Verify user has access
    from app.models.business import UserBusiness
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business"
        )
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.business_id == current_business.id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return NotificationResponse(
        id=notification.id,
        queue_item_id=notification.queue_item_id,
        customer_id=notification.customer_id,
        business_id=notification.business_id,
        notification_type=notification.notification_type,
        recipient_phone=notification.recipient_phone,
        recipient_email=notification.recipient_email,
        message_template=notification.message_template,
        message_body=notification.message_body,
        status=notification.status,
        retry_count=notification.retry_count,
        max_retries=notification.max_retries,
        external_id=notification.external_id,
        error_message=notification.error_message,
        sent_at=notification.sent_at,
        delivered_at=notification.delivered_at,
        read_at=notification.read_at,
        created_at=notification.created_at,
        updated_at=notification.updated_at
    )

