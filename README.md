# Project Template

A production-ready template for deploying FastAPI + React applications using Docker with self-hosted authentication.

## Project Structure

```
project-template/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # Application entry point
│   │   ├── config.py          # Configuration management
│   │   └── routers/
│   │       ├── auth.py        # Authentication endpoints
│   │       ├── health.py      # Health checks
│   │       └── items.py       # Example CRUD
│   ├── Dockerfile             # Multi-stage Docker build
│   └── requirements.txt       # Python dependencies
│
├── frontend/                   # React + Vite frontend
│   ├── src/
│   │   ├── App.jsx            # Main component with routing
│   │   ├── context/           # Auth context
│   │   ├── components/        # Reusable components
│   │   └── pages/             # Page components
│   ├── Dockerfile             # Multi-stage Docker build
│   ├── Caddyfile              # Static file server config
│   └── package.json           # Node dependencies
│
├── infra/
│   ├── single-vm/             # Single VM deployment
│   │   ├── docker-compose.yml # Production stack
│   │   ├── caddy/             # Reverse proxy config
│   │   └── scripts/           # Management scripts
│   │       ├── deploy.sh      # Automated deployment
│   │       ├── manage.sh      # Service management
│   │       └── status.sh      # Health monitoring
│   │
│   └── cloud/                 # Cloud infrastructure (Terraform)
│       ├── main.tf
│       └── variables.tf
│
├── docker-compose.yml         # Local development
└── .env.example               # Environment template
```

## Quick Start

### Local Development

1. **Copy environment file:**
   ```bash
   cp .env.example .env
   ```

2. **Start services:**
   ```bash
   docker compose up -d
   ```

3. **Access the application:**
   - Frontend: http://localhost:5173 (redirects to sign-in)
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

4. **Create an account** and start using the app!

### Single VM Deployment

1. **SSH to your VM and clone the repository:**
   ```bash
   git clone <repo-url>
   cd project-template
   ```

2. **Install Docker (if needed):**
   ```bash
   sudo ./infra/single-vm/scripts/install-docker.sh
   ```

3. **Configure environment:**
   ```bash
   cd infra/single-vm
   cp .env.example .env
   nano .env  # Edit with your settings
   ```

4. **Deploy:**
   ```bash
   ./scripts/deploy.sh
   ```

5. **Manage services:**
   ```bash
   ./scripts/manage.sh status    # Check status
   ./scripts/manage.sh logs      # View logs
   ./scripts/manage.sh health    # Health check
   ./scripts/manage.sh backup    # Backup database
   ```

## Features

### Backend (FastAPI)
- **Self-hosted authentication** with JWT tokens and bcrypt password hashing
- **Comprehensive OpenAPI documentation** with Swagger UI and ReDoc
- **Interactive API testing** directly from the browser
- Health check endpoints (`/health/live`, `/health/ready`)
- CORS configuration via environment
- Pydantic settings management
- Multi-stage Docker build (development/production)

### Frontend (React + Vite)
- Modern React 18 with hooks
- **Built-in authentication** (sign-in, sign-up, protected routes)
- React Router for navigation
- Auth context for state management
- Vite for fast development
- Multi-stage Docker build with Caddy

### Infrastructure
- **Caddy** reverse proxy with automatic SSL
- **PostgreSQL** database with health checks
- Profile-based Docker Compose (local-db, tools, cache)
- Comprehensive management scripts

## API Documentation

The template includes **professional-grade API documentation** powered by FastAPI's automatic OpenAPI generation:

### Swagger UI (`/docs`)

Interactive API documentation with a modern interface:

- **🔐 Built-in authentication testing** - Click the "Authorize" button to add your JWT token
- **📝 Detailed examples** - Every endpoint includes request/response examples
- **🎯 Try it out** - Execute API calls directly from your browser
- **📊 Schema visualization** - Explore request/response models with interactive schemas
- **🎨 Syntax highlighting** - Code examples with beautiful Monokai theme
- **🔖 Organized by tags** - Endpoints grouped by functionality (Authentication, Items, Health)

#### How to use Swagger UI:

1. **Start the backend:**
   ```bash
   docker compose up -d
   ```

