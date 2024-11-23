# Habito Backend
Habito Backend is a FastAPI and PostgreSQL-based backend for the Habito app, providing robust APIs to manage and interact with application data.


## Setup and Run the Application

There are two ways to run the application:

1. **Run the application locally (without Docker)**.
2. **Run the application using Docker** (recommended for an isolated, easy setup).

### Option 1: Run the Application Locally (Without Docker)

Follow these steps to set up and run the application locally.

#### 1. Clone the Repository
```bash
git clone https://github.com/SaranshBaniyal/habito-backend.git
cd habito-backend
```

#### 2. Create and Activate a Virtual Environment
Create a virtual environment to manage dependencies:

```bash
# On macOS/Linux
python3 -m venv venv
source venv/bin/activate

# On Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. Install Requirements
Install the dependencies from the requirements.txt file:

```bash
pip install -r requirements.txt
```

#### 4. Setup the Database
Ensure you have a PostgreSQL server running and accessible. Create the required tables using the .sql files in the db_schemas directory:

```bash
psql -U <your_username> -d <your_database> -f db_schemas/<schema_file>.sql
```
Repeat for each .sql file in the db_schemas directory.

#### 5. Configure Environment Variables
Create a .env file in the project root based on the .env-example file. Modify it to include your specific database credentials and settings:

```bash
cp .env-example .env
```

#### 6. Run the Application
Start the FastAPI application using the following command:

```bash
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
```
Change the number of workers as per your requirements and machine configuration.


### Option 2: Run the Application with Docker (Recommended)
Using Docker Compose is the easiest way to set up and run both the backend and the database in an isolated environment. This option automatically sets up all dependencies, including the PostgreSQL database, and is the recommended method.

#### 1. Build and Start the Containers (First Time Setup)
Run the following command to build the Docker images and start the services defined in the docker-compose.yml:

```bash
docker-compose up --build
```
This will:

Build the Docker images for the backend and PostgreSQL.
Start the FastAPI application on port 8008 on your host machine.
Start the PostgreSQL database on port 5433 on your host machine.

#### 2. Start the Containers (Subsequent Runs)
After the initial setup and image build, you can simply use the following command to start the containers without rebuilding the images:

```bash
docker-compose up
```
This will:

Start the containers using the pre-built Docker images.

#### 3. Stopping the Containers
To stop the running containers and clean up, run:

```bash
docker-compose down
```
If you want to also remove the volumes (e.g., database data), use:

```bash
docker-compose down --volumes
```
