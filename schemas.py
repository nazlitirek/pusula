from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, time

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    class_year: Optional[str] = None
    is_graduate: bool = False

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str
    class_year: Optional[str] = None
    is_graduate: bool

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None  