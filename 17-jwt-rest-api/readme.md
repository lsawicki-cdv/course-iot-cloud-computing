## JWT Token Authentication in REST API

**Important**: Before starting, check your Azure subscription's [Policy assignments](https://portal.azure.com/#view/Microsoft_Azure_Policy/PolicyMenuBlade.MenuView/~/Assignments) to verify which regions you can deploy resources to. If you plan to deploy this REST API to Azure (e.g., Azure App Service), your subscription may be limited to specific regions (typically 5 allowed regions). Use one of your allowed regions instead of UK South if necessary.

### Learning Objectives
- Understand JWT (JSON Web Tokens) and how they work
- Learn about stateless authentication in REST APIs
- Implement user authentication and authorization
- Secure API endpoints with JWT tokens
- Understand token expiration and refresh strategies
- Learn about Bearer token authentication

### Tested environments
Ubuntu 22.04
Python 3.10.12

### Background

#### What is JWT?
JWT (JSON Web Token) is an open standard (RFC 7519) for securely transmitting information between parties as a JSON object. JWTs are commonly used for authentication in modern web applications and APIs.

A JWT consists of three parts separated by dots (.):
- **Header**: Contains the token type (JWT) and signing algorithm (e.g., HS256)
- **Payload**: Contains the claims (user data, expiration time, etc.)
- **Signature**: Ensures the token hasn't been tampered with

Example: `xxxxx.yyyyy.zzzzz`

#### Why Use JWT?
Traditional session-based authentication stores session data on the server. JWT provides:
- **Stateless**: No server-side session storage needed
- **Scalable**: Works well with distributed systems and microservices
- **Cross-domain**: Can be used across different domains
- **Mobile-friendly**: Perfect for mobile apps and IoT devices
- **Self-contained**: Token contains all user information needed

#### How JWT Authentication Works
1. User sends credentials (username/password) to login endpoint
2. Server validates credentials
3. Server creates a JWT token containing user information
4. Server sends token back to user
5. User includes token in subsequent requests (Authorization header)
6. Server validates token and processes request

#### JWT Structure Example
```
Header (Base64):
{
  "alg": "HS256",
  "typ": "JWT"
}

Payload (Base64):
{
  "user_id": "123",
  "username": "john",
  "exp": 1735488000
}

Signature:
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  secret_key
)
```

### Exercise

In this exercise, you will:
1. Create a REST API with Flask
2. Implement user registration and login
3. Generate JWT tokens on successful login
4. Protect API endpoints with JWT authentication
5. Test the API with a Python client

#### Prerequisites
1. Python 3.10+ installed
2. Basic understanding of REST APIs
3. Familiarity with HTTP methods (GET, POST, PUT, DELETE)

### Steps

#### 1. Setup Python Environment

On **macOS/Linux**:
```bash
cd 17-jwt-rest-api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

On **Windows**:
```powershell
cd 17-jwt-rest-api
py -m venv .venv
.venv\scripts\activate
pip install -r requirements.txt
```

#### 2. Configure the Application

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and set a secure secret key:
```
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_EXPIRATION_MINUTES=30
```

**Important**: In production, use a strong random secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

#### 3. Understand the API Structure

The API provides the following endpoints:

**Public Endpoints (No authentication required):**
- `POST /api/register` - Create a new user account
- `POST /api/login` - Login and receive JWT token
- `GET /api/health` - Check if API is running

**Protected Endpoints (JWT token required):**
- `GET /api/profile` - Get current user's profile
- `GET /api/sensors` - Get list of IoT sensors
- `POST /api/sensors` - Create a new sensor
- `GET /api/sensors/<id>/data` - Get sensor telemetry data
- `POST /api/sensors/<id>/data` - Add sensor telemetry data

#### 4. Run the REST API Server

Start the Flask server:
```bash
python app.py
```

The server will start on `http://localhost:5000`

You should see:
```
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

#### 5. Test with the Client Script

Open a **new terminal** (keep the server running), activate the virtual environment, and run the client:
```bash
source .venv/bin/activate  # or .venv\scripts\activate on Windows
python client_demo.py
```

The client will:
1. Register a new user
2. Login and receive JWT token
3. Access protected endpoints using the token
4. Create sensors and add telemetry data
5. Demonstrate token expiration

#### 6. Manual Testing with curl

You can also test manually with curl:

**Register a user:**
```bash
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123", "email": "test@example.com"}'
```

**Login:**
```bash
curl -X POST http://localhost:5000/api/login \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass123"}'
```

This returns a JWT token:
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 1800
}
```

