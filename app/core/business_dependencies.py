from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session
from typing import Optional
from uuid import UUID

from app.core.database import get_db
from app.core.dependencies import get_current_active_user
from app.core.config import settings
from app.models.user import User
from app.models.business import Business, UserBusiness, UserRole


def get_business_id_from_header(
    x_business_id: Optional[str] = Header(None, alias="X-Business-ID")
) -> Optional[UUID]:
    """
    Extract business_id from request header.
    
    Args:
        x_business_id: Business ID from X-Business-ID header (as string)
    
    Returns:
        Business ID as UUID if provided, None otherwise
    """
    if x_business_id is None:
        return None
    try:
        return UUID(x_business_id)
    except (ValueError, TypeError):
        return None


async def get_current_business(
    business_id: Optional[UUID] = Depends(get_business_id_from_header),
    db: Session = Depends(get_db)
) -> Business:
    """
    Dependency to get the current business from header.
    
    Args:
        business_id: Business ID from header
        db: Database session
    
    Returns:
        Business object
    
    Raises:
        HTTPException: If business_id is missing or business not found
    """
    if business_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Business-ID header is required"
        )
    
    business = db.query(Business).filter(Business.id == business_id).first()
    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found"
        )
    
    return business


async def get_user_business_relationship(
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
) -> UserBusiness:
    """
    Dependency to get the user-business relationship.
    Verifies that the current user has access to the current business.
    
    Args:
        current_user: Current authenticated user
        current_business: Current business from header
        db: Database session
    
    Returns:
        UserBusiness relationship object
    
    Raises:
        HTTPException: If user doesn't have access to the business
    """
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this business"
        )
    
    return user_business


def require_role(*allowed_roles: UserRole):
    """
    Factory function to create a dependency that requires specific roles.
    
    Args:
        *allowed_roles: Roles that are allowed to access the endpoint
    
    Returns:
        Dependency function that checks user role
    """
    async def role_checker(
        user_business: UserBusiness = Depends(get_user_business_relationship)
    ) -> UserBusiness:
        """
        Check if user has required role.
        
        Args:
            user_business: User-business relationship
        
        Returns:
            UserBusiness if role is allowed
        
        Raises:
            HTTPException: If user doesn't have required role
        """
        if user_business.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join([r.value for r in allowed_roles])}"
            )
        return user_business
    
    return role_checker


# Convenience dependencies for common role checks
require_owner = require_role(UserRole.OWNER)
require_manager = require_role(UserRole.OWNER, UserRole.MANAGER)
require_owner_or_manager = require_role(UserRole.OWNER, UserRole.MANAGER)
require_any_role = require_role(UserRole.OWNER, UserRole.MANAGER, UserRole.COUNTER)

