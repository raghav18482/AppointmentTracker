# Appointment Tracker

A production-ready multi-tenant SaaS application built with FastAPI, PostgreSQL, and SQLAlchemy.

## Features

- 🚀 FastAPI with async support
- 🗄️ PostgreSQL database with SQLAlchemy ORM
- 🔄 Alembic for database migrations
- 🔐 Multi-tenant architecture support
- ⚙️ Environment-based configuration (dev/staging/prod)
- 📦 Modular folder structure
- 🔒 Security best practices

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 12 or higher
- pip (Python package manager)

## Installation

1. **Clone the repository** (if applicable) or navigate to the project directory:
   ```bash
   cd "Appointment Tracker"
   ```

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**:
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```

4. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Environment Setup

1. **Create a `.env` file** in the root directory:
   ```bash
   cp .env.example .env
   ```

2. **Configure your environment variables** in `.env`:
   ```env
   # Application
   APP_NAME=Appointment Tracker
   APP_VERSION=1.0.0
   DEBUG=true
   ENVIRONMENT=dev

   # Database
   DATABASE_URL=postgresql://user:password@localhost:5432/appointment_tracker

   # Security
   SECRET_KEY=your-secret-key-here-change-in-production
   ACCESS_TOKEN_EXPIRE_MINUTES=30

   # CORS (comma-separated)
   CORS_ORIGINS=http://localhost:3000,http://localhost:8000
   ```

   **Important**: 
   - Replace `user`, `password`, and `appointment_tracker` with your PostgreSQL credentials and database name
   - Generate a strong `SECRET_KEY` for production (you can use: `openssl rand -hex 32`)

## Database Setup

1. **Create a PostgreSQL database**:
   ```bash
   createdb appointment_tracker
   ```
   Or using psql:
   ```sql
   CREATE DATABASE appointment_tracker;
   ```

2. **Run database migrations**:
   ```bash
   # Create initial migration (if needed)
   alembic revision --autogenerate -m "Initial migration"

   # Apply migrations
   alembic upgrade head
   ```

## Running the Application

### Development Mode

Run the application with auto-reload enabled:

```bash
uvicorn main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive API Docs (Swagger)**: http://localhost:8000/docs
- **Alternative API Docs (ReDoc)**: http://localhost:8000/redoc

### Production Mode

For production, use a production ASGI server like Gunicorn with Uvicorn workers:

```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## API Endpoints

### Health Check
- `GET /` - Root endpoint
- `GET /health` - Health check endpoint

### API v1
All API endpoints are prefixed with `/api/v1`:

- `/api/v1/auth/*` - Authentication endpoints
- `/api/v1/users/*` - User management endpoints
- `/api/v1/business/*` - Business management endpoints
- `/api/v1/queue/*` - Queue management endpoints

## Project Structure

```
Appointment Tracker/
├── app/
│   ├── api/
│   │   └── v1/              # API version 1
│   │       ├── auth/        # Authentication module
│   │       ├── users/       # Users module
│   │       ├── business/    # Business module
│   │       └── queue/       # Queue module
│   ├── core/
│   │   ├── config.py        # Application settings
│   │   └── database.py      # Database configuration
│   ├── models/              # SQLAlchemy models
│   │   └── base.py          # Base model with common fields
│   └── schemas/             # Pydantic schemas
├── alembic/                 # Database migrations
│   ├── versions/            # Migration files
│   └── env.py               # Alembic environment
├── main.py                  # FastAPI application entry point
├── alembic.ini              # Alembic configuration
├── requirements.txt         # Python dependencies
└── .env                     # Environment variables (create from .env.example)
```

## Database Migrations

### Create a new migration:
```bash
alembic revision --autogenerate -m "Description of changes"
```

### Apply migrations:
```bash
alembic upgrade head
```

### Rollback last migration:
```bash
alembic downgrade -1
```

### View migration history:
```bash
alembic history
```

## Development

### Adding a New Module

1. Create a new folder in `app/api/v1/` (e.g., `appointments/`)
2. Create `routes.py` with your router:
   ```python
   from fastapi import APIRouter
   
   router = APIRouter()
   
   @router.get("/")
   async def get_appointments():
       return {"message": "Appointments module"}
   ```
3. Create `__init__.py`:
   ```python
   from app.api.v1.appointments.routes import router
   __all__ = ["router"]
   ```
4. Register the router in `app/api/v1/__init__.py`

### Creating Models

1. Create your model in `app/models/`:
   ```python
   from app.models.base import BaseModel
   from sqlalchemy import Column, String
   
   class YourModel(BaseModel):
       name = Column(String, nullable=False)
   ```
2. Import it in `app/models/__init__.py` if needed
3. Create a migration: `alembic revision --autogenerate -m "Add YourModel"`

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `APP_NAME` | Application name | "Appointment Tracker" |
| `ENVIRONMENT` | Environment (dev/staging/prod) | "dev" |
| `DEBUG` | Debug mode | false |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | Secret key for JWT tokens | Required |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiration | 30 |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | "http://localhost:3000,http://localhost:8000" |
| `TENANT_HEADER` | Header name for tenant ID | "X-Tenant-ID" |

## Troubleshooting

### Database Connection Issues
- Ensure PostgreSQL is running
- Verify `DATABASE_URL` in `.env` is correct
- Check database credentials and permissions

### Migration Issues
- Make sure all models are imported in `alembic/env.py`
- Check that the database exists
- Verify Alembic version table exists: `alembic upgrade head`

### Import Errors
- Ensure virtual environment is activated
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check Python path and module structure

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

