from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.business_dependencies import (
    get_current_business,
    get_user_business_relationship,
    require_any_role
)
from app.models.user import User
from app.models.business import Business
from app.models.customer import Customer
from app.models.queue import QueueItem, QueueType, QueueItemStatus, Counter
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.queue_service import QueueService

router = APIRouter()


def get_next_position(
    db: Session,
    business_id: UUID,
    queue_type: QueueType
) -> int:
    """
    Get the next position in the queue for a given queue type.
    Positions are assigned at the end of the queue.
    
    Args:
        db: Database session
        business_id: Business ID
        queue_type: Type of queue (NORMAL or EMERGENCY)
    
    Returns:
        Next position number (1-based)
    """
    # Get the maximum position for active queue items (WAITING or NOTIFIED)
    max_position = db.query(func.max(QueueItem.position)).filter(
        QueueItem.business_id == business_id,
        QueueItem.queue_type == queue_type,
        QueueItem.status.in_([QueueItemStatus.WAITING, QueueItemStatus.NOTIFIED])
    ).scalar()
    
    # If no active items, start at position 1
    if max_position is None:
        return 1
    
    return max_position + 1


def find_or_create_customer(
    db: Session,
    booking_data: BookingCreate,
    business_id: UUID
) -> Customer:
    """
    Find existing customer by phone and business or create a new one.
    
    Args:
        db: Database session
        booking_data: Booking creation data
        business_id: Business ID
    
    Returns:
        Customer object
    """
    # Try to find existing customer by phone and business
    customer = db.query(Customer).filter(
        Customer.phone == booking_data.phone,
        Customer.business_id == business_id
    ).first()
    
    if customer:
        # Update customer info if provided
        if booking_data.email and not customer.email:
            customer.email = booking_data.email
        if booking_data.firstname:
            customer.firstname = booking_data.firstname
        if booking_data.lastname:
            customer.lastname = booking_data.lastname
        if booking_data.whatsapp_enabled is not None:
            customer.whatsapp_enabled = booking_data.whatsapp_enabled
        return customer
    
    # Create new customer
    customer = Customer(
        firstname=booking_data.firstname,
        lastname=booking_data.lastname,
        email=booking_data.email,
        phone=booking_data.phone,
        whatsapp_enabled=booking_data.whatsapp_enabled,
        business_id=business_id
    )
    
    db.add(customer)
    db.flush()  # Flush to get the customer ID
    
    return customer


