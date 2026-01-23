from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    create_refresh_token_db,
    revoke_refresh_token,
    verify_refresh_token
)
from app.core.config import settings
from app.core.dependencies import get_current_active_user
from app.core.business_dependencies import get_current_business, get_user_business_relationship
from app.models.user import User
from app.models.business import UserBusiness, Business
from app.schemas.auth import (
    UserCreate, 
    UserResponse, 
    UserLogin, 
    Token, 
    LogoutResponse, 
    UserRoleResponse,
    RefreshTokenResponse
)

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
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT access token (JSON-based).
    Sets refresh token in HTTP-only cookie.
    
    Args:
        login_data: User login credentials (email and password)
        response: FastAPI response object for setting cookies
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
    
    # Create refresh token and store in database
    refresh_token_obj = create_refresh_token_db(str(user.id), db)
    
    # Set refresh token in HTTP-only cookie
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token_obj.token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # Convert days to seconds
        httponly=settings.REFRESH_TOKEN_COOKIE_HTTP_ONLY,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAME_SITE,
        path="/"  # Available for all API calls
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
    response: Response = None,
    db: Session = Depends(get_db)
):
    """
    Login user and return JWT access token (OAuth2 form-based).
    Compatible with OAuth2 password flow for tools like Swagger UI.
    Sets refresh token in HTTP-only cookie.
    
    Args:
        form_data: OAuth2 password form data (username=email, password)
        response: FastAPI response object for setting cookies
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
    
    # Create refresh token and store in database
    refresh_token_obj = create_refresh_token_db(str(user.id), db)
    
    # Set refresh token in HTTP-only cookie
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token_obj.token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=settings.REFRESH_TOKEN_COOKIE_HTTP_ONLY,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAME_SITE,
        path="/api/v1/auth"
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


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token from HTTP-only cookie.
    
    Args:
        request: FastAPI request object to access cookies
        response: FastAPI response object for setting cookies
        db: Database session
    
    Returns:
        New access token, token type, user_id, and business_id
    
    Raises:
        HTTPException: If refresh token is invalid, expired, or revoked
    """
    # Get refresh token from cookie
    refresh_token_value = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    
    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify refresh token
    refresh_token_obj = verify_refresh_token(refresh_token_value, db)
    
    if not refresh_token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user
    user = db.query(User).filter(User.id == refresh_token_obj.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get first business for the user (if any)
    first_business = db.query(UserBusiness).filter(
        UserBusiness.user_id == user.id
    ).first()
    
    business_id = first_business.business_id if first_business else None
    
    # Create new access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": str(user.id)},
        expires_delta=access_token_expires
    )
    
    # Optionally rotate refresh token (create new, revoke old)
    # For security, we'll rotate the token
    revoke_refresh_token(refresh_token_value, db)
    new_refresh_token_obj = create_refresh_token_db(str(user.id), db)
    
    # Set new refresh token in HTTP-only cookie
    response.set_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        value=new_refresh_token_obj.token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=settings.REFRESH_TOKEN_COOKIE_HTTP_ONLY,
        secure=settings.REFRESH_TOKEN_COOKIE_SECURE,
        samesite=settings.REFRESH_TOKEN_COOKIE_SAME_SITE,
        path="/"  # Available for all API calls
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "business_id": business_id
    }


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Logout user and revoke refresh token.
    
    Args:
        request: FastAPI request object to access cookies
        response: FastAPI response object for clearing cookies
        current_user: Current authenticated user from dependency
        db: Database session
    
    Returns:
        Success message confirming logout
    """
    # Get refresh token from cookie and revoke it
    refresh_token_value = request.cookies.get(settings.REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token_value:
        revoke_refresh_token(refresh_token_value, db)
    
    # Clear refresh token cookie
    response.delete_cookie(
        key=settings.REFRESH_TOKEN_COOKIE_NAME,
        path="/",  # Match the path used when setting the cookie
        samesite=settings.REFRESH_TOKEN_COOKIE_SAME_SITE
    )
    
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

