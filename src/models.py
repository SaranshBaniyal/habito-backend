from typing import Optional
from pydantic import BaseModel
from datetime import datetime


class Response(BaseModel):
    detail: str


class SignUpRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    username: str