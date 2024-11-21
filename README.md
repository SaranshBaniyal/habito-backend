# Habito Backend
Habito Backend is a FastAPI and PostgreSQL-based backend for the Habito app, providing robust APIs to manage and interact with application data.

## Setup
Follow these steps to set up the project locally:

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/habito-backend.git
cd habito-backend
```

### 2. Create and Activate a Virtual Environment
Create a virtual environment to manage dependencies:

```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

### 3. Install Requirements
Install the dependencies from the requirements.txt file:

```bash
pip install -r requirements.txt
```

### 4. Setup the Database
Ensure you have a PostgreSQL server running and accessible. Create the required tables using the .sql files in the db_schemas directory:

```bash
psql -U <your_username> -d <your_database> -f db_schemas/<schema_file>.sql
```
Repeat for each .sql file in the db_schemas directory.

### 5. Configure Environment Variables
Create a .env file in the project root based on the .env-example file. Modify it to include your specific database credentials and settings:

```bash
cp .env-example .env
```

## Run the Application
Start the FastAPI application using the following command:

```bash
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
```
Change the number of workers as per your requirements and machine configuration.
