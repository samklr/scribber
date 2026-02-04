# API Documentation Guide

This guide provides comprehensive information about the Project Template API, its endpoints, authentication, and how to use the interactive documentation.

## Table of Contents

- [Overview](#overview)
- [Interactive Documentation](#interactive-documentation)
- [Authentication](#authentication)
- [API Endpoints](#api-endpoints)
- [Using Swagger UI](#using-swagger-ui)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)

## Overview

The Project Template API is built with **FastAPI** and follows **RESTful** design principles. It provides:

- Self-hosted JWT authentication
- Automatic OpenAPI 3.0 documentation
- Interactive API testing via Swagger UI
- Comprehensive request/response validation
- Detailed error messages

**Base URL:**
- Local: `http://localhost:8000`
- Production: `https://api.yourdomain.com`

**API Version:** v1  
**Prefix:** `/api/v1` (for most endpoints)

## Interactive Documentation

### Documentation Endpoints

| URL | Description | Best For |
|-----|-------------|----------|
| `/docs` | **Swagger UI** - Interactive API testing | Development, testing, debugging |
| `/redoc` | **ReDoc** - Clean documentation view | Reading, reference, documentation |
| `/openapi.json` | **OpenAPI Schema** - Raw JSON spec | API clients, SDK generation |

### Swagger UI Features

Access at `http://localhost:8000/docs`

**Features:**
- ✨ **Try It Out** - Execute real API calls from the browser
- 🔐 **Authorization** - Test protected endpoints with JWT tokens
- 📝 **Examples** - Pre-filled request examples for quick testing
- 📊 **Schemas** - Interactive model visualization
- 🎨 **Syntax Highlighting** - Monokai theme for code examples
- 🔍 **Search** - Filter endpoints by keyword
- 💾 **Persistent Auth** - Your token is saved in the browser

## Authentication

### Authentication Flow

```mermaid
graph LR
    A[Register/Login] --> B[Receive JWT Token]
    B --> C[Include Token in Requests]
    C --> D[Access Protected Resources]
```

### Getting Started

#### 1. Register a New Account

**Endpoint:** `POST /api/v1/auth/register`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "name": "John Doe"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "name": "John Doe",
    "created_at": "2024-01-30T12:00:00"
  }
}
```

#### 2. Login (Existing Users)

**Endpoint:** `POST /api/v1/auth/login`

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response:** Same as registration

#### 3. Using the Token

Include the token in the `Authorization` header for protected endpoints:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token Lifetime:** 24 hours

## API Endpoints

### Health Checks

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/health/live` | GET | No | Liveness probe (is app running?) |
| `/health/ready` | GET | No | Readiness probe (ready for traffic?) |

**Use Cases:**
- Container orchestration (Docker, Kubernetes)
- Load balancer health checks
- Monitoring systems

### Authentication

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/auth/register` | POST | No | Create new account |
| `/api/v1/auth/login` | POST | No | Login and get token |
| `/api/v1/auth/me` | GET | Yes | Get current user info |
| `/api/v1/auth/logout` | POST | Yes | Logout (invalidate token) |

### Items (CRUD Example)

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/items` | GET | No | List all items |
| `/api/v1/items/{id}` | GET | No | Get item by ID |
| `/api/v1/items` | POST | No | Create new item |
| `/api/v1/items/{id}` | PUT | No | Update item |
| `/api/v1/items/{id}` | DELETE | No | Delete item |

**Note:** Items endpoints are currently public for demonstration. In production, you may want to add authentication requirements.

## Using Swagger UI

### Step-by-Step Tutorial

#### 1. Access Swagger UI

```bash
# Start the application
docker compose up -d

# Open in browser
http://localhost:8000/docs
```

#### 2. Register/Login

1. Locate the **Authentication** section
2. Expand `POST /api/v1/auth/register` (or `/login` if you have an account)
3. Click **"Try it out"**
4. Modify the example JSON:
   ```json
   {
     "email": "your-email@example.com",
     "password": "YourSecurePassword123!",
     "name": "Your Name"
   }
   ```
5. Click **"Execute"**
6. **Copy** the `access_token` from the response

#### 3. Authorize

1. Click the **"Authorize" button** (🔓) at the top of the page
2. In the popup, enter: `Bearer YOUR_TOKEN_HERE`
   - Example: `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
3. Click **"Authorize"**
4. Click **"Close"**

✅ You're now authenticated! All protected endpoints will automatically use your token.

#### 4. Test Protected Endpoints

1. Expand `GET /api/v1/auth/me`
2. Click **"Try it out"**
3. Click **"Execute"**
4. See your user information in the response

#### 5. Create, Update, Delete Items

Try the Items endpoints to see full CRUD operations:
- Create an item with `POST /api/v1/items`
- List all items with `GET /api/v1/items`
- Update with `PUT /api/v1/items/{id}`
- Delete with `DELETE /api/v1/items/{id}`

### Swagger UI Tips

**Pro Tips:**
- 💡 **Persist Authorization** - Your token is saved in the browser, so you don't need to re-enter it
- 🔄 **Reset** - Clear authorization by clicking "Logout" in the Authorize dialog
- 📋 **Copy Responses** - Click the "Copy" button on any response
- 🔍 **Filter** - Use the search box to find specific endpoints
- 🌐 **Server Selection** - Switch between development and production servers (if configured)

## Error Handling

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Successful GET, PUT requests |
| 201 | Created | Successful POST (resource created) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Invalid input data, validation errors |
| 401 | Unauthorized | Missing or invalid authentication token |
| 404 | Not Found | Resource doesn't exist |
| 422 | Unprocessable Entity | Request validation failed (Pydantic) |
| 500 | Internal Server Error | Unexpected server error |

### Error Response Format

```json
{
  "detail": "Item with ID 999 not found"
}
```

For validation errors (422):
```json
{
  "detail": [
    {
      "loc": ["body", "price"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

## Best Practices

### Security

1. **Always use HTTPS in production** - Caddy provides automatic SSL
2. **Rotate secrets regularly** - Change `SECRET_KEY` periodically
3. **Use strong passwords** - Minimum 8 characters, mix of types
4. **Never commit tokens** - Don't store JWT tokens in version control
5. **Token expiration** - Tokens expire after 24 hours, implement refresh if needed

### API Usage

1. **Check health endpoints** - Use `/health/ready` before making requests
2. **Handle errors gracefully** - Always check status codes
3. **Validate input** - The API validates, but client-side validation improves UX
4. **Rate limiting** - Consider adding rate limiting in production
5. **Pagination** - For large datasets, implement pagination (not in template)

### Development

1. **Use Swagger UI for testing** - Faster than curl or Postman during development
2. **Check OpenAPI schema** - Review `/openapi.json` for accurate API contracts
3. **Update examples** - Keep Swagger examples synchronized with actual usage
4. **Test error cases** - Try invalid inputs to see error responses
5. **Monitor logs** - Use `docker compose logs -f backend` during development

## Advanced Topics

### Generating API Clients

Use the OpenAPI schema to generate client libraries:

```bash
# Download schema
curl http://localhost:8000/openapi.json > openapi.json

# Generate TypeScript client
npx openapi-typescript-codegen --input openapi.json --output ./client

# Generate Python client
pip install openapi-python-client
openapi-python-client generate --url http://localhost:8000/openapi.json
```

### Postman Integration

1. Open Postman
2. Import → Link → Enter `http://localhost:8000/openapi.json`
3. Postman will create a collection with all endpoints

### Custom Headers

For additional functionality, you might add:
- `X-Request-ID` - Request tracking
- `X-API-Version` - API version pinning
- `Accept-Language` - Internationalization

### Extending the API

See `CLAUDE.md` for detailed instructions on:
- Adding new endpoints
- Creating database models
- Implementing middleware
- Adding authentication to endpoints

## Support

- **Documentation Issues:** Check `/docs` for the latest API reference
- **Code Examples:** See `CLAUDE.md` for implementation patterns
- **Deployment:** Refer to `README.md` for deployment instructions

---

**Generated by FastAPI's automatic OpenAPI integration**  
*Last Updated: 2024-01-30*
