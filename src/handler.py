import uuid
import logging
import psycopg2
import datetime
from psycopg2.extras import RealDictCursor
from psycopg2 import errors 
from sentence_transformers import util

from fastapi import Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import UploadFile

import models
import utils
from connection import Database

from PIL import Image
from io import BytesIO

db_instance = Database()

logger = logging.getLogger()


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


async def post_user_habit_log_endpoint(request: Request, user_habit_id: str, image_file: UploadFile, token: str):
    payload = utils.verify_decode_token(token=token)
    current_date = datetime.date.today()

    sentence_model = request.app.state.sentence_model
    blip_model = request.app.state.blip_model
    processor = request.app.state.blip_processor
    device = request.app.state.device

    try:
        file_content = await image_file.read()
        image = Image.open(BytesIO(file_content)).convert("RGB")

        inputs = processor(images=image, return_tensors="pt").to(device)
        output = blip_model.generate(**inputs)
        caption = processor.decode(output[0], skip_special_tokens=True)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"BLIP captioning error: {str(e)}")

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

        caption_embedding = sentence_model.encode(caption)

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


def get_leaderboard_endpoint(habit_id:str, token: str):
    payload = utils.verify_decode_token(token=token)
    try:
        conn = db_instance.get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                            SELECT u.username, uh.current_streak
                            FROM user_habits uh
                            JOIN users u ON uh.user_id = u.user_id
                            WHERE uh.habit_id = %s
                            ORDER BY current_streak DESC
                            LIMIT 10;
                        """, (habit_id,))
            leaderboard_data = cursor.fetchall()
        
            if leaderboard_data:
                return leaderboard_data
        
        raise HTTPException(status_code=404, detail="Habit's leaderboard does not exist")

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)


def get_user_streaks_endpoint(token):
    payload = utils.verify_decode_token(token=token)
    user_id = payload["sub"]
    try:
        today = datetime.date.today()
        start_of_week = today - datetime.timedelta(days=today.weekday())  # Monday
        week_days = [(start_of_week + datetime.timedelta(days=i)) for i in range(7)]  # Monday to Sunday
        week_day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        conn = db_instance.get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                            SELECT uh.user_habit_id, h.habit_name
                            FROM user_habits uh
                            JOIN habits h ON uh.habit_id = h.habit_id
                            WHERE uh.user_id = %s;
                           """, (user_id,))
            user_habits = cursor.fetchall()
            user_habit_map = {habit["user_habit_id"]: habit["habit_name"] for habit in user_habits}
            user_habit_ids = list(user_habit_map.keys())

            if not user_habit_ids:
                return []
            
            cursor.execute("""
                            SELECT user_habit_id, performed_at
                            FROM habit_logs
                            WHERE user_habit_id = ANY(%s::uuid[])
                            AND performed_at BETWEEN %s AND %s;
                           """, (user_habit_ids, start_of_week, week_days[-1]))
            logs = cursor.fetchall()

        
        # Organize logs by user_habit_id
        logs_by_habit = {}
        for log in logs:
            habit_id = log["user_habit_id"]
            performed_at = log["performed_at"]
            if habit_id not in logs_by_habit:
                logs_by_habit[habit_id] = set()
            logs_by_habit[habit_id].add(performed_at)

        # Prepare the day-wise breakdown with day names
        result = []
        for habit_id, habit_name in user_habit_map.items():
            breakdown = {
                week_day_names[i]: (week_days[i] in logs_by_habit.get(habit_id, set()))
                for i in range(len(week_days))
            }
            result.append({"habit_name": habit_name, "breakdown": breakdown})

        return result
        
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)

def update_user_location_endpoint(loc: models.UpdateLocationRequest, token: str):
    payload = utils.verify_decode_token(token=token)
    user_id = payload["sub"]

    point = f"SRID=4326;POINT({loc.longitude} {loc.latitude})"

    try:
        conn = db_instance.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "UPDATE users SET location = ST_GeomFromText(%s, 4326) WHERE user_id = %s",
                (point, user_id),
            )
            conn.commit()
        return {"detail": "User location updated"}

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)


def get_leaderboard_nearby_endpoint(habit_id: str, token: str):
    payload = utils.verify_decode_token(token=token)
    user_id = payload["sub"]
    try:
        conn = db_instance.get_connection()

        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("""
                SELECT ST_X(location) AS lng, ST_Y(location) AS lat
                FROM users
                WHERE user_id = %s
            """, (user_id,))
            user_loc = cursor.fetchone()

            if not user_loc or None in user_loc:
                raise HTTPException(status_code=400, detail="User location is not set.")
            
            lng = user_loc["lng"] # X = lng,
            lat = user_loc["lat"] # Y = lat

            # Query nearby users (excluding the current user)
            cursor.execute("""
                SELECT u.username, uh.current_streak,
                ST_Distance(u.location::geography,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) AS distance
                FROM users u
                JOIN user_habits uh
                ON u.user_id=uh.user_id
                WHERE uh.habit_id = %s
                AND uh.user_id != %s 
                AND location IS NOT NULL
                ORDER BY distance
                LIMIT 5
            """, (lng, lat, habit_id, user_id))

            results = cursor.fetchall()
            return results
        
        raise HTTPException(status_code=404, detail="Habit's leaderboard does not exist")

    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        logger.error(f"500: Internal server error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

    finally:
        if conn:
            db_instance.release_connection(conn)