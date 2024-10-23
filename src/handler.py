import uuid
import os
import logging
import psycopg2
from datetime import datetime
# from passlib.context import CryptContext
from psycopg2.extras import RealDictCursor
from psycopg2 import errors 

from fastapi import Depends, HTTPException, Response, Request
from fastapi.security import OAuth2PasswordRequestForm

import models
import utils
from connection import Database


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
