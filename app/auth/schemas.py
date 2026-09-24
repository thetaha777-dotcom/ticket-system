import uuid

from pydantic import BaseModel, EmailStr, field_validator, ConfigDict

class RegisterRequest(BaseModel):
    email: EmailStr 
    password: str
    
    @field_validator
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long!")
        return v

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    email: EmailStr
    role:str
    is_verified: bool
    
class VerifyEmailRequest(BaseModel):
    token: str

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    
    @field_validator("new password")
    @classmethod
    def password_strength(cis, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long!")
        return v