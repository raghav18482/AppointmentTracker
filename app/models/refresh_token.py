from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime

from app.models.base import BaseModel


class RefreshToken(BaseModel):
    """Refresh token model for JWT token refresh functionality."""
    
    __tablename__ = "refresh_tokens"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False, index=True)
    is_revoked = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
    
    def is_expired(self) -> bool:
        """Check if the refresh token is expired."""
        return datetime.utcnow() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if the refresh token is valid (not revoked and not expired)."""
        return not self.is_revoked and not self.is_expired()

