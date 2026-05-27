from fastapi import APIRouter, Depends, HTTPException, Header
import logging
import secrets
from datetime import datetime, timedelta, timezone
import bcrypt
from pydantic import BaseModel, EmailStr
from app.core.auth import get_current_user
from app.db.store import store
from app.schemas.user import ProfileUpdate, UserSignup
from app.core.config import settings

router = APIRouter(prefix="/api/users", tags=["Users"])
logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise HTTPException(status_code=422, detail="Password must be 72 bytes or fewer")

    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        return False

    return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))

# ── Schemas ────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    password: str

class VerifyEmailRequest(BaseModel):
    token: str


# ── Endpoints ──────────────────────────────────────────────────

@router.get("/profile-by-email/{email}")
async def get_profile_by_email(
    email: str,
    x_internal_secret: str = Header(None)
):
    """Internal route to fetch user profile by email."""
    if not x_internal_secret or x_internal_secret != settings.SECRET_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized internal call")
        
    user = await store.get_user_by_email(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "userType": user.userType
    }


@router.post("/signup")
async def signup(user: UserSignup):
    """Create a new user account."""
    existing = await store.get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="An account with this email already exists")
    
    if len(user.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    password_hash = hash_password(user.password)
    success = await store.create_user(
        email=user.email,
        name=user.name,
        user_type=user.accountType,
        password_hash=password_hash,
    )
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to create account")
    
    return {"status": "success"}


@router.post("/login")
async def login(credentials: dict):
    """Verify user credentials and return user info."""
    email = credentials.get("email")
    password = credentials.get("password")
    
    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password required")
    
    user = await store.get_user_by_email(email)
    if not user or not user.passwordHash:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    if not verify_password(password, user.passwordHash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "userType": user.userType,
    }


@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    """
    Initiate a password reset. Creates a time-limited token in the DB.
    Always returns 200 to avoid leaking whether an email exists (security best practice).
    """
    try:
        user = await store.get_user_by_email(req.email)
        if user:
            # Generate a cryptographically-secure reset token
            token = secrets.token_urlsafe(48)
            expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

            await store.prisma.passwordresettoken.create(
                data={
                    "token": token,
                    "email": req.email,
                    "expiresAt": expires_at,
                }
            )

            # TODO: Send email via your mail service (SendGrid, SES, etc.)
            # For now we log the reset URL so it can be tested locally.
            reset_url = f"http://localhost:3000/auth/reset-password?token={token}"
            logger.info(f"[PASSWORD RESET] URL for {req.email}: {reset_url}")

    except Exception:
        logger.exception("Error during forgot-password flow")
        # Still return 200 — do not expose internal errors

    return {"status": "ok", "message": "If an account exists, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    """
    Reset the user's password using a valid, unexpired token.
    """
    if len(req.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    try:
        record = await store.prisma.passwordresettoken.find_unique(
            where={"token": req.token}
        )

        if not record:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        now = datetime.now(timezone.utc)
        if record.expiresAt.replace(tzinfo=timezone.utc) < now:
            # Clean up expired token
            await store.prisma.passwordresettoken.delete(where={"token": req.token})
            raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")

        # Find user and update password
        user = await store.get_user_by_email(record.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        new_hash = hash_password(req.password)
        await store.prisma.user.update(
            where={"id": user.id},
            data={"passwordHash": new_hash},
        )

        # Invalidate the token after use
        await store.prisma.passwordresettoken.delete(where={"token": req.token})

        return {"status": "success", "message": "Password has been reset successfully"}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error during password reset")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/verify-email")
async def verify_email(req: VerifyEmailRequest):
    """
    Verify a user's email address using a token from the verification link.
    """
    try:
        record = await store.prisma.emailverificationtoken.find_unique(
            where={"token": req.token}
        )

        if not record:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")

        now = datetime.now(timezone.utc)
        if record.expiresAt.replace(tzinfo=timezone.utc) < now:
            await store.prisma.emailverificationtoken.delete(where={"token": req.token})
            raise HTTPException(status_code=400, detail="Verification token has expired. Please register again.")

        # Mark user as verified (the existence of a passwordHash means they registered)
        user = await store.get_user_by_email(record.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Clean up the used token
        await store.prisma.emailverificationtoken.delete(where={"token": req.token})

        return {"status": "success", "message": "Email verified successfully"}

    except HTTPException:
        raise
    except Exception:
        logger.exception("Unexpected error during email verification")
        raise HTTPException(status_code=500, detail="Internal server error")
