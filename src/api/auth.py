"""
JWT Authentication system for API security.
Provides login, logout, and token verification.
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.config import (
    JWT_SECRET_KEY, 
    JWT_ALGORITHM, 
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    ADMIN_USERNAME,
    ADMIN_PASSWORD,
    USER_USERNAME,
    USER_PASSWORD,
    API_KEY as CONFIGURED_API_KEY
)

# =============================================================================
# Password Hashing
# =============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)

# =============================================================================
# JWT Token Management
# =============================================================================

security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

class Token(BaseModel):
    """JWT token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds

class TokenData(BaseModel):
    """JWT token payload model."""
    username: Optional[str] = None
    role: Optional[str] = None
    exp: Optional[datetime] = None

class LoginRequest(BaseModel):
    """Login request model."""
    username: str
    password: str

class LoginResponse(BaseModel):
    """Login response model."""
    access_token: str
    token_type: str
    expires_in: int
    username: str
    role: str

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload to encode in token
        expires_delta: Optional expiration time delta
    
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> TokenData:
    """
    Decode and verify a JWT access token.
    
    Args:
        token: JWT token string
    
    Returns:
        TokenData with username and expiration
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role", "user")
        exp: datetime = datetime.fromtimestamp(payload.get("exp", 0))
        
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(username=username, role=role, exp=exp)
        return token_data
    
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# =============================================================================
# Authentication Dependencies
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    api_key: Optional[str] = Security(api_key_header)
) -> str:
    """
    Dependency to get current authenticated user.
    Supports both JWT token and API key authentication.
    
    Args:
        credentials: Bearer token from Authorization header
        api_key: API key from X-API-Key header
    
    Returns:
        Username of authenticated user
    
    Raises:
        HTTPException: If authentication fails
    """
    # Check API key first (if configured)
    if CONFIGURED_API_KEY and api_key and api_key == CONFIGURED_API_KEY:
        return "api_key_user"
    
    # Check JWT token
    if credentials:
        token = credentials.credentials
        token_data = decode_access_token(token)
        return token_data.username
    
    # No valid authentication
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )

async def get_current_user_token_data(
    credentials: HTTPAuthorizationCredentials = Security(security),
    api_key: Optional[str] = Security(api_key_header)
) -> TokenData:
    """Return full TokenData (including role) for the authenticated user."""
    if CONFIGURED_API_KEY and api_key and api_key == CONFIGURED_API_KEY:
        return TokenData(username="api_key_user", role="admin")
    if credentials:
        return decode_access_token(credentials.credentials)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_admin_user(
    token_data: TokenData = Security(get_current_user_token_data)
) -> str:
    """
    Dependency to ensure current user is admin.
    Checks role='admin' embedded in JWT (or API key).
    """
    if token_data.role != "admin" and token_data.username != "api_key_user":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return token_data.username

# =============================================================================
# Authentication Functions
# =============================================================================

def authenticate_user(username: str, password: str) -> Optional[str]:
    """
    Authenticate a user with username and password.
    
    Args:
        username: Username to authenticate
        password: Plain text password
    
    Returns:
        Username if authentication successful, None otherwise
    
    Note:
        In production, this should check against a database with hashed passwords.
        Current implementation is simplified for demo purposes.
    """
    # Check admin credentials
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return {"username": username, "role": "admin"}
    
    # Check regular user credentials
    if username == USER_USERNAME and password == USER_PASSWORD:
        return {"username": username, "role": "user"}
    
    return None

def login(username: str, password: str) -> LoginResponse:
    """
    Login user and return JWT token.
    
    Args:
        username: Username to login
        password: Plain text password
    
    Returns:
        LoginResponse with access token
    
    Raises:
        HTTPException: If authentication fails
    """
    user_info = authenticate_user(username, password)
    
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token with role embedded
    access_token_expires = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_info["username"], "role": user_info["role"]}, 
        expires_delta=access_token_expires
    )
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        username=user_info["username"],
        role=user_info["role"]
    )
