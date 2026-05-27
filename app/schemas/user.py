from typing import Optional
from pydantic import BaseModel, EmailStr

class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    userType: Optional[str] = None

class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str
    accountType: str
