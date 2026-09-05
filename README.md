# Ox Alpha OpenAI-Compatible LLM API Proxy

A production-ready, high-performance API reverse proxy built with **FastAPI**, **Uvicorn**, and **HTTPX** in Python 3.13. This service exposes standard OpenAI-compatible endpoints (`/v1/chat/completions`, `/v1/models`, and `/health`) backed by the upstream Ox Alpha web chat service (`https://oxalpha.com/api/chat`) running the `z-ai/glm-5.3-flash` model.

It allows you to plug the upstream model directly into any OpenAI-compatible application, UI, framework (such as LangChain, LlamaIndex, LiteLLM, Continue, Open WebUI), or the official OpenAI Python SDK.

---

## Architecture

```
Client (OpenAI SDK / curl / WebUI)
           │
           │  Authorization: Bearer <API_KEY>
           ▼
FastAPI Application Proxy (:8000 or $PORT)
 ├── Request ID Middleware (X-Request-ID propagation)
 ├── Access Logger (Sanitizes tokens, cookies & prompts)
 ├── Body Size Limiter (Rejects > 2MB payloads)
 ├── Bearer Authentication (Constant-time token validation)
 └── Sliding Window Rate Limiter (Configurable window/requests)
           │
           │  Session Warmup: GET https://oxalpha.com/chat
           │  Extracts: ox_alpha_session & XSRF-TOKEN
           ▼
Ox Alpha Web Upstream (POST https://oxalpha.com/api/chat)
 ├── Headers: X-XSRF-TOKEN, Origin, Referer, X-Context-Sent
 ├── 428 Precondition Required Automatic Recovery & 1-Retry
 └── Model: z-ai/glm-5.3-flash
           │
           │  Content-Type: text/event-stream (SSE)
           ▼
Proxy Streaming / Aggregation Engine
 ├── If stream=true  --> Yields OpenAI SSE chunks (data: {...}) + data: [DONE]
 └── If stream=false --> Consumes SSE stream, combines chunks, returns JSON
           │
           ▼
Client (OpenAI-compatible Response)
```

---

## Important Legal & Technical Disclaimer

> [!CAUTION]
> **Unofficial / Internal Upstream Notice**: The upstream endpoint (`https://oxalpha.com/api/chat`) is an internal web application endpoint utilized by the Ox Alpha web frontend. It is **NOT** an officially documented or contracted third-party developer API.
>
> Web application endpoints may change their internal protocols, session structures, CSRF token mechanics, rate limits, or anti-bot protections without prior notice.
>
> To mitigate disruption risks, this proxy decouples upstream configurations (`UPSTREAM_URL`, `UPSTREAM_MODEL`, `PUBLIC_MODEL_NAME`) into environment variables so the upstream provider can be swapped at any time.

---

## Features

- **Standard OpenAI Compatibility**:
  - `POST /v1/chat/completions` (full streaming & non-streaming support).
  - `GET /v1/models` (returns standard model cards for `glm-5.3-flash` and `z-ai/glm-5.3-flash`).
  - `GET /health` (unauthenticated monitoring endpoint).
- **Upstream Session & CSRF Automation**:
  - Automatically warms up upstream session (`GET /chat`).
  - Extracts and decodes `XSRF-TOKEN`.
  - Reuses HTTP connection pools and maintains cookies across requests.
- **Resilient 428 Handling**:
  - Detects `428 Precondition Required`.
  - Closes response, refreshes session and cookies, and retries the request once.
  - Returns a clean `502 Bad Gateway` if failure persists (strictly avoids infinite retry loops).
- **Production Security & Privacy**:
  - Bearer token authentication with timing-safe comparison (`secrets.compare_digest`).
  - Strict logging sanitizer: API keys, bearer headers, session cookies, and user prompts are never logged.
  - Request body size limiter (defaults to 2MB).
  - Sliding-window rate limiter per client IP.
- **Railway & Container Ready**:
  - Multi-stage / lightweight Python 3.13 Dockerfile.
  - Dynamically binds to `0.0.0.0:$PORT` provided by Railway at runtime.
  - Non-root user execution in container for security hardening.

---

## Project Structure

```
.
├── app/
│   ├── __init__.py           # Application package init
│   ├── main.py               # FastAPI factory, lifespan, middleware & error handlers
│   ├── config.py             # Pydantic Settings and env validation
│   ├── models.py             # OpenAI request, response, and SSE chunk schemas
│   ├── auth.py               # Bearer token verification dependency
│   ├── rate_limiter.py       # Thread-safe sliding window rate limiter
│   ├── upstream.py           # Ox Alpha session manager, CSRF, 428 retry & SSE handler
│   ├── routes.py             # API route endpoints
│   └── utils.py              # Sanitized logging, contextvars & SSE formatters
├── tests/
│   ├── __init__.py           # Test package init
│   ├── conftest.py           # Pytest fixtures and mock transport
│   ├── test_health.py        # /health tests
│   ├── test_auth.py          # Authentication tests
│   ├── test_models.py        # /v1/models tests
│   ├── test_completions.py   # Streaming, non-streaming & 428 retry tests
│   ├── test_rate_limit.py    # Rate limiter tests
│   ├── test_errors.py        # Validation and upstream error tests
│   └── verify_live.py        # Live server smoke test
├── examples/
│   └── client_demo.py        # OpenAI Python SDK usage example
├── .env.example              # Template environment variables
├── .gitignore                # Git ignore rules
├── requirements.txt          # Python dependencies
├── pytest.ini                # Pytest configuration
├── Dockerfile                # Production Docker container
├── railway.json              # Railway deployment configuration
└── README.md                 # Project documentation
```

---

## Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `API_KEY` | `change-this` | Secret key required in client `Authorization: Bearer <API_KEY>` |
| `UPSTREAM_URL` | `https://oxalpha.com` | Base URL of the Ox Alpha service |
| `UPSTREAM_MODEL` | `z-ai/glm-5.3-flash` | Upstream model identifier sent in `/api/chat` payload |
| `PUBLIC_MODEL_NAME` | `glm-5.3-flash` | Model identifier exposed publicly in `/v1/models` and responses |
| `RATE_LIMIT_REQUESTS` | `30` | Maximum number of requests allowed per window |
| `RATE_LIMIT_WINDOW` | `60` | Sliding window duration in seconds |
| `REQUEST_TIMEOUT` | `120` | Timeout in seconds for upstream requests |
| `MAX_REQUEST_BODY_SIZE` | `2097152` | Maximum incoming request body size in bytes (2MB) |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated or `*`) |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |
| `PORT` | `8000` | Port for Uvicorn (assigned dynamically by Railway or container) |

---

## Setup & Local Running

### Prerequisites
- Python 3.13+
- Git

### 1. Windows Setup (PowerShell)

```powershell
# Clone or navigate to the repository
cd d:\oxalpha

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt

# Create your .env file
Copy-Item .env.example .env
# Open .env and set your custom API_KEY
notepad .env

# Run unit tests
python -m pytest tests/ -v

# Start the server locally
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Linux / macOS Setup (Bash)

```bash
# Clone or navigate to the repository
cd /path/to/oxalpha

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create your .env file
cp .env.example .env
# Edit .env and set your custom API_KEY
nano .env

# Run unit tests
pytest tests/ -v

# Start the server locally
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## Testing

The test suite runs against mocked upstream transports without making live external network requests:

```bash
python -m pytest tests/ -v
```

To run the live endpoint smoke test on localhost:

```bash
python -m tests.verify_live
```

---

## Usage Examples

### 1. Check Health

```bash
curl http://127.0.0.1:8000/health
```

Output:
```json
{"status": "ok"}
```

---

### 2. List Models (cURL)

```bash
curl -X GET http://127.0.0.1:8000/v1/models \
  -H "Authorization: Bearer change-this"
```

Output:
```json
{
  "object": "list",
  "data": [
    {
      "id": "glm-5.3-flash",
      "object": "model",
      "created": 1700000000,
      "owned_by": "oxalpha-proxy"
    },
    {
      "id": "z-ai/glm-5.3-flash",
      "object": "model",
      "created": 1700000000,
      "owned_by": "oxalpha-proxy"
    }
  ]
}
```

---

### 3. Non-Streaming Chat Completion (cURL)

```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer change-this" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-5.3-flash",
    "messages": [
      {"role": "user", "content": "Explain quantum computing in one sentence."}
    ],
    "stream": false
  }'
```

Output:
```json
{
  "id": "chatcmpl-abc123456789",
  "object": "chat.completion",
  "created": 1741165000,
  "model": "glm-5.3-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Quantum computing uses quantum bits to perform complex calculations exponentially faster than classical computers for certain problems."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_tokens": 0
  }
}
```

---

### 4. Streaming Chat Completion (cURL)

```bash
curl -N -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Authorization: Bearer change-this" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "glm-5.3-flash",
    "messages": [
      {"role": "user", "content": "Count from 1 to 5."}
    ],
    "stream": true
  }'
```

