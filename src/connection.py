import os
import logging
import psycopg2
from dotenv import load_dotenv
from psycopg2 import pool


# Initialize logging
logger = logging.getLogger()
load_dotenv()


class Database:
    def __init__(self):
        self.database_name = os.getenv("PG_DB")
        self.user_name = os.getenv("PG_USER")
        self.password = os.getenv("PG_PW")
        self.host = os.getenv("PG_HOST")
        self.port = os.getenv("PG_PORT")

        try:
            # Create a connection pool
            self.pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1, 
                maxconn=10,
                dbname=self.database_name,
                user=self.user_name,
                password=self.password,
                host=self.host,
                port=self.port,
            )

            if self.pool:
                logger.info("Postgres Database connection pool created successfully")

        except psycopg2.DatabaseError as e:
            logger.error(f"Database connection error: {str(e)}")
            raise


    def get_connection(self):
        """Fetch a connection from the pool."""
        try:
            return self.pool.getconn()
        except psycopg2.DatabaseError as e:
            logger.error(f"Failed to get a connection from the pool: {str(e)}")
            raise


    def release_connection(self, conn):
        """Return the connection back to the pool."""
        try:
            self.pool.putconn(conn)
        except psycopg2.DatabaseError as e:
            logger.error(f"Failed to release the connection back to the pool: {str(e)}")
            raise


    def close_pool(self):
        """Close the connection pool."""
        if self.pool:
            self.pool.closeall()
            logger.info("Postgres connection pool closed successfully")
