import models
import handler
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi import File, UploadFile, Form


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


@router.post(
    "/user/habit/log",
    # response_model=models.Response,
    responses={
        401: {"description": "Unauthorized"},
        409: {"description": "You have already logged this habit for today"},
        400: {"description": "Habit was not verified due to incorrect image"},
        500: {"description": "Internal server error"},
    },
)
async def post_user_habit_log(user_habit_id: str = Form(...), image_file: UploadFile = File(...), token: str = Depends(oauth2_scheme)):
    return await handler.post_user_habit_log_endpoint(user_habit_id, image_file, token)


@router.get(
    "/leaderboard",
    response_model=List[Optional[models.GetLeaderboardResponse]],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Habit's leaderboard does not exist"},
        500: {"description": "Internal server error"},
    },
)
def get_leaderboard(habit_id: str, token: str = Depends(oauth2_scheme)):
    return handler.get_leaderboard_endpoint(habit_id, token)


@router.get(
    "/user/streaks",
    response_model=List[Optional[models.GetStreakResponse]],
    responses={
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    },
)
def get_user_streaks(token: str = Depends(oauth2_scheme)):
    return handler.get_user_streaks_endpoint(token)

@router.patch("/user/location",
    response_model=models.Response,
    responses={
        401: {"description": "Unauthorized"},
        500: {"description": "Internal server error"},
    }
)
def update_user_location(loc: models.UpdateLocationRequest, token: str = Depends(oauth2_scheme)):
    return handler.update_user_location_endpoint(loc, token)


# TODO: Modify this to be habit specific
# TODO: Consider making this radius bound, if required
@router.get("/leaderboard/nearby",
    response_model=List[Optional[models.GetLeaderboardNearbyResponse]],
    responses={
        401: {"description": "Unauthorized"},
        404: {"description": "Habit's leaderboard does not exist"},
        500: {"description": "Internal server error"},
    },
)
def get_leaderboard_nearby(habit_id: str, token: str = Depends(oauth2_scheme)):
    return handler.get_leaderboard_nearby_endpoint(habit_id, token)
