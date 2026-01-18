from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.business_dependencies import (
    get_current_business,
    get_user_business_relationship,
    require_owner,
    require_any_role
)
from app.models.user import User
from app.models.business import Business, UserBusiness, UserRole
from app.schemas.business import (
    BusinessCreate,
    BusinessResponse,
    BusinessUpdate,
    UserBusinessCreate,
    UserBusinessResponse,
    BusinessWithRoleResponse
)

router = APIRouter()


@router.post("/", response_model=BusinessResponse, status_code=status.HTTP_201_CREATED)
async def create_business(
    business_data: BusinessCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Create a new business and assign the creator as OWNER.
    
    Args:
        business_data: Business creation data
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        Created business object
    """
    # Create business
    db_business = Business(
        name=business_data.name,
        type=business_data.type,
        timezone=business_data.timezone
    )
    
    db.add(db_business)
    db.flush()  # Flush to get the business ID
    
    # Create user-business relationship with OWNER role
    user_business = UserBusiness(
        user_id=current_user.id,
        business_id=db_business.id,
        role=UserRole.OWNER
    )
    
    db.add(user_business)
    db.commit()
    db.refresh(db_business)
    
    return db_business


@router.post("/{business_id}/users", response_model=UserBusinessResponse, status_code=status.HTTP_201_CREATED)
async def add_user_to_business(
    business_id: UUID,
    user_business_data: UserBusinessCreate,
    current_user_business: UserBusiness = Depends(require_owner),
    db: Session = Depends(get_db)
):
    """
    Add a user to a business with a specific role.
    Only business owners can add users.
    
    Args:
        business_id: Business ID
        user_business_data: User and role information
        current_user_business: Current user's relationship with business (must be OWNER)
        db: Database session
    
    Returns:
        Created user-business relationship
    
    Raises:
        HTTPException: If user or business not found, or user already in business
    """
    # The dependency already validates that the user is an owner of the business
    # We just need to ensure the business_id in the path matches
    if str(current_user_business.business_id) != str(business_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business ID mismatch"
        )
    
    # Check if user exists
    user = db.query(User).filter(User.id == user_business_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is already in this business
    existing = db.query(UserBusiness).filter(
        UserBusiness.user_id == user_business_data.user_id,
        UserBusiness.business_id == business_id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already associated with this business"
        )
    
    # Create user-business relationship
    user_business = UserBusiness(
        user_id=user_business_data.user_id,
        business_id=business_id,
        role=user_business_data.role
    )
    
    db.add(user_business)
    db.commit()
    db.refresh(user_business)
    
    return user_business


@router.get("/my-businesses", response_model=List[BusinessWithRoleResponse])
async def list_user_businesses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    List all businesses associated with the current user.
    
    Args:
        current_user: Current authenticated user
        db: Database session
    
    Returns:
        List of businesses with user's role in each
    """
    user_businesses = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id
    ).all()
    
    result = []
    for ub in user_businesses:
        business_dict = {
            "id": ub.business.id,
            "name": ub.business.name,
            "type": ub.business.type,
            "timezone": ub.business.timezone,
            "created_at": ub.business.created_at,
            "updated_at": ub.business.updated_at,
            "role": ub.role
        }
        result.append(BusinessWithRoleResponse(**business_dict))
    
    return result


@router.get("/{business_id}", response_model=BusinessResponse)
async def get_business(
    business_id: UUID,
    user_business: UserBusiness = Depends(get_user_business_relationship),
    db: Session = Depends(get_db)
):
    """
    Get business details.
    User must have access to the business.
    
    Args:
        business_id: Business ID
        user_business: User's relationship with business (validates access)
        db: Database session
    
    Returns:
        Business details
    """
    return user_business.business


@router.put("/{business_id}", response_model=BusinessResponse)
async def update_business(
    business_id: UUID,
    business_data: BusinessUpdate,
    user_business: UserBusiness = Depends(require_owner),
    db: Session = Depends(get_db)
):
    """
    Update business details.
    Only business owners can update business information.
    
    Args:
        business_id: Business ID
        business_data: Business update data
        user_business: User's relationship with business (must be OWNER)
        db: Database session
    
    Returns:
        Updated business details
    """
    business = user_business.business
    
    if business_data.name is not None:
        business.name = business_data.name
    if business_data.type is not None:
        business.type = business_data.type
    if business_data.timezone is not None:
        business.timezone = business_data.timezone
    
    db.commit()
    db.refresh(business)
    
    return business


@router.delete("/{business_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_business(
    business_id: UUID,
    user_id: UUID,
    current_user_business: UserBusiness = Depends(require_owner),
    db: Session = Depends(get_db)
):
    """
    Remove a user from a business.
    Only business owners can remove users.
    Owners cannot remove themselves.
    
    Args:
        business_id: Business ID
        user_id: User ID to remove
        current_user_business: Current user's relationship (must be OWNER)
        db: Database session
    
    Raises:
        HTTPException: If trying to remove owner or user not found
    """
    if str(current_user_business.business_id) != str(business_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Business ID mismatch"
        )
    
    # Prevent owner from removing themselves
    if str(user_id) == str(current_user_business.user_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the business"
        )
    
    user_business = db.query(UserBusiness).filter(
        UserBusiness.business_id == business_id,
        UserBusiness.user_id == user_id
    ).first()
    
    if not user_business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not associated with this business"
        )
    
    db.delete(user_business)
    db.commit()
    
    return None

