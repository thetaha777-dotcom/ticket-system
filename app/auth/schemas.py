from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from app.users.schemas import UserOut

# bcrypt reads at most 72 bytes of a password, so longer ones are refused instead of silently cut.
Password = Field(min_length=8, max_length=72)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Password
    role: Literal["attendee", "organizer"] = "attendee"
    locale: str = Field("ru", pattern="^(kk|ru|en)$")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Password


class Message(BaseModel):
    detail: str
