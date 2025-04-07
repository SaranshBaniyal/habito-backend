CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY,
    username VARCHAR UNIQUE NOT NULL,
    email VARCHAR UNIQUE NOT NULL,
    password VARCHAR NOT NULL,
    location GEOMETRY(Point, 4326)
);

CREATE INDEX IF NOT EXISTS users_location_idx ON users USING GIST (location);
