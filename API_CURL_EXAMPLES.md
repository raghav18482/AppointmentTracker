# API cURL Examples for Frontend Integration

## Base URL
```
http://localhost:8000
```

## 1. Register User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

**Response:**
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## 2. Login User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "uuid-here",
  "business_id": "uuid-here-or-null"
}
```

**Note:** `business_id` will be `null` if the user is not associated with any business yet.

## 3. Get Current User (Protected)

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response:**
```json
{
  "id": "uuid-here",
  "email": "user@example.com",
  "is_active": true,
  "created_at": "2024-01-01T00:00:00",
  "updated_at": "2024-01-01T00:00:00"
}
```

## 4. Get User Role (Protected)

```bash
curl -X GET "http://localhost:8000/api/v1/auth/role" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE" \
  -H "X-Business-ID: YOUR_BUSINESS_ID_HERE"
```

**Response:**
```json
{
  "user_id": "uuid-here",
  "business_id": "uuid-here",
  "role": "owner",
  "business_name": "My Business"
}
```

**Note:** 
- Requires `X-Business-ID` header to specify which business to check
- Role can be: `owner`, `manager`, or `counter`
- Returns 404 if user is not associated with the specified business

## 5. Logout User (Protected)

```bash
curl -X POST "http://localhost:8000/api/v1/auth/logout" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN_HERE"
```

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

**Note:** After receiving this response, the client should remove the token from storage (localStorage, cookies, etc.).

## Frontend Integration Examples

### JavaScript/Fetch API

#### Register
```javascript
const registerUser = async (email, password) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: email,
      password: password
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Registration failed');
  }
  
  return await response.json();
};
```

#### Login
```javascript
const loginUser = async (email, password) => {
  const response = await fetch('http://localhost:8000/api/v1/auth/login', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      email: email,
      password: password
    })
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }
  
  const data = await response.json();
  // Store token in localStorage or state
  localStorage.setItem('access_token', data.access_token);
  // Store user_id and business_id if available
  if (data.user_id) {
    localStorage.setItem('user_id', data.user_id);
  }
  if (data.business_id) {
    localStorage.setItem('business_id', data.business_id);
  }
  return data;
};
```

#### Get Current User
```javascript
const getCurrentUser = async () => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('http://localhost:8000/api/v1/auth/me', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
  });
  
  if (!response.ok) {
    throw new Error('Failed to get user info');
  }
  
  return await response.json();
};
```

#### Get User Role
```javascript
const getUserRole = async (businessId) => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('http://localhost:8000/api/v1/auth/role', {
    method: 'GET',
    headers: {
      'Authorization': `Bearer ${token}`,
      'X-Business-ID': businessId,
      'Content-Type': 'application/json',
    }
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get user role');
  }
  
  return await response.json();
};
```

#### Logout
```javascript
const logoutUser = async () => {
  const token = localStorage.getItem('access_token');
  
  const response = await fetch('http://localhost:8000/api/v1/auth/logout', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    }
  });
  
  if (!response.ok) {
    throw new Error('Logout failed');
  }
  
  // Remove token and user data from storage after successful logout
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_id');
  localStorage.removeItem('business_id');
  
  return await response.json();
};
```

### Axios Example

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  }
});

// Add token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Register
const register = async (email, password) => {
  const response = await api.post('/auth/register', { email, password });
  return response.data;
};

// Login
const login = async (email, password) => {
  const response = await api.post('/auth/login', { email, password });
  localStorage.setItem('access_token', response.data.access_token);
  if (response.data.user_id) {
    localStorage.setItem('user_id', response.data.user_id);
  }
  if (response.data.business_id) {
    localStorage.setItem('business_id', response.data.business_id);
  }
  return response.data;
};

// Get current user
const getCurrentUser = async () => {
  const response = await api.get('/auth/me');
  return response.data;
};

// Get user role
const getUserRole = async (businessId) => {
  const response = await api.get('/auth/role', {
    headers: {
      'X-Business-ID': businessId
    }
  });
  return response.data;
};

// Logout
const logout = async () => {
  const response = await api.post('/auth/logout');
  // Remove token and user data from storage after successful logout
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_id');
  localStorage.removeItem('business_id');
  return response.data;
};
```

## Error Handling

All endpoints return errors in the following format:

```json
{
  "detail": "Error message here"
}
```

Common status codes:
- `200 OK` - Success
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid input (e.g., email already exists)
- `401 Unauthorized` - Invalid credentials or missing token
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

