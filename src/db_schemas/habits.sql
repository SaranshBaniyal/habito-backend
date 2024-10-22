CREATE TABLE standard_habits (
  habit_id UUID PRIMARY KEY,
  habit_name VARCHAR NOT NULL,
  description VARCHAR,
  tags VARCHAR,
  created_by UUID REFERENCES users(user_id) DEFAULT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
