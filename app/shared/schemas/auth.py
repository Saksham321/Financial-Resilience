"""
Pydantic v2 Schemas for Authentication & User Registration
"""

import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user_id: uuid.UUID
    email: EmailStr
    role: str

class PasswordInput(BaseModel):
    @field_validator("password", check_fields=False)
    @classmethod
    def bcrypt_byte_limit(cls, value):
        if len(value.encode("utf-8")) > 72:
            raise ValueError("Password must not exceed 72 UTF-8 bytes")
        return value


class LoginRequest(PasswordInput):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)

class RegisterRequest(PasswordInput):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    province: str = Field(default="Ontario", max_length=50)

class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    role: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    province: Optional[str] = None

    class Config:
        from_attributes = True
