import logging
import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt import PyJWKClient

from app.core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)
jwks_client = PyJWKClient(settings.CLERK_JWKS_URL)

def verify_clerk_token(token: str) -> str:
    """
    Validate the Clerk JWT token using RS256 signature verification.
    Returns the user_id (sub).
    """
    if not token:
        raise ValueError("No token provided")
    
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.CLERK_ISSUER,
        )
        
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Token does not contain a user ID (sub).")
        return user_id
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error during token validation: {e}")
        raise ValueError(f"Token validation failed: {str(e)}")


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    FastAPI dependency to authenticate the user and return their user_id.
    """
    if settings.DISABLE_AUTH:
        return "anonymous_user"

    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = verify_clerk_token(credentials.credentials)
        return user_id
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=f"Authentication failed: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
