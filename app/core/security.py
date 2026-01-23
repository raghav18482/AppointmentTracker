from datetime import datetime, timedelta
from typing import Optional
import secrets
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.refresh_token import RefreshToken

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Note: bcrypt has a 72-byte limit for passwords. Longer passwords are truncated.
    """
    # Bcrypt has a 72-byte limit, so we truncate if necessary
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Note: bcrypt has a 72-byte limit for passwords. Longer passwords are truncated.
    """
    # Bcrypt has a 72-byte limit, so we truncate if necessary
    if len(password.encode('utf-8')) > 72:
        password = password.encode('utf-8')[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary containing the data to encode in the token (typically user ID or email)
        expires_delta: Optional timedelta for token expiration. If not provided, uses default from settings.
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token string to decode
    
    Returns:
        Decoded token payload as dictionary, or None if token is invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None


def generate_refresh_token() -> str:
    """
    Generate a secure random refresh token.
    
    Returns:
        A secure random token string (32 bytes, URL-safe base64 encoded)
    """
    return secrets.token_urlsafe(32)


def create_refresh_token_db(user_id: str, db: Session) -> RefreshToken:
    """
    Create a refresh token record in the database.
    
    Args:
        user_id: User UUID as string
        db: Database session
    
    Returns:
        Created RefreshToken object
    """
    token = generate_refresh_token()
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    refresh_token = RefreshToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at,
        is_revoked=False
    )
    
    db.add(refresh_token)
    db.commit()
    db.refresh(refresh_token)
    
    return refresh_token


def verify_refresh_token(token: str, db: Session) -> Optional[RefreshToken]:
    """
    Verify a refresh token from the database.
    
    Args:
        token: Refresh token string
        db: Database session
    
    Returns:
        RefreshToken object if valid, None otherwise
    """
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token
    ).first()
    
    if not refresh_token:
        return None
    
    if not refresh_token.is_valid():
        return None
    
    return refresh_token


def revoke_refresh_token(token: str, db: Session) -> bool:
    """
    Revoke a refresh token by marking it as revoked.
    
    Args:
        token: Refresh token string
        db: Database session
    
    Returns:
        True if token was found and revoked, False otherwise
    """
    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == token
    ).first()
    
    if not refresh_token:
        return False
    
    refresh_token.is_revoked = True
    db.commit()
    
    return True


def revoke_all_user_refresh_tokens(user_id: str, db: Session) -> int:
    """
    Revoke all refresh tokens for a user.
    
    Args:
        user_id: User UUID as string
        db: Database session
    
    Returns:
        Number of tokens revoked
    """
    refresh_tokens = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False
    ).all()
    
    count = len(refresh_tokens)
    for token in refresh_tokens:
        token.is_revoked = True
    
    db.commit()
    
    return count

