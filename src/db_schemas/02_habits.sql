CREATE TABLE habits (
  habit_id UUID PRIMARY KEY,
  habit_name VARCHAR NOT NULL,
  description VARCHAR,
  sentences TEXT[],
  embeddings FLOAT8[][]
);