Output:
```text
data: {"id":"chatcmpl-01","object":"chat.completion.chunk","created":1741165000,"model":"glm-5.3-flash","choices":[{"index":0,"delta":{"role":"assistant","content":"1, "},"finish_reason":null}]}

data: {"id":"chatcmpl-01","object":"chat.completion.chunk","created":1741165000,"model":"glm-5.3-flash","choices":[{"index":0,"delta":{"content":"2, "},"finish_reason":null}]}

data: {"id":"chatcmpl-01","object":"chat.completion.chunk","created":1741165000,"model":"glm-5.3-flash","choices":[{"index":0,"delta":{"content":"3, 4, 5."},"finish_reason":"stop"}]}

data: [DONE]
```

---

### 5. Official OpenAI Python SDK

Install the OpenAI client:
```bash
pip install openai
```

Run Python code:
```python
from openai import OpenAI

client = OpenAI(
    api_key="change-this",
    base_url="http://127.0.0.1:8000/v1" # Or your Railway domain: https://your-app.up.railway.app/v1
)

# 1. Non-Streaming Example
completion = client.chat.completions.create(
    model="glm-5.3-flash",
    messages=[
        {"role": "user", "content": "Hello! Introduce yourself."}
    ],
    stream=False
)
print("Non-streaming:", completion.choices[0].message.content)

# 2. Streaming Example
stream = client.chat.completions.create(
    model="glm-5.3-flash",
    messages=[
        {"role": "user", "content": "Write a short poem about the ocean."}
    ],
    stream=True
)

print("Streaming output:")
for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
```

---

## Deployment to Railway

The project includes a production `Dockerfile` and `railway.json` configured for zero-friction Railway deployment.

### Step-by-Step Railway Deployment:

1. **Push your code to a GitHub repository**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit of Ox Alpha LLM Proxy"
   git remote add origin https://github.com/<your-user>/<your-repo>.git
   git push -u origin main
   ```

2. **Create a new Project on Railway**:
   - Log into [Railway.app](https://railway.app/).
   - Click **New Project** -> **Deploy from GitHub repo**.
   - Select your repository.

3. **Configure Environment Variables in Railway**:
   Navigate to your service's **Variables** tab and configure:
   - `API_KEY`: Set your strong secret token (e.g., `sk-prod-xxxxxxx`).
   - `UPSTREAM_URL`: `https://oxalpha.com`
   - `UPSTREAM_MODEL`: `z-ai/glm-5.3-flash`
   - `PUBLIC_MODEL_NAME`: `glm-5.3-flash`
   - `RATE_LIMIT_REQUESTS`: `30`
   - `RATE_LIMIT_WINDOW`: `60`
   - `REQUEST_TIMEOUT`: `120`
   - `CORS_ORIGINS`: `*` (or your web application domain)

4. **Generate Public Domain**:
   - In Railway, go to **Settings** -> **Networking** -> **Generate Domain**.
   - You will receive a URL such as `https://oxalpha-proxy-production.up.railway.app`.

5. **Test Your Deployed Proxy**:
   ```bash
   curl https://oxalpha-proxy-production.up.railway.app/health
   ```

---

## Troubleshooting & Operational Resilience

### 1. Handling HTTP 428 Precondition Required
- **Cause**: Ox Alpha's backend enforces CSRF / session freshness via Laravel session cookies. If a session expires or token becomes out of sync, upstream returns `428 Precondition Required`.
- **Proxy Behavior**: The proxy automatically intercepts status `428`, immediately closes the connection, requests `GET /chat` to regenerate a fresh session and `XSRF-TOKEN`, and retries the chat completion once.
- **Persistent 428**: If upstream returns `428` a second time, the proxy stops retrying to prevent thrashing, logs the occurrence, and returns `502 Bad Gateway` with error code `upstream_precondition_failed`.

### 2. Upstream Outages / 5xx Errors
- When Ox Alpha returns 500/502/503/504, the proxy sanitizes the error, masks upstream infrastructure details, and returns an OpenAI-standard JSON error:
  ```json
  {
    "error": {
      "message": "Upstream provider error (HTTP 500)",
      "type": "upstream_error",
      "param": null,
      "code": "upstream_error"
    }
  }
  ```

### 3. Rate Limit (HTTP 429)
- By default, clients are limited to 30 requests per 60 seconds (configurable via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_WINDOW`).
- When exceeded, response returns HTTP 429 with header `Retry-After: <seconds>`:
  ```json
  {
    "error": {
      "message": "Rate limit exceeded. Limit is 30 requests per 60s. Try again in 15 seconds.",
      "type": "rate_limit_error",
      "param": null,
      "code": "rate_limit_exceeded"
    }
  }
  ```

### 4. Correlation IDs (`X-Request-ID`)
- Every request is tagged with a unique `X-Request-ID` (or adopts incoming `X-Request-ID`).
- Check server logs using `req_id=<uuid>` to trace specific transactions without exposing secret keys or user prompts.
