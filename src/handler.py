import uuid
import os
import logging
import psycopg2
import datetime
import httpx
from psycopg2.extras import RealDictCursor
from psycopg2 import errors 
from sentence_transformers import SentenceTransformer, util

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

model = SentenceTransformer('all-MiniLM-L6-v2')

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
    current_date = datetime.date.today()

    try:
        # Read the uploaded file directly without saving it to disk
        file_content = await image_file.read()

        # Use httpx for making asynchronous requests
        async with httpx.AsyncClient() as client:
            blip_response = await client.post(BLIP_API_URL, headers=blip_headers, data=file_content)
            blip_response.raise_for_status()  # Check for errors
            caption = blip_response.json()[0]['generated_text']

    except httpx.HTTPStatusError as e:
        return JSONResponse(
            status_code=500,
            content={"message": "Error processing the image with Hugging Face API", "error": str(e)},
        )

    try:
        conn = db_instance.get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""SELECT embeddings 
                                FROM habits 
                                WHERE habit_id = (
                                    SELECT habit_id 
                                    FROM user_habits 
                                    WHERE user_habit_id = %s
                                );""", (user_habit_id,))
            embeddings = cursor.fetchone()["embeddings"]

        caption_embedding = model.encode(caption)

        # Compute cosine similarity
        similarities = util.cos_sim(caption_embedding, embeddings)

        # Find the most similar description
        best_match_index = similarities.argmax()
        best_similarity = similarities[0][best_match_index]

        if best_similarity > 0.5:
            # Log habit and implement streak logic
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                try:
                    # Insert the habit log
                    cursor.execute("""
                        INSERT INTO habit_logs (user_habit_id, performed_at) 
                        VALUES (%s, %s)
                        """, (user_habit_id, current_date))

                except errors.UniqueViolation:
                    logger.error(f"409: You have already logged this habit for today")
                    raise HTTPException(
                        status_code=409,
                        detail=f"You have already logged this habit for today"
                    )

                # Update the current streak
                cursor.execute("""
                    SELECT current_streak, last_streak_date FROM user_habits 
                    WHERE user_habit_id = %s
                    """, (user_habit_id,))
                streak_data = cursor.fetchone()
                current_streak = streak_data["current_streak"]
                last_streak_date = streak_data["last_streak_date"]
                # current_streak, last_streak_date = cursor.fetchone()

                # Ensure last_streak_date is a datetime.date object
                if last_streak_date is not None and isinstance(last_streak_date, str):
                    last_streak_date = datetime.datetime.strptime(last_streak_date, "%Y-%m-%d").date()

                if last_streak_date is None:
                    # This is the first log
                    new_streak = 1
                    last_streak_date = current_date

                else:
                    if current_date == last_streak_date + datetime.timedelta(days=1):
                        # Increment streak
                        new_streak = current_streak + 1
                    elif current_date > last_streak_date + datetime.timedelta(days=1):
                        # Reset streak
                        new_streak = 1
                    else:
                        # If the log is for a date in the past, we do nothing or return a message
                        raise HTTPException(status_code=400, detail="Cannot log a habit for a past date.")

                # Update the user's habit record
                cursor.execute("""
                    UPDATE user_habits 
                    SET current_streak = %s, last_streak_date = %s 
                    WHERE user_habit_id = %s
                    """, (new_streak, current_date, user_habit_id))
            conn.commit()
            return {
                "detail": "Habit streak updated successfully"
            }

        else:
            logger.error("400: Habit was not verified due to incorrect image")
            raise HTTPException(status_code=400, detail="Habit was not verified due to incorrect image")

    except psycopg2.Error as e:
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)