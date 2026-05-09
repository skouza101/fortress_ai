import logging
import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer()

def verify_nextauth_token(token: str) -> str:
    """
    Validate the NextAuth JWT token using HS256 signature verification.
    Returns the user_id (sub).
    """
    if not token:
        logger.error("No token provided in request")
        raise ValueError("No token provided")
    
    # Try multiple potential secrets in order of preference
    secrets_to_try = [
        settings.NEXTAUTH_SECRET,
        settings.SECRET_KEY,
    ]
    
    # Filter out None and duplicates
    secrets_to_try = list(dict.fromkeys([s for s in secrets_to_try if s]))
    if not secrets_to_try:
        logger.critical("Token validation misconfigured: NEXTAUTH_SECRET/SECRET_KEY missing")
        raise RuntimeError("Authentication secrets are not configured")
    
    last_exception = None
    
    for secret in secrets_to_try:
        try:
            # Attempt to decode
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
            )
            
            user_id = payload.get("sub")
            if not user_id:
                logger.error(f"Token payload missing 'sub'. Keys: {list(payload.keys())}")
                raise ValueError("Malformed token payload: missing 'sub'")
            
            return user_id
        except jwt.ExpiredSignatureError:
            logger.error("Token has expired")
            raise ValueError("Token has expired.")
        except jwt.InvalidSignatureError:
            # Continue to next secret
            last_exception = "Invalid signature"
            continue
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid token error: {str(e)}")
            last_exception = f"Invalid token: {str(e)}"
            continue
        except Exception as e:
            logger.error(f"Unexpected error during token validation: {type(e).__name__}: {e}")
            last_exception = str(e)
            continue

    logger.error(f"All secret verification attempts failed. Last error: {last_exception}")
    raise ValueError(f"Token validation failed: {last_exception or 'Unknown error'}")


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    FastAPI dependency to authenticate the user and return their user_id.
    """
    try:
        logger.debug(
            "Incoming request with token %s",
            "present" if credentials.credentials else "absent",
        )
        
        user_id = verify_nextauth_token(credentials.credentials)
        return user_id
    except ValueError as e:
        logger.error(f"Auth failed: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
