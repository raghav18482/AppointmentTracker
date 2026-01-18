from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.business_dependencies import (
    get_current_business,
    get_user_business_relationship,
    require_role
)
from app.core.security import get_password_hash
from app.models.user import User
from app.models.business import Business, UserBusiness, UserRole
from app.schemas.staff import (
    StaffCreate,
    StaffCreateNew,
    StaffUpdate,
    StaffResponse,
    StaffDetailResponse
)

router = APIRouter()


@router.post("/create", response_model=StaffDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_staff(
    staff_data: StaffCreateNew,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Create a new staff member (creates user account and adds to business).
    Only OWNER and MANAGER can create staff.
    
    This endpoint:
    1. Creates a new user account with email and password
    2. Adds the user to the business with the specified role
    
    Args:
        staff_data: Staff creation data (email, password, and role)
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Created staff relationship with user details
    
    Raises:
        HTTPException: If user doesn't have permission, email already exists, or role assignment not allowed
    """
    # Check if current user has permission (OWNER or MANAGER)
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business or user_business.role not in [UserRole.OWNER, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and managers can create staff"
        )
    
    # Check if user with this email already exists
    existing_user = db.query(User).filter(User.email == staff_data.email).first()
    if existing_user:
        # Check if user is already in this business
        existing_staff = db.query(UserBusiness).filter(
            UserBusiness.user_id == existing_user.id,
            UserBusiness.business_id == current_business.id
        ).first()
        
        if existing_staff:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email is already a staff member in this business"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists. Use the add staff endpoint with user_id instead"
            )
    
    # Prevent non-owners from assigning OWNER or MANAGER roles
    if user_business.role != UserRole.OWNER and staff_data.role in [UserRole.OWNER, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can assign owner or manager roles"
        )
    
    # Create new user
    hashed_password = get_password_hash(staff_data.password)
    new_user = User(
        email=staff_data.email,
        password_hash=hashed_password,
        is_active=True
    )
    
    db.add(new_user)
    db.flush()  # Flush to get the user ID
    
    # Create user-business relationship
    user_business_new = UserBusiness(
        user_id=new_user.id,
        business_id=current_business.id,
        role=staff_data.role
    )
    
    db.add(user_business_new)
    db.commit()
    db.refresh(user_business_new)
    db.refresh(new_user)
    
    return StaffDetailResponse(
        id=user_business_new.id,
        user_id=user_business_new.user_id,
        business_id=user_business_new.business_id,
        role=user_business_new.role,
        created_at=user_business_new.created_at,
        updated_at=user_business_new.updated_at,
        user_email=new_user.email,
        user_is_active=new_user.is_active
    )


@router.post("/", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
async def add_staff(
    staff_data: StaffCreate,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Add staff to a business.
    Only OWNER and MANAGER can add staff.
    
    Args:
        staff_data: Staff creation data (user_id and role)
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Created staff relationship
    
    Raises:
        HTTPException: If user doesn't have permission, user not found, or user already in business
    """
    # Check if current user has permission (OWNER or MANAGER)
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business or user_business.role not in [UserRole.OWNER, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and managers can add staff"
        )
    
    # Check if user exists
    user = db.query(User).filter(User.id == staff_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if user is already in this business
    existing = db.query(UserBusiness).filter(
        UserBusiness.user_id == staff_data.user_id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already associated with this business"
        )
    
    # Prevent non-owners from assigning OWNER or MANAGER roles
    if user_business.role != UserRole.OWNER and staff_data.role in [UserRole.OWNER, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can assign owner or manager roles"
        )
    
    # Create user-business relationship
    user_business_new = UserBusiness(
        user_id=staff_data.user_id,
        business_id=current_business.id,
        role=staff_data.role
    )
    
    db.add(user_business_new)
    db.commit()
    db.refresh(user_business_new)
    
    return user_business_new


@router.put("/{staff_id}/role", response_model=StaffResponse)
async def update_staff_role(
    staff_id: UUID,
    staff_update: StaffUpdate,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Update staff role.
    Only OWNER and MANAGER can update staff roles.
    Only OWNER can assign OWNER or MANAGER roles.
    
    Args:
        staff_id: Staff relationship ID (UserBusiness ID)
        staff_update: New role
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        Updated staff relationship
    
    Raises:
        HTTPException: If permission denied or staff not found
    """
    # Check if current user has permission (OWNER or MANAGER)
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business or user_business.role not in [UserRole.OWNER, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and managers can update staff roles"
        )
    
    # Get the staff relationship to update
    staff_relationship = db.query(UserBusiness).filter(
        UserBusiness.id == staff_id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not staff_relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found in this business"
        )
    
    # Prevent non-owners from assigning OWNER or MANAGER roles
    if user_business.role != UserRole.OWNER and staff_update.role in [UserRole.OWNER, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can assign owner or manager roles"
        )
    
    # Prevent removing the last owner
    if staff_relationship.role == UserRole.OWNER and staff_update.role != UserRole.OWNER:
        owner_count = db.query(UserBusiness).filter(
            UserBusiness.business_id == current_business.id,
            UserBusiness.role == UserRole.OWNER
        ).count()
        
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner from the business"
            )
    
    # Update role
    staff_relationship.role = staff_update.role
    
    db.commit()
    db.refresh(staff_relationship)
    
    return staff_relationship


@router.get("/", response_model=List[StaffDetailResponse])
async def list_staff(
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    List all staff for a business.
    All staff members (OWNER, MANAGER, COUNTER) can view the staff list.
    
    Args:
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        List of staff members with details
    """
    # Verify user has access to this business
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business"
        )
    
    # Get all staff for this business
    staff_list = db.query(UserBusiness).filter(
        UserBusiness.business_id == current_business.id
    ).all()
    
    # Build response with user details
    result = []
    for staff in staff_list:
        result.append(StaffDetailResponse(
            id=staff.id,
            user_id=staff.user_id,
            business_id=staff.business_id,
            role=staff.role,
            created_at=staff.created_at,
            updated_at=staff.updated_at,
            user_email=staff.user.email,
            user_is_active=staff.user.is_active
        ))
    
    return result


@router.delete("/{staff_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_staff(
    staff_id: UUID,
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Remove staff from a business.
    Only OWNER and MANAGER can remove staff.
    Cannot remove the last owner.
    Cannot remove yourself.
    
    Args:
        staff_id: Staff relationship ID (UserBusiness ID)
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Raises:
        HTTPException: If permission denied, staff not found, or cannot remove
    """
    # Check if current user has permission (OWNER or MANAGER)
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business or user_business.role not in [UserRole.OWNER, UserRole.MANAGER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and managers can remove staff"
        )
    
    # Get the staff relationship to remove
    staff_relationship = db.query(UserBusiness).filter(
        UserBusiness.id == staff_id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not staff_relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Staff member not found in this business"
        )
    
    # Prevent removing yourself
    if staff_relationship.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove yourself from the business"
        )
    
    # Prevent removing the last owner
    if staff_relationship.role == UserRole.OWNER:
        owner_count = db.query(UserBusiness).filter(
            UserBusiness.business_id == current_business.id,
            UserBusiness.role == UserRole.OWNER
        ).count()
        
        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last owner from the business"
            )
    
    # Prevent managers from removing owners
    if user_business.role == UserRole.MANAGER and staff_relationship.role == UserRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Managers cannot remove owners"
        )
    
    db.delete(staff_relationship)
    db.commit()
    
    return None