@router.post("/book", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_normal_booking(
    booking_data: BookingCreate,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Create a normal booking.
    Assigns position at the end of the normal queue.
    
    Args:
        booking_data: Booking creation data
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Created booking with queue position
    
    Raises:
        HTTPException: If validation fails or counter not found
    """
    # Verify user has access to this business
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
    
    # Validate counter if provided
    if booking_data.counter_id:
        counter = db.query(Counter).filter(
            Counter.id == booking_data.counter_id,
            Counter.business_id == current_business.id,
            Counter.is_active == True
        ).first()
        
        if not counter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Counter not found or inactive"
            )
    
    # Ensure queue_type is NORMAL for normal booking
    if booking_data.queue_type != QueueType.NORMAL:
        booking_data.queue_type = QueueType.NORMAL
    
    # Find or create customer
    customer = find_or_create_customer(db, booking_data, current_business.id)
    
    # Get next position in queue
    position = get_next_position(db, current_business.id, booking_data.queue_type)
    
    # Create queue item
    queue_item = QueueItem(
        business_id=current_business.id,
        customer_id=customer.id,
        counter_id=booking_data.counter_id,
        queue_type=booking_data.queue_type,
        position=position,
        status=QueueItemStatus.WAITING,
        miss_count=0
    )
    
    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)
    db.refresh(customer)
    
    return BookingResponse(
        id=queue_item.id,
        customer_id=queue_item.customer_id,
        business_id=queue_item.business_id,
        counter_id=queue_item.counter_id,
        queue_type=queue_item.queue_type,
        position=queue_item.position,
        status=queue_item.status,
        miss_count=queue_item.miss_count,
        created_at=queue_item.created_at,
        updated_at=queue_item.updated_at,
        customer_firstname=customer.firstname,
        customer_lastname=customer.lastname,
        customer_phone=customer.phone,
        customer_email=customer.email
    )


@router.post("/book/emergency", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_emergency_booking(
    booking_data: BookingCreate,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Create an emergency booking.
    Emergency bookings are assigned at the end of the emergency queue.
    
    Args:
        booking_data: Booking creation data
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Created emergency booking with queue position
    
    Raises:
        HTTPException: If validation fails or counter not found
    """
    # Verify user has access to this business
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
    
    # Validate counter if provided
    if booking_data.counter_id:
        counter = db.query(Counter).filter(
            Counter.id == booking_data.counter_id,
            Counter.business_id == current_business.id,
            Counter.is_active == True
        ).first()
        
        if not counter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Counter not found or inactive"
            )
    
    # Force queue_type to EMERGENCY
    booking_data.queue_type = QueueType.EMERGENCY
    
    # Find or create customer
    customer = find_or_create_customer(db, booking_data, current_business.id)
    
    # Get next position in emergency queue
    position = get_next_position(db, current_business.id, QueueType.EMERGENCY)
    
    # Create queue item
    queue_item = QueueItem(
        business_id=current_business.id,
        customer_id=customer.id,
        counter_id=booking_data.counter_id,
        queue_type=QueueType.EMERGENCY,
        position=position,
        status=QueueItemStatus.WAITING,
        miss_count=0
    )
    
    db.add(queue_item)
    db.commit()
    db.refresh(queue_item)
    db.refresh(customer)
    
    return BookingResponse(
        id=queue_item.id,
        customer_id=queue_item.customer_id,
        business_id=queue_item.business_id,
        counter_id=queue_item.counter_id,
        queue_type=queue_item.queue_type,
        position=queue_item.position,
        status=queue_item.status,
        miss_count=queue_item.miss_count,
        created_at=queue_item.created_at,
        updated_at=queue_item.updated_at,
        customer_firstname=customer.firstname,
        customer_lastname=customer.lastname,
        customer_phone=customer.phone,
        customer_email=customer.email
    )


@router.get("/", response_model=List[BookingResponse])
async def list_queue(
    queue_type: Optional[QueueType] = None,
    status_filter: Optional[QueueItemStatus] = None,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    List queue items for the business.
    All staff members can view the queue.
    
    Args:
        queue_type: Optional filter by queue type (NORMAL or EMERGENCY)
        status_filter: Optional filter by status
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        List of queue items
    """
    # Verify user has access to this business
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
    query = db.query(QueueItem).filter(
        QueueItem.business_id == current_business.id
    )
    
    if queue_type:
        query = query.filter(QueueItem.queue_type == queue_type)
    
    if status_filter:
        query = query.filter(QueueItem.status == status_filter)
    
    # Order by position
    queue_items = query.order_by(QueueItem.position).all()
    
    # Build response
    result = []
    for item in queue_items:
        result.append(BookingResponse(
            id=item.id,
            customer_id=item.customer_id,
            business_id=item.business_id,
            counter_id=item.counter_id,
            queue_type=item.queue_type,
            position=item.position,
            status=item.status,
            miss_count=item.miss_count,
            created_at=item.created_at,
            updated_at=item.updated_at,
            customer_firstname=item.customer.firstname,
            customer_lastname=item.customer.lastname,
            customer_phone=item.customer.phone,
            customer_email=item.customer.email
        ))
    
    return result


@router.post("/serve/next", response_model=BookingResponse)
async def serve_next_customer(
    counter_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Serve the next customer based on the smart queue pattern:
    - Serves 2 emergency customers, then 1 normal customer
    - Uses atomic operations with row-level locking for safe concurrency
    
    Args:
        counter_id: Optional counter ID to filter by
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Served customer booking
    
    Raises:
        HTTPException: If no customers in queue or access denied
    """
    # Verify user has access to this business
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
    
    # Validate counter if provided
    if counter_id:
        counter = db.query(Counter).filter(
            Counter.id == counter_id,
            Counter.business_id == current_business.id,
            Counter.is_active == True
        ).first()
        
        if not counter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Counter not found or inactive"
            )
    
    # Get next customer using queue service
    queue_service = QueueService(db)
    next_item = queue_service.get_next_customer(current_business.id, counter_id)
    
    if not next_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No customers waiting in queue"
        )
    
    # Serve the customer (atomic operation)
    served_item = queue_service.serve_customer(next_item.id, counter_id)
    
    if not served_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to serve customer"
        )
    
    db.refresh(served_item)
    
    return BookingResponse(
        id=served_item.id,
        customer_id=served_item.customer_id,
        business_id=served_item.business_id,
        counter_id=served_item.counter_id,
        queue_type=served_item.queue_type,
        position=served_item.position,
        status=served_item.status,
        miss_count=served_item.miss_count,
        created_at=served_item.created_at,
        updated_at=served_item.updated_at,
        customer_firstname=served_item.customer.firstname,
        customer_lastname=served_item.customer.lastname,
        customer_phone=served_item.customer.phone,
        customer_email=served_item.customer.email
    )


