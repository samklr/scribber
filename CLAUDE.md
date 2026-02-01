# CLAUDE.md - Project Template Guide

## Overview

This is a production-ready template for building and deploying **FastAPI + React** applications with **self-hosted authentication**. Use this as a starting point for new projects that need:

- Dockerized development and production environments
- Single-VM deployment with automatic SSL
- Built-in authentication (no external services required)
- Health monitoring and management scripts
- Database backup/restore capabilities

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend | FastAPI (Python 3.12) | REST API |
| Frontend | React 18 + Vite + Caddy | Single-page application |
| Auth | JWT + bcrypt (self-hosted) | Authentication |
| Database | PostgreSQL 16 | Data persistence |
| Proxy | Caddy | Reverse proxy, auto SSL |
| Container | Docker Compose | Orchestration |
| IaC | Terraform | Cloud infrastructure (placeholder) |

---

## Building From This Template

### Step 1: Copy and Rename

```bash
cp -r project-template my-new-project
cd my-new-project

# Update project references
sed -i '' 's/project-template/my-new-project/g' README.md
sed -i '' 's/Project Template/My New Project/g' backend/app/config.py
```

### Step 2: Customize the Backend

#### Add New API Endpoints

1. **Create a new router** in `backend/app/routers/`:

```python
# backend/app/routers/users.py
from fastapi import APIRouter, Depends
from app.routers.auth import get_current_user, User

router = APIRouter()

@router.get("/users/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    return {"user": current_user.email}
```

2. **Register the router** in `backend/app/main.py`:

```python
from app.routers import auth, health, items, users

app.include_router(users.router, prefix="/api/v1", tags=["Users"])
```

#### Add Database Models (SQLAlchemy)

1. **Install dependencies** - add to `backend/requirements.txt`:

```
sqlalchemy[asyncio]==2.0.32
asyncpg==0.29.0
alembic==1.13.2
```

2. **Create database module** at `backend/app/database.py`:

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

3. **Create models** at `backend/app/models.py`:

```python
from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    hashed_password = Column(String)
    created_at = Column(DateTime, server_default=func.now())
```

### Step 3: Understanding the Authentication System

The template includes a complete self-hosted auth system in `backend/app/routers/auth.py`:

#### Backend Auth Features

- **Password hashing** with bcrypt
- **JWT tokens** for session management
- **Protected routes** via dependency injection

```python
from fastapi import Depends
from app.routers.auth import get_current_user, User

@router.get("/protected")
async def protected_route(user: User = Depends(get_current_user)):
    return {"message": f"Hello {user.email}"}
```

#### Frontend Auth Features

- **AuthContext** for global state management
- **Protected routes** that redirect to sign-in
- **Token storage** in localStorage

```jsx
import { useAuth } from './context/AuthContext'

function MyComponent() {
  const { user, signIn, signOut, getAuthHeader } = useAuth()

  const fetchProtectedData = async () => {
    const response = await fetch('/api/v1/protected', {
      headers: getAuthHeader(),
    })
    return response.json()
  }
}
```

#### Auth Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Create account |
| `/api/v1/auth/login` | POST | Get JWT token |
| `/api/v1/auth/me` | GET | Get current user |
| `/api/v1/auth/logout` | POST | Invalidate session |

### Step 4: Customize the Frontend

#### Add More Routes

Edit `frontend/src/App.jsx`:

```jsx
import NewPage from './pages/NewPage'

// In Routes:
<Route path="new-page" element={<NewPage />} />
```

#### Add State Management (if needed)

For more complex state, consider adding:

```bash
npm install zustand
# or
npm install @tanstack/react-query
```

#### Add UI Library (Optional)

```bash
# Tailwind CSS
npm install -D tailwindcss postcss autoprefixer
npx tailwindcss init -p

# Or shadcn/ui
npx shadcn-ui@latest init

# Or Material UI
npm install @mui/material @emotion/react @emotion/styled
```

### Step 5: Configure Environment

#### Development (`.env`)

```bash
cp .env.example .env
# Edit with your local settings
```

#### Production (`infra/single-vm/.env`)

```bash
cd infra/single-vm
cp .env.example .env

# Generate secure keys
echo "SECRET_KEY=$(openssl rand -base64 64)" >> .env
echo "POSTGRES_PASSWORD=$(openssl rand -base64 32)" >> .env

# Set your domain
echo "DOMAIN_NAME=myapp.example.com" >> .env
echo "CADDY_EMAIL=admin@example.com" >> .env
```

### Step 6: Add Database Migrations

1. **Initialize Alembic**:

```bash
cd backend
alembic init alembic
```

2. **Configure `alembic/env.py`**:

```python
from app.database import Base
from app.models import *  # Import all models
target_metadata = Base.metadata
```

3. **Create migration**:

```bash
alembic revision --autogenerate -m "Initial tables"
alembic upgrade head
```

---

