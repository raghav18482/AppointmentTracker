from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, case

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.business_dependencies import get_current_business
from app.models.user import User
from app.models.business import Business
from app.models.queue import QueueItem, QueueItemStatus, QueueType, Counter
from app.models.notification import Notification, NotificationStatus
from app.models.customer import Customer
from app.schemas.dashboard import (
    DashboardStats,
    QueueItemSummary,
    MissedCustomerSummary,
    FailedNotificationSummary,
    CounterActivitySummary,
    LiveQueueView
)

router = APIRouter()


@router.get("/live-queue", response_model=LiveQueueView)
async def get_live_queue_view(
    counter_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Get live queue view with all dashboard data.
    Optimized read-only endpoint for admin dashboards.
    
    Args:
        counter_id: Optional counter ID to filter by
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Complete dashboard view with stats, queue items, missed customers, etc.
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
    
    # Build base query filter
    base_filter = QueueItem.business_id == current_business.id
    if counter_id:
        base_filter = and_(
            base_filter,
            or_(
                QueueItem.counter_id == counter_id,
                QueueItem.counter_id.is_(None)
            )
        )
    
    # Get queue items (WAITING and NOTIFIED only)
    queue_items_query = db.query(QueueItem).filter(
        base_filter,
        QueueItem.status.in_([QueueItemStatus.WAITING, QueueItemStatus.NOTIFIED])
    ).order_by(
        QueueItem.queue_type.desc(),  # Emergency first
        QueueItem.position.asc()
    )
    
    queue_items = queue_items_query.all()
    
    # Calculate wait time for each item
    now = datetime.utcnow()
    queue_item_summaries = []
    for item in queue_items:
        wait_time = (now - item.created_at).total_seconds() / 60  # minutes
        queue_item_summaries.append(QueueItemSummary(
            id=item.id,
            position=item.position,
            queue_type=item.queue_type,
            status=item.status,
            customer_name=f"{item.customer.firstname} {item.customer.lastname}",
            customer_phone=item.customer.phone,
            counter_name=item.counter.name if item.counter else None,
            wait_time_minutes=int(wait_time),
            created_at=item.created_at
        ))
    
    # Get missed customers (today)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    missed_items = db.query(QueueItem).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.MISSED,
        QueueItem.updated_at >= today_start
    ).order_by(QueueItem.updated_at.desc()).all()
    
    missed_summaries = []
    for item in missed_items:
        missed_summaries.append(MissedCustomerSummary(
            id=item.customer.id,
            queue_item_id=item.id,
            customer_name=f"{item.customer.firstname} {item.customer.lastname}",
            customer_phone=item.customer.phone,
            miss_count=item.miss_count,
            last_missed_at=item.updated_at,
            queue_type=item.queue_type,
            position=item.position
        ))
    
    # Get failed notifications
    failed_notifications = db.query(Notification).filter(
        Notification.business_id == current_business.id,
        Notification.status == NotificationStatus.FAILED,
        Notification.retry_count < Notification.max_retries
    ).order_by(Notification.updated_at.desc()).all()
    
    failed_notification_summaries = []
    for notif in failed_notifications:
        failed_notification_summaries.append(FailedNotificationSummary(
            id=notif.id,
            queue_item_id=notif.queue_item_id,
            customer_name=f"{notif.customer.firstname} {notif.customer.lastname}",
            customer_phone=notif.customer.phone,
            retry_count=notif.retry_count,
            max_retries=notif.max_retries,
            error_message=notif.error_message,
            failed_at=notif.updated_at,
            last_retry_at=notif.updated_at if notif.retry_count > 0 else None
        ))
    
    # Get counter activity
    counters = db.query(Counter).filter(
        Counter.business_id == current_business.id,
        Counter.is_active == True
    ).all()
    
    counter_activity_summaries = []
    for counter in counters:
        counter_filter = and_(
            base_filter,
            QueueItem.counter_id == counter.id
        )
        
        # Count served today
        served_today = db.query(func.count(QueueItem.id)).filter(
            counter_filter,
            QueueItem.status == QueueItemStatus.SERVED,
            QueueItem.updated_at >= today_start
        ).scalar() or 0
        
        # Count waiting
        waiting_count = db.query(func.count(QueueItem.id)).filter(
            counter_filter,
            QueueItem.status.in_([QueueItemStatus.WAITING, QueueItemStatus.NOTIFIED])
        ).scalar() or 0
        
        # Get currently serving (NOTIFIED status)
        currently_serving = db.query(QueueItem).filter(
            counter_filter,
            QueueItem.status == QueueItemStatus.NOTIFIED
        ).order_by(QueueItem.updated_at.desc()).first()
        
        # Get last served
        last_served = db.query(QueueItem).filter(
            counter_filter,
            QueueItem.status == QueueItemStatus.SERVED
        ).order_by(QueueItem.updated_at.desc()).first()
        
        counter_activity_summaries.append(CounterActivitySummary(
            counter_id=counter.id,
            counter_name=counter.name,
            total_served_today=served_today,
            currently_serving=currently_serving.id if currently_serving else None,
            waiting_count=waiting_count,
            last_served_at=last_served.updated_at if last_served else None
        ))
    
    # Calculate stats
    total_waiting = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.WAITING
    ).scalar() or 0
    
    total_notified = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.NOTIFIED
    ).scalar() or 0
    
    total_served_today = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.SERVED,
        QueueItem.updated_at >= today_start
    ).scalar() or 0
    
    total_missed_today = len(missed_summaries)
    
    total_failed_notifications = len(failed_notification_summaries)
    
    emergency_waiting = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.WAITING,
        QueueItem.queue_type == QueueType.EMERGENCY
    ).scalar() or 0
    
    normal_waiting = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.WAITING,
        QueueItem.queue_type == QueueType.NORMAL
    ).scalar() or 0
    
    active_counters = len(counter_activity_summaries)
    
    stats = DashboardStats(
        total_waiting=total_waiting,
        total_notified=total_notified,
        total_served_today=total_served_today,
        total_missed_today=total_missed_today,
        total_failed_notifications=total_failed_notifications,
        emergency_waiting=emergency_waiting,
        normal_waiting=normal_waiting,
        active_counters=active_counters
    )
    
    return LiveQueueView(
        stats=stats,
        queue_items=queue_item_summaries,
        missed_customers=missed_summaries,
        failed_notifications=failed_notification_summaries,
        counter_activity=counter_activity_summaries
    )


