CREATE TABLE habit_logs (
  log_id BIGSERIAL PRIMARY KEY,
  user_habit_id UUID REFERENCES user_habits(user_habit_id),
  performed_at DATE NOT NULL,
  UNIQUE(user_habit_id, performed_at)
);
