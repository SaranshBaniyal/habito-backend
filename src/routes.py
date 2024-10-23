import models
import handler
from typing import List, Optional

from fastapi import APIRouter, Depends, Response, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import Request, Form
from fastapi.responses import RedirectResponse


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


@router.post("/token", response_model=models.LoginResponse)
def token(request_form: OAuth2PasswordRequestForm = Depends()):
    return handler.token_endpoint(request_form)


@router.post(
    "/user/signup",
    response_model=models.Response,
    responses={
        400: {"description": "Username or email already exists"},
        500: {"description": "Internal server error"},
    },
)
def user_signup(user: models.SignUpRequest):
    return handler.user_signup_endpoint(user)


@router.post(
    "/user/login",
    response_model=models.LoginResponse,
    responses={
        401: {"description": "Incorrect email or password"},
        500: {"description": "Internal server error"},
    },
)
def user_login(user: models.LoginRequest):
    return handler.user_login_endpoint(user)


@router.get(
    "/habits",
    response_model=List[Optional[models.GetHabitsResponse]],
    responses={
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
def get_habits(token: str = Depends(oauth2_scheme)):
    return handler.get_habits_endpoint(token)


@router.post(
    "/user/habit",
    response_model=models.Response,
    responses={
        401: {"description": "Unauthorized"},
        409: {"description": "You have already added this habit"},
        500: {"description": "Internal server error"},
    },
)
def post_user_habit(habit: models.PostUserHabitRequest, token: str = Depends(oauth2_scheme)):
    return handler.post_user_habit_endpoint(habit, token)


@router.get(
    "/user/habits",
    response_model=List[Optional[models.GetUserHabitsResponse]],
    responses={
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
def get_user_habits(token: str = Depends(oauth2_scheme)):
    return handler.get_user_habits_endpoint(token)