@router.post("/{queue_item_id}/notify", response_model=BookingResponse)
async def notify_customer(
    queue_item_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Notify a customer that they're next in line.
    State transition: WAITING -> NOTIFIED
    
    Args:
        queue_item_id: Queue item ID
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Updated booking with NOTIFIED status
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
    queue_item = db.query(QueueItem).filter(
        QueueItem.id == queue_item_id,
        QueueItem.business_id == current_business.id
    ).first()
    
    if not queue_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue item not found"
        )
    
    # Notify customer (atomic operation)
    queue_service = QueueService(db)
    notified_item = queue_service.notify_customer(queue_item_id)
    
    if not notified_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer cannot be notified (invalid status)"
        )
    
    db.refresh(notified_item)
    
    return BookingResponse(
        id=notified_item.id,
        customer_id=notified_item.customer_id,
        business_id=notified_item.business_id,
        counter_id=notified_item.counter_id,
        queue_type=notified_item.queue_type,
        position=notified_item.position,
        status=notified_item.status,
        miss_count=notified_item.miss_count,
        created_at=notified_item.created_at,
        updated_at=notified_item.updated_at,
        customer_firstname=notified_item.customer.firstname,
        customer_lastname=notified_item.customer.lastname,
        customer_phone=notified_item.customer.phone,
        customer_email=notified_item.customer.email
    )


@router.post("/{queue_item_id}/miss", response_model=BookingResponse)
async def handle_customer_miss(
    queue_item_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Handle a missed customer appointment.
    - First miss: move to bottom of queue
    - Second miss: cancel the booking
    
    Args:
        queue_item_id: Queue item ID
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Updated booking
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
    queue_item = db.query(QueueItem).filter(
        QueueItem.id == queue_item_id,
        QueueItem.business_id == current_business.id
    ).first()
    
    if not queue_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue item not found"
        )
    
    # Handle miss (atomic operation)
    queue_service = QueueService(db)
    updated_item = queue_service.handle_miss(queue_item_id)
    
    if not updated_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot handle miss (invalid status)"
        )
    
    db.refresh(updated_item)
    
    return BookingResponse(
        id=updated_item.id,
        customer_id=updated_item.customer_id,
        business_id=updated_item.business_id,
        counter_id=updated_item.counter_id,
        queue_type=updated_item.queue_type,
        position=updated_item.position,
        status=updated_item.status,
        miss_count=updated_item.miss_count,
        created_at=updated_item.created_at,
        updated_at=updated_item.updated_at,
        customer_firstname=updated_item.customer.firstname,
        customer_lastname=updated_item.customer.lastname,
        customer_phone=updated_item.customer.phone,
        customer_email=updated_item.customer.email
    )


@router.post("/{queue_item_id}/cancel", response_model=BookingResponse)
async def cancel_booking(
    queue_item_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Cancel a booking (manual cancellation).
    State transition: WAITING/NOTIFIED -> CANCELLED
    
    Args:
        queue_item_id: Queue item ID
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Cancelled booking
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
    queue_item = db.query(QueueItem).filter(
        QueueItem.id == queue_item_id,
        QueueItem.business_id == current_business.id
    ).first()
    
    if not queue_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Queue item not found"
        )
    
    # Cancel booking (atomic operation)
    queue_service = QueueService(db)
    cancelled_item = queue_service.cancel_booking(queue_item_id)
    
    if not cancelled_item:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel booking (invalid status)"
        )
    
    db.refresh(cancelled_item)
    
    return BookingResponse(
        id=cancelled_item.id,
        customer_id=cancelled_item.customer_id,
        business_id=cancelled_item.business_id,
        counter_id=cancelled_item.counter_id,
        queue_type=cancelled_item.queue_type,
        position=cancelled_item.position,
        status=cancelled_item.status,
        miss_count=cancelled_item.miss_count,
        created_at=cancelled_item.created_at,
        updated_at=cancelled_item.updated_at,
        customer_firstname=cancelled_item.customer.firstname,
        customer_lastname=cancelled_item.customer.lastname,
        customer_phone=cancelled_item.customer.phone,
        customer_email=cancelled_item.customer.email
    )


@router.get("/stats", response_model=dict)
async def get_queue_stats(
    counter_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Get queue statistics.
    
    Args:
        counter_id: Optional counter ID to filter by
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Queue statistics
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
    
    queue_service = QueueService(db)
    stats = queue_service.get_queue_stats(current_business.id, counter_id)
    
    return stats