## Project Structure Reference

```
my-project/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI app entry
│   │   ├── config.py            # Settings from env
│   │   ├── database.py          # DB connection (add this)
│   │   ├── models.py            # SQLAlchemy models (add this)
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── auth.py          # Authentication (included)
│   │       ├── health.py        # Health checks
│   │       └── items.py         # Example CRUD
│   ├── alembic/                 # Migrations (add this)
│   ├── tests/                   # Tests (add this)
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── index.css
│   │   ├── context/
│   │   │   └── AuthContext.jsx  # Auth state (included)
│   │   ├── components/
│   │   │   └── Layout.jsx       # App layout (included)
│   │   └── pages/
│   │       ├── HomePage.jsx
│   │       ├── ItemsPage.jsx
│   │       ├── SignInPage.jsx
│   │       └── SignUpPage.jsx
│   ├── public/
│   ├── Dockerfile
│   ├── Caddyfile
│   └── package.json
│
├── infra/
│   ├── single-vm/
│   │   ├── docker-compose.yml
│   │   ├── caddy/Caddyfile
│   │   ├── scripts/
│   │   └── .env.example
│   └── cloud/
│       └── *.tf
│
├── docker-compose.yml           # Local dev
├── .env.example
├── .gitignore
├── README.md
└── CLAUDE.md
```

---

## Deployment Checklist

### Before First Deployment

- [ ] Generate secure `SECRET_KEY` with `openssl rand -base64 64`
- [ ] Set strong `POSTGRES_PASSWORD`
- [ ] Configure `DOMAIN_NAME` with DNS pointing to VM
- [ ] Set `CADDY_EMAIL` for SSL certificate notifications
- [ ] Review CORS settings in `CORS_ALLOWED_ORIGINS`

### VM Setup

```bash
# 1. SSH to VM
ssh user@your-vm-ip

# 2. Clone repository
git clone <repo-url>
cd my-project

# 3. Install Docker (if needed)
sudo ./infra/single-vm/scripts/install-docker.sh
# Log out and back in for docker group

# 4. Configure environment
cd infra/single-vm
cp .env.example .env
nano .env  # Edit settings

# 5. Deploy
./scripts/deploy.sh

# 6. Verify
./scripts/manage.sh health
./scripts/manage.sh status
```

### Post-Deployment

```bash
# View logs
./scripts/manage.sh logs

# Check resource usage
./scripts/manage.sh stats

# Create database backup
./scripts/manage.sh backup

# Update application
./scripts/manage.sh update
```

---

## Common Patterns

### Adding a New Feature

1. Create backend models and migrations
2. Create API endpoints in a new router
3. Register router in `main.py`
4. Create frontend components/pages
5. Add API calls to frontend
6. Test locally with `docker compose up`
7. Deploy with `./scripts/manage.sh update`

### Adding External Services

Update `docker-compose.yml` and `infra/single-vm/docker-compose.yml`:

```yaml
# Redis for caching/sessions
redis:
  image: redis:7-alpine
  profiles:
    - cache
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]

# MinIO for object storage
minio:
  image: minio/minio
  profiles:
    - storage
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: ${MINIO_USER}
    MINIO_ROOT_PASSWORD: ${MINIO_PASSWORD}
```

### Adding Background Tasks

1. **Install Celery**:

```
celery[redis]==5.4.0
```

2. **Create worker** at `backend/app/worker.py`:

```python
from celery import Celery
from app.config import settings

celery = Celery("tasks", broker=settings.REDIS_URL)

@celery.task
def process_data(data_id: int):
    # Long-running task
    pass
```

3. **Add worker service** to `docker-compose.yml`:

```yaml
worker:
  build:
    context: ./backend
    target: production
  command: celery -A app.worker worker --loglevel=info
  depends_on:
    - redis
    - postgres
```

---

## Troubleshooting

### Container won't start

```bash
# Check logs
./scripts/manage.sh logs-backend
./scripts/manage.sh logs-frontend

# Check health
./scripts/manage.sh health

# Rebuild from scratch
./scripts/manage.sh clean
./scripts/deploy.sh --build
```

### Database connection issues

```bash
# Check PostgreSQL is running
./scripts/manage.sh logs-db

# Connect to database shell
./scripts/manage.sh shell-db

# Verify connection string in .env
echo $DATABASE_URL
```

### SSL certificate not working

```bash
# Check Caddy logs
./scripts/manage.sh logs-caddy

# Verify domain DNS
dig +short your-domain.com

# Ensure ports 80/443 are open
sudo ufw allow 80
sudo ufw allow 443
```

### Authentication issues

```bash
# Check if backend is receiving requests
./scripts/manage.sh logs-backend

# Test auth endpoint directly
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password"}'
```

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [Vite Documentation](https://vitejs.dev/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Caddy Documentation](https://caddyserver.com/docs/)
- [SQLAlchemy Async](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
