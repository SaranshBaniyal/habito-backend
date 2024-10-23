import uuid
import os
import logging
import psycopg2
import datetime
import requests
from psycopg2.extras import RealDictCursor
from psycopg2 import errors 

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import File, UploadFile, Form
from fastapi.responses import JSONResponse

import models
import utils
from connection import Database


db_instance = Database()

logger = logging.getLogger()

BLIP_API_URL = os.getenv("BLIP_API_URL")
BLIP_TOKEN = os.getenv("BLIP_TOKEN")

blip_headers = {"Authorization": f"Bearer {BLIP_TOKEN}"}


def token_endpoint(request_form: OAuth2PasswordRequestForm = Depends()):
    try:
        conn = db_instance.get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s;", (request_form.username,))
            user_data = cursor.fetchone()
        
        if user_data and utils.verify_password(request_form.password, user_data["password"]):
            access_token = utils.generate_token(user_id=user_data["user_id"])
            return {
                    "access_token": access_token,
                    "username": user_data["username"]
                    }

        raise HTTPException(status_code=401, detail="Unauthorized")

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)


def user_signup_endpoint(user: models.SignUpRequest):
    try:
        conn = db_instance.get_connection()
        hashed_password = utils.get_password_hash(user.password)
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            user_id = str(uuid.uuid4())
            cursor.execute("INSERT INTO users (user_id, username, email, password) VALUES (%s, %s, %s, %s);",
                           (user_id, user.username, user.email, hashed_password))
        conn.commit()
        
        return {
            "detail": "User signup successful"
        }

    except errors.UniqueViolation as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=400, detail="Username or email already exists")

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)


def user_login_endpoint(user: models.LoginRequest):
    try:
        conn = db_instance.get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM users WHERE email = %s;", (user.email,))
            user_data = cursor.fetchone()
        
        if user_data and utils.verify_password(user.password, user_data["password"]):
            access_token = utils.generate_token(user_id=user_data["user_id"])
            return {
                    "access_token": access_token,
                    "username": user_data["username"]
                    }

        raise HTTPException(status_code=401, detail="Incorrect email or password")

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)


def get_habits_endpoint(token: str):
    payload = utils.verify_decode_token(token=token)
    try:
        conn = db_instance.get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT habit_id, habit_name, description FROM habits;")
            habits_data = cursor.fetchall()
        
        if habits_data:
            return habits_data
        
        return []

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)


def post_user_habit_endpoint(habit: models.PostUserHabitRequest, token: str):
    payload = utils.verify_decode_token(token=token)
    try:
        conn = db_instance.get_connection()

        current_date = datetime.date.today()
        user_habit_id = str(uuid.uuid4())

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("INSERT INTO user_habits VALUES (%s, %s, %s, %s);",
                (user_habit_id, payload["sub"], habit.habit_id, current_date))
        
        conn.commit()

        return {
            "detail": "Habit added successfully"
        }

    except errors.UniqueViolation:
        # Handle the unique constraint violation for duplicate entries
        if conn:
            conn.rollback()
        logger.error(f"409: Habit already exists for current user")
        raise HTTPException(
            status_code=409,
            detail=f"You have already added this habit"
        )

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)



def get_user_habits_endpoint(token: str):
    payload = utils.verify_decode_token(token=token)
    try:
        conn = db_instance.get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                            SELECT uh.user_habit_id, uh.habit_id, uh.start_date,
                            uh.current_streak, h.habit_name, h.description
                            FROM user_habits uh
                            JOIN habits h ON uh.habit_id = h.habit_id
                            WHERE uh.user_id = %s;
                        """, (payload["sub"],))
            habits_data = cursor.fetchall()
        
            if habits_data:
                return habits_data
        
        return []

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)


async def post_user_habit_log_endpoint(user_habit_id: str, image_file: UploadFile, token: str):
    payload = utils.verify_decode_token(token=token)
    try:
        # Read the uploaded file directly without saving it to disk
        file_content = await image_file.read()
        
        # Query the Hugging Face API directly with the file content
        blip_response = requests.post(BLIP_API_URL, headers=blip_headers, data=file_content)
        caption = blip_response[0]['generated_text']

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": "Error processing the image with Hugging Face API", "error": str(e)},
        )

    # Return the result with the caption
    return {
        "user_habit_id": user_habit_id,
        "filename": image_file.filename,
        "content_type": image_file.content_type,
        "generated_caption": caption
    }

    # try:
    #     conn = db_instance.get_connection()

    #     current_date = datetime.date.today()
    #     user_habit_id = str(uuid.uuid4())

    #     with conn.cursor(cursor_factory=RealDictCursor) as cursor:
    #         cursor.execute("INSERT INTO user_habits VALUES (%s, %s, %s, %s);",
    #             (user_habit_id, payload["sub"], habit.habit_id, current_date))
        
    #     conn.commit()

    #     return {
    #         "detail": "Habit added successfully"
    #     }

    # except errors.UniqueViolation:
    #     # Handle the unique constraint violation for duplicate entries
    #     if conn:
    #         conn.rollback()
    #     logger.error(f"409: Habit already exists for current user")
    #     raise HTTPException(
    #         status_code=409,
    #         detail=f"You have already added this habit"
    #     )

    # except psycopg2.Error as e:
    #     if conn:
    #         conn.rollback()
    #     logger.error(f"500: Internal server error: {str(e)}")
    #     raise HTTPException(status_code=500, detail="Internal server error")

    # finally:
    #     if conn:
    #         db_instance.release_connection(conn)
