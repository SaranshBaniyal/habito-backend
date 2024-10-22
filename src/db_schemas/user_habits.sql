CREATE TABLE user_habits (
  user_habit_id UUID PRIMARY KEY,
  user_id UUID REFERENCES users(user_id),
  habit_id UUID REFERENCES habits(habit_id),
  start_date DATE,
  UNIQUE(user_id, habit_id)
);
