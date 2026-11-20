import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Server running and connected to Supabase")

app = FastAPI(title="Auth Login & Protect API", version="1.0.0")


@app.get("/")
def root():
    return {"status": "Server running and connected to Supabase"}


@app.post("/auth/signup", status_code=201)
async def signup(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    email = body.get("email")
    password = body.get("password")

    if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password.strip():
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    try:
        res = supabase.auth.sign_up({"email": email.strip(), "password": password})
        if not res.user:
            return JSONResponse(status_code=400, content={"error": "User registration failed"})
        return {
            "id": res.user.id,
            "email": res.user.email,
            "created_at": str(res.user.created_at),
        }
    except Exception as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})


@app.post("/auth/login")
async def login(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    if not isinstance(body, dict):
        return JSONResponse(status_code=400, content={"error": "Request body must be a JSON object"})

    email = body.get("email")
    password = body.get("password")

    if not isinstance(email, str) or not email.strip() or not isinstance(password, str) or not password.strip():
        return JSONResponse(status_code=400, content={"error": "Email and password are required"})

    try:
        res = supabase.auth.sign_in_with_password({"email": email.strip(), "password": password})
        if not res.session:
            return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})
        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "token_type": "bearer",
        }
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Invalid login credentials"})


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def protected_profile(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return JSONResponse(status_code=401, content={"error": "Access token required"})

    token = auth_header.removeprefix("Bearer ").strip()
    if not token:
        return JSONResponse(status_code=401, content={"error": "Access token required"})

    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            return JSONResponse(status_code=401, content={"error": "Invalid or expired token"})
        user = user_response.user
        return {
            "id": user.id,
            "email": user.email,
            "created_at": str(user.created_at),
            "role": user.role,
        }
    except Exception:
        return JSONResponse(status_code=401, content={"error": "Invalid or expired token"})