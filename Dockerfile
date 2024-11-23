FROM python:3.12-slim

# Install system dependencies required for psycopg2
RUN apt-get update && apt-get install -y libpq-dev gcc

WORKDIR /app

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./src ./src

WORKDIR /app/src

# Set environment variables from .env
ENV $(cat .env | xargs)

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
