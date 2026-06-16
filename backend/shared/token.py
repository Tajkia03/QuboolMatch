from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from config import get_settings
from database import get_db

from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from config import get_settings
from database import get_db

security = HTTPBearer()

class Token:
    @staticmethod
    def generate_and_sign(user_id: str) -> str:
        expire = datetime.now(timezone.utc) + timedelta(days=7)
        payload = {"user_id": user_id, "exp": expire}
        return jwt.encode(payload, get_settings().SECRET_KEY, algorithm="HS256")

    @staticmethod
    def verify_token(token: str):
        try:
            payload = jwt.decode(token, get_settings().SECRET_KEY, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

def get_current_user(db: Session = Depends(get_db), token: str = Depends(security)):
    """
    Get the current authenticated user from the JWT token
    """
    # Import here to avoid circular imports
    from models.user.user import User
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Extract token from Bearer token
        token_str = token.credentials
        payload = Token.verify_token(token_str)
        
        if payload is None:
            raise credentials_exception
            
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
            
    except AttributeError as e:
        print(f"Token attribute error: {e}")
        raise credentials_exception
    except Exception as e:
        print(f"Authentication error: {e}")
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
        
    return user

# Alternative simpler authentication function for profile endpoints
def get_current_user_from_header(authorization: str = Depends(lambda: None), db: Session = Depends(get_db)):
    """
    Get the current authenticated user from Authorization header
    This is a simpler alternative that directly reads the header
    """
    from fastapi import Header, Request
    from models.user.user import User
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not authorization:
        raise credentials_exception
    
    try:
        # Extract token from "Bearer <token>"
        if not authorization.startswith("Bearer "):
            raise credentials_exception
        
        token_str = authorization.split(" ")[1]
        payload = Token.verify_token(token_str)
        
        if payload is None:
            raise credentials_exception
            
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise credentials_exception
            
    except Exception as e:
        print(f"Authentication error: {e}")
        raise credentials_exception
    
    # Get user from database
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
        
    return user

def get_current_admin_user(current_user = Depends(get_current_user)):
    """
    Get the current authenticated admin user
    Raises HTTPException if user is not an admin
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user