**Access protected endpoint (replace YOUR_TOKEN with actual token):**
```bash
curl -X GET http://localhost:5000/api/profile \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Create a sensor:**
```bash
curl -X POST http://localhost:5000/api/sensors \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Temperature Sensor 1", "type": "temperature", "location": "Room 101"}'
```

#### 7. Understand JWT Token Structure

Decode your JWT token to see what's inside:
```bash
python decode_jwt.py YOUR_TOKEN
```

This shows:
- Header (algorithm and type)
- Payload (user info, expiration)
- Signature verification status

You can also use online tools like [jwt.io](https://jwt.io) to decode tokens (but never paste production tokens there!)

#### 8. Test Token Expiration

By default, tokens expire after 30 minutes. To test expiration:

1. Edit `.env` and set `JWT_EXPIRATION_MINUTES=1`
2. Restart the server
3. Login to get a token
4. Wait 61 seconds
5. Try to access a protected endpoint - you'll get "Token has expired"

#### 9. Understanding Security Best Practices

**What the API demonstrates:**
- Passwords are hashed (never stored in plain text)
- Tokens have expiration times
- Protected endpoints verify tokens before processing
- Secret key is stored in environment variables (not in code)

**Production considerations:**
- Use HTTPS (not HTTP) in production
- Store secret keys securely (e.g., Azure Key Vault)
- Implement token refresh mechanism
- Add rate limiting to prevent brute force attacks
- Use stronger password requirements
- Implement account lockout after failed attempts
- Log authentication attempts

### Questions to Consider

1. **What happens if someone steals my JWT token?**
   - They can impersonate you until the token expires
   - That's why short expiration times are important
   - HTTPS prevents tokens from being intercepted
   - Consider implementing token refresh/revocation

2. **How is JWT different from session-based authentication?**
   - Sessions: Server stores session data, client gets session ID
   - JWT: Client stores token with all info, server is stateless
   - JWT scales better for distributed systems
   - Sessions can be revoked immediately, JWTs cannot (until expiry)

3. **What's in the JWT payload?**
   - User identifier (user_id)
   - Username
   - Expiration time (exp)
   - Issued at time (iat)
   - Any other claims you want to include
   - Don't include sensitive data (passwords, credit cards)

4. **Can I modify the JWT token?**
   - No! The signature prevents tampering
   - If you change the payload, the signature won't match
   - Server will reject the token

5. **What is Bearer authentication?**
   - "Bearer" means "whoever holds this token"
   - Format: `Authorization: Bearer <token>`
   - Standard way to send tokens in HTTP headers

### Advanced Challenges

Want to go further? Try these:

1. **Add token refresh**: Implement a `/api/refresh` endpoint that issues new tokens
2. **Add roles**: Implement user roles (admin, user) and role-based access control
3. **Add database**: Replace in-memory storage with SQLite or PostgreSQL
4. **Deploy to Azure**: Deploy the API to Azure App Service
5. **Add IoT integration**: Connect this API to Azure IoT Hub from previous exercises
6. **Add rate limiting**: Use Flask-Limiter to prevent abuse
7. **Add Swagger docs**: Use Flask-RESTX to add API documentation

### Cleanup

When finished:
```bash
# Stop the server (CTRL+C in the server terminal)

# Deactivate virtual environment
deactivate
```

### Additional Resources

- [JWT Introduction](https://jwt.io/introduction)
- [RFC 7519 - JWT Standard](https://tools.ietf.org/html/rfc7519)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [REST API Best Practices](https://restfulapi.net/)

### Troubleshooting

**"Token has expired"**
- Generate a new token by logging in again
- Increase `JWT_EXPIRATION_MINUTES` in `.env` for testing

**"Invalid token"**
- Ensure you're sending the token in the correct format: `Bearer <token>`
- Check that the secret key matches between token generation and validation
- Verify the token wasn't corrupted when copying

**"Missing Authorization Header"**
- Protected endpoints require the Authorization header
- Format: `Authorization: Bearer <your-token>`

**"User already exists"**
- Use a different username for registration
- Or login with existing credentials