2. **Open Swagger UI:**
   - Visit http://localhost:8000/docs

3. **Test authentication:**
   - Expand `POST /api/v1/auth/register`
   - Click "Try it out"
   - Fill in the example data (or customize it)
   - Click "Execute"
   - Copy the `access_token` from the response

4. **Authorize:**
   - Click the "Authorize" button (🔓 icon at the top)
   - Enter: `Bearer <your_token>` (replace `<your_token>` with your actual token)
   - Click "Authorize"

5. **Test protected endpoints:**
   - Try `GET /api/v1/auth/me` to see your user info
   - All protected endpoints will now use your token automatically!

### ReDoc (`/redoc`)

Alternative documentation view with:
- Clean, document-style layout
- Better for reading and reference
- Printable format
- Three-panel layout (menu, content, schema)

### OpenAPI Schema (`/openapi.json`)

Raw OpenAPI 3.0 specification in JSON format:
- Import into Postman, Insomnia, or other API clients
- Generate client SDKs in any language
- Use for API testing frameworks

### Documentation Features

✅ **Comprehensive endpoint descriptions** with usage notes  
✅ **Request/response examples** for every endpoint  
✅ **Field-level documentation** with constraints and types  
✅ **Security scheme documentation** for JWT authentication  
✅ **Error response examples** (400, 401, 404, etc.)  
✅ **Model schemas** with validation rules  
✅ **Best practices** and production recommendations  


## Authentication

The template includes a complete self-hosted authentication system:

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/register` | POST | Create new account |
| `/api/v1/auth/login` | POST | Sign in and get token |
| `/api/v1/auth/me` | GET | Get current user (protected) |
| `/api/v1/auth/logout` | POST | Sign out (protected) |

### Frontend Pages

- `/sign-in` - Login page
- `/sign-up` - Registration page
- `/` - Home (protected)
- `/items` - Items CRUD (protected)

### Using Auth in Components

```jsx
import { useAuth } from './context/AuthContext'

function MyComponent() {
  const { user, signIn, signOut, getAuthHeader } = useAuth()

  // Make authenticated API calls
  const fetchData = async () => {
    const response = await fetch('/api/v1/protected', {
      headers: getAuthHeader()
    })
  }

  return <div>Hello, {user?.name}!</div>
}
```

## Environment Variables

### Required (Production)
| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | JWT signing key (generate with `openssl rand -base64 64`) |
| `POSTGRES_PASSWORD` | Database password |
| `DOMAIN_NAME` | Domain for SSL |

### Optional
| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_MODE` | `local` | `local` or `remote` |
| `POSTGRES_USER` | `appuser` | Database user |
| `POSTGRES_DB` | `app_db` | Database name |
| `CADDY_EMAIL` | `admin@localhost` | SSL cert email |

## Management Commands

```bash
# Service control
./manage.sh start           # Start services
./manage.sh stop            # Stop services
./manage.sh restart         # Restart all
./manage.sh update          # Pull, rebuild, restart

# Monitoring
./manage.sh status          # Container status
./manage.sh health          # Health checks
./manage.sh stats           # Resource usage
./manage.sh logs            # All logs
./manage.sh logs-backend    # Backend logs

# Database
./manage.sh backup          # Create backup
./manage.sh restore         # Restore backup
./manage.sh shell-db        # PostgreSQL shell

# Maintenance
./manage.sh clean           # Remove all containers
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Root info |
| `/health/live` | GET | Liveness probe |
| `/health/ready` | GET | Readiness probe |
| `/api/v1/auth/*` | * | Authentication |
| `/api/v1/items` | GET | List items |
| `/api/v1/items/{id}` | GET | Get item |
| `/api/v1/items` | POST | Create item |
| `/api/v1/items/{id}` | PUT | Update item |
| `/api/v1/items/{id}` | DELETE | Delete item |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc |

## Security Notes

1. **Generate secure keys:**
   ```bash
   openssl rand -base64 64
   ```

2. **Never commit `.env` files**

3. **Use HTTPS in production** (Caddy handles this automatically)

4. **Rotate secrets regularly**

5. **Passwords are hashed with bcrypt** - never stored in plain text

## License

MIT