@router.get("/missed-customers", response_model=List[MissedCustomerSummary])
async def get_missed_customers(
    days: int = 1,
    counter_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Get missed customers.
    
    Args:
        days: Number of days to look back (default: 1)
        counter_id: Optional counter ID to filter by
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        List of missed customers
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
    
    # Calculate date range
    date_from = datetime.utcnow() - timedelta(days=days)
    
    # Build query
    query = db.query(QueueItem).filter(
        QueueItem.business_id == current_business.id,
        QueueItem.status == QueueItemStatus.MISSED,
        QueueItem.updated_at >= date_from
    )
    
    if counter_id:
        query = query.filter(QueueItem.counter_id == counter_id)
    
    missed_items = query.order_by(QueueItem.updated_at.desc()).all()
    
    return [
        MissedCustomerSummary(
            id=item.customer.id,
            queue_item_id=item.id,
            customer_name=f"{item.customer.firstname} {item.customer.lastname}",
            customer_phone=item.customer.phone,
            miss_count=item.miss_count,
            last_missed_at=item.updated_at,
            queue_type=item.queue_type,
            position=item.position
        )
        for item in missed_items
    ]


@router.get("/failed-notifications", response_model=List[FailedNotificationSummary])
async def get_failed_notifications(
    retryable_only: bool = True,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Get failed notifications.
    
    Args:
        retryable_only: Only show notifications that can still be retried
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        List of failed notifications
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
        Notification.business_id == current_business.id,
        Notification.status == NotificationStatus.FAILED
    )
    
    if retryable_only:
        query = query.filter(Notification.retry_count < Notification.max_retries)
    
    failed_notifications = query.order_by(Notification.updated_at.desc()).all()
    
    return [
        FailedNotificationSummary(
            id=notif.id,
            queue_item_id=notif.queue_item_id,
            customer_name=f"{notif.customer.firstname} {notif.customer.lastname}",
            customer_phone=notif.customer.phone,
            retry_count=notif.retry_count,
            max_retries=notif.max_retries,
            error_message=notif.error_message,
            failed_at=notif.updated_at,
            last_retry_at=notif.updated_at if notif.retry_count > 0 else None
        )
        for notif in failed_notifications
    ]


@router.get("/counter-activity", response_model=List[CounterActivitySummary])
async def get_counter_activity(
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Get counter activity summary.
    
    Args:
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        List of counter activity summaries
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
    
    # Get all active counters
    counters = db.query(Counter).filter(
        Counter.business_id == current_business.id,
        Counter.is_active == True
    ).all()
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    counter_activity_summaries = []
    for counter in counters:
        # Count served today
        served_today = db.query(func.count(QueueItem.id)).filter(
            QueueItem.business_id == current_business.id,
            QueueItem.counter_id == counter.id,
            QueueItem.status == QueueItemStatus.SERVED,
            QueueItem.updated_at >= today_start
        ).scalar() or 0
        
        # Count waiting
        waiting_count = db.query(func.count(QueueItem.id)).filter(
            QueueItem.business_id == current_business.id,
            QueueItem.counter_id == counter.id,
            QueueItem.status.in_([QueueItemStatus.WAITING, QueueItemStatus.NOTIFIED])
        ).scalar() or 0
        
        # Get currently serving (NOTIFIED status)
        currently_serving = db.query(QueueItem).filter(
            QueueItem.business_id == current_business.id,
            QueueItem.counter_id == counter.id,
            QueueItem.status == QueueItemStatus.NOTIFIED
        ).order_by(QueueItem.updated_at.desc()).first()
        
        # Get last served
        last_served = db.query(QueueItem).filter(
            QueueItem.business_id == current_business.id,
            QueueItem.counter_id == counter.id,
            QueueItem.status == QueueItemStatus.SERVED
        ).order_by(QueueItem.updated_at.desc()).first()
        
        counter_activity_summaries.append(CounterActivitySummary(
            counter_id=counter.id,
            counter_name=counter.name,
            total_served_today=served_today,
            currently_serving=currently_serving.id if currently_serving else None,
            waiting_count=waiting_count,
            last_served_at=last_served.updated_at if last_served else None
        ))
    
    return counter_activity_summaries


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    counter_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Get dashboard statistics only (lightweight endpoint).
    
    Args:
        counter_id: Optional counter ID to filter by
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Dashboard statistics
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
    
    # Build base filter
    base_filter = QueueItem.business_id == current_business.id
    if counter_id:
        base_filter = and_(
            base_filter,
            or_(
                QueueItem.counter_id == counter_id,
                QueueItem.counter_id.is_(None)
            )
        )
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Get all stats in optimized queries
    total_waiting = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.WAITING
    ).scalar() or 0
    
    total_notified = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.NOTIFIED
    ).scalar() or 0
    
    total_served_today = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.SERVED,
        QueueItem.updated_at >= today_start
    ).scalar() or 0
    
    total_missed_today = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.MISSED,
        QueueItem.updated_at >= today_start
    ).scalar() or 0
    
    total_failed_notifications = db.query(func.count(Notification.id)).filter(
        Notification.business_id == current_business.id,
        Notification.status == NotificationStatus.FAILED,
        Notification.retry_count < Notification.max_retries
    ).scalar() or 0
    
    emergency_waiting = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.WAITING,
        QueueItem.queue_type == QueueType.EMERGENCY
    ).scalar() or 0
    
    normal_waiting = db.query(func.count(QueueItem.id)).filter(
        base_filter,
        QueueItem.status == QueueItemStatus.WAITING,
        QueueItem.queue_type == QueueType.NORMAL
    ).scalar() or 0
    
    active_counters = db.query(func.count(Counter.id)).filter(
        Counter.business_id == current_business.id,
        Counter.is_active == True
    ).scalar() or 0
    
    return DashboardStats(
        total_waiting=total_waiting,
        total_notified=total_notified,
        total_served_today=total_served_today,
        total_missed_today=total_missed_today,
        total_failed_notifications=total_failed_notifications,
        emergency_waiting=emergency_waiting,
        normal_waiting=normal_waiting,
        active_counters=active_counters
    )

