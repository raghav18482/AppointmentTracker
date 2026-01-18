from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.core.business_dependencies import get_current_business, get_user_business_relationship
from app.models.user import User
from app.models.business import UserBusiness, Business
from app.schemas.auth import UserCreate, UserResponse, UserLogin, Token, LogoutResponse, UserRoleResponse

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user.
    
    Args:
        user_data: User registration data (email and password)
        db: Database session
    
    Returns:
        Created user object
    
    Raises:
        HTTPException: If email already exists
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        is_active=True
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def _authenticate_user(email: str, password: str, db: Session) -> User:
    """
    Authenticate a user by email and password.
    
    Args:
        email: User email
        password: Plain text password
        db: Database session
    
    Returns:
        User object if authentication successful
    
    Raises:
        HTTPException: If credentials are invalid
    """
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


@router.post("/login", response_model=Token)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT access token (JSON-based).
    
    Args:
        login_data: User login credentials (email and password)
        db: Database session
    
    Returns:
        Access token, token type, user_id, and first business_id (if available)
    
    Raises:
        HTTPException: If credentials are invalid
    """
    user = _authenticate_user(login_data.email, login_data.password, db)
    
    # Get first business for the user (if any)
    first_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == user.id
    ).first()
    
    business_id = first_business.business_id if first_business else None
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "business_id": business_id
    }


@router.post("/login/oauth2", response_model=Token)
async def login_oauth2(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT access token (OAuth2 form-based).
    Compatible with OAuth2 password flow for tools like Swagger UI.
    
    Args:
        form_data: OAuth2 password form data (username=email, password)
        db: Database session
    
    Returns:
        Access token, token type, user_id, and first business_id (if available)
    
    Raises:
        HTTPException: If credentials are invalid
    """
    user = _authenticate_user(form_data.username, form_data.password, db)
    
    # Get first business for the user (if any)
    first_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == user.id
    ).first()
    
    business_id = first_business.business_id if first_business else None
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "business_id": business_id
    }


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """
    Get current authenticated user information.
    
    Args:
        current_user: Current authenticated user from dependency
    
    Returns:
        Current user information
    """
    return current_user


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """
    Logout user.
    
    Note: Since JWT tokens are stateless, this endpoint validates the token
    and returns a success message. The client should remove the token from
    storage (localStorage, cookies, etc.) after receiving this response.
    
    Args:
        current_user: Current authenticated user from dependency
    
    Returns:
        Success message confirming logout
    """
    return {"message": "Successfully logged out"}


@router.get("/role", response_model=UserRoleResponse)
async def get_user_role(
    current_user: User = Depends(get_current_active_user),
    current_business: Business = Depends(get_current_business),
    db: Session = Depends(get_db)
):
    """
    Get the current user's role in the specified business.
    
    Requires X-Business-ID header to specify which business to check.
    
    Args:
        current_user: Current authenticated user
        current_business: Current business from X-Business-ID header
        db: Database session
    
    Returns:
        User's role in the specified business
    
    Raises:
        HTTPException: If user is not associated with the business
    """
    user_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == current_user.id,
        UserBusiness.business_id == current_business.id
    ).first()
    
    if not user_business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User is not associated with this business"
        )
    
    return UserRoleResponse(
        user_id=current_user.id,
        business_id=current_business.id,
        role=user_business.role,
        business_name=current_business.name
    )

