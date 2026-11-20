# Auth Login & Protect API

A secure authentication and route-protection REST API built with **FastAPI** and **Supabase Auth**. It handles user registration, login with JWT issuance, token verification via a reusable FastAPI `HTTPBearer` dependency, session logout, and interactive Swagger UI Bearer authorization.

## Tech Stack
- **Language / Framework:** Python 3.10+, FastAPI, Uvicorn
- **Identity Provider:** Supabase Auth (`supabase` Python SDK)
- **Configuration:** `python-dotenv`
- **API Docs:** Swagger UI (`/docs`) with `HTTPBearer` security scheme

## Project Structure
```text
flyrank-auth-api/
├── main.py             # FastAPI app, Supabase client, auth routes, HTTPBearer dependency
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .gitignore          # Excludes .env, .venv/, and __pycache__/
├── swagger-ui.png      # Screenshot of Swagger UI with Bearer authorization
└── README.md           # Project documentation