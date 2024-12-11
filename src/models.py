from typing import Optional, Dict
from pydantic import BaseModel
import datetime


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


class GetHabitsResponse(BaseModel):
    habit_id: str
    habit_name: str
    description: str


class PostUserHabitRequest(BaseModel):
    habit_id: str


class GetUserHabitsResponse(BaseModel):
    user_habit_id: str
    habit_id: str
    start_date: datetime.date
    current_streak: int
    habit_name: str
    description: str


class GetLeaderboardResponse(BaseModel):
    username: str
    current_streak: int


class GetStreakResponse(BaseModel):
    habit_name: str
    breakdown: Dict[str, bool] 
