from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.business_dependencies import get_current_business, require_owner_or_manager
from app.models.user import User
from app.models.business import Business
from app.models.queue import Counter
from app.schemas.counter import CounterCreate, CounterUpdate, CounterResponse

router = APIRouter()


@router.post("/", response_model=CounterResponse, status_code=status.HTTP_201_CREATED)
async def create_counter(
    counter_data: CounterCreate,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    _: None = Depends(require_owner_or_manager),
    db: Session = Depends(get_db)
):
    """
    Create a new counter for the business.
    Only OWNER or MANAGER can create counters.
    
    Args:
        counter_data: Counter creation data
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Created counter
    
    Raises:
        HTTPException: If user doesn't have permission or validation fails
    """
    # Check if counter with same name already exists for this business
    existing_counter = db.query(Counter).filter(
        Counter.business_id == current_business.id,
        Counter.name == counter_data.name
    ).first()
    
    if existing_counter:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Counter with name '{counter_data.name}' already exists for this business"
        )
    
    # Create counter
    counter = Counter(
        name=counter_data.name,
        business_id=current_business.id,
        is_active=counter_data.is_active
    )
    
    db.add(counter)
    db.commit()
    db.refresh(counter)
    
    return CounterResponse(
        id=counter.id,
        name=counter.name,
        business_id=counter.business_id,
        is_active=counter.is_active,
        created_at=counter.created_at,
        updated_at=counter.updated_at
    )


@router.get("/", response_model=List[CounterResponse])
async def list_counters(
    include_inactive: bool = False,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    List all counters for the business.
    
    Args:
        include_inactive: Whether to include inactive counters
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        List of counters
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
    
    query = db.query(Counter).filter(Counter.business_id == current_business.id)
    
    if not include_inactive:
        query = query.filter(Counter.is_active == True)
    
    counters = query.order_by(Counter.name.asc()).all()
    
    return [
        CounterResponse(
            id=counter.id,
            name=counter.name,
            business_id=counter.business_id,
            is_active=counter.is_active,
            created_at=counter.created_at,
            updated_at=counter.updated_at
        )
        for counter in counters
    ]


@router.get("/{counter_id}", response_model=CounterResponse)
async def get_counter(
    counter_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Get a specific counter by ID.
    
    Args:
        counter_id: Counter ID
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Counter details
    
    Raises:
        HTTPException: If counter not found or doesn't belong to business
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
    
    counter = db.query(Counter).filter(
        Counter.id == counter_id,
        Counter.business_id == current_business.id
    ).first()
    
    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counter not found"
        )
    
    return CounterResponse(
        id=counter.id,
        name=counter.name,
        business_id=counter.business_id,
        is_active=counter.is_active,
        created_at=counter.created_at,
        updated_at=counter.updated_at
    )


@router.put("/{counter_id}", response_model=CounterResponse)
async def update_counter(
    counter_id: UUID,
    counter_data: CounterUpdate,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    _: None = Depends(require_owner_or_manager),
    db: Session = Depends(get_db)
):
    """
    Update a counter.
    Only OWNER or MANAGER can update counters.
    
    Args:
        counter_id: Counter ID
        counter_data: Counter update data
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Updated counter
    
    Raises:
        HTTPException: If counter not found or validation fails
    """
    counter = db.query(Counter).filter(
        Counter.id == counter_id,
        Counter.business_id == current_business.id
    ).first()
    
    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counter not found"
        )
    
    # Check if name is being changed and if new name already exists
    if counter_data.name and counter_data.name != counter.name:
        existing_counter = db.query(Counter).filter(
            Counter.business_id == current_business.id,
            Counter.name == counter_data.name,
            Counter.id != counter_id
        ).first()
        
        if existing_counter:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Counter with name '{counter_data.name}' already exists for this business"
            )
    
    # Update fields
    if counter_data.name is not None:
        counter.name = counter_data.name
    if counter_data.is_active is not None:
        counter.is_active = counter_data.is_active
    
    db.commit()
    db.refresh(counter)
    
    return CounterResponse(
        id=counter.id,
        name=counter.name,
        business_id=counter.business_id,
        is_active=counter.is_active,
        created_at=counter.created_at,
        updated_at=counter.updated_at
    )


@router.delete("/{counter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_counter(
    counter_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    _: None = Depends(require_owner_or_manager),
    db: Session = Depends(get_db)
):
    """
    Delete a counter.
    Only OWNER or MANAGER can delete counters.
    
    Args:
        counter_id: Counter ID
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Raises:
        HTTPException: If counter not found or has active queue items
    """
    counter = db.query(Counter).filter(
        Counter.id == counter_id,
        Counter.business_id == current_business.id
    ).first()
    
    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counter not found"
        )
    
    # Check if counter has active queue items
    from app.models.queue import QueueItem, QueueItemStatus
    active_queue_items = db.query(QueueItem).filter(
        QueueItem.counter_id == counter_id,
        QueueItem.status.in_([QueueItemStatus.WAITING, QueueItemStatus.NOTIFIED])
    ).count()
    
    if active_queue_items > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete counter with {active_queue_items} active queue items. Please serve or cancel them first."
        )
    
    db.delete(counter)
    db.commit()
    
    return None

