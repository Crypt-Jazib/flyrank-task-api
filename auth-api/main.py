import os
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Server running and connected to Supabase")

app = FastAPI(
    title="Auth Login & Protect API",
    description="Secure authentication and route protection with FastAPI and Supabase Auth.",
    version="1.0.0",
)


@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)})


class AuthRequest(BaseModel):
    email: str | None = None
    password: str | None = None


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise HTTPException(status_code=401, detail={"error": "Access token required"})

    token = credentials.credentials.strip()
    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail={"error": "Invalid or expired token"})
        return {"user": user_response.user, "token": token}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail={"error": "Invalid or expired token"})


@app.get("/")
def root():
    return {"status": "Server running and connected to Supabase"}


@app.post("/auth/signup", status_code=201)
def signup(payload: AuthRequest):
    if not payload.email or not payload.email.strip() or not payload.password or not payload.password.strip():
        raise HTTPException(status_code=400, detail={"error": "Email and password are required"})

    try:
        res = supabase.auth.sign_up({"email": payload.email.strip(), "password": payload.password})
        if not res.user:
            raise HTTPException(status_code=400, detail={"error": "User registration failed"})
        return {
            "id": res.user.id,
            "email": res.user.email,
            "created_at": str(res.user.created_at),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail={"error": str(exc)})


@app.post("/auth/login")
def login(payload: AuthRequest):
    if not payload.email or not payload.email.strip() or not payload.password or not payload.password.strip():
        raise HTTPException(status_code=400, detail={"error": "Email and password are required"})

    try:
        res = supabase.auth.sign_in_with_password({"email": payload.email.strip(), "password": payload.password})
        if not res.session:
            raise HTTPException(status_code=401, detail={"error": "Invalid login credentials"})
        return {
            "access_token": res.session.access_token,
            "refresh_token": res.session.refresh_token,
            "token_type": "bearer",
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail={"error": "Invalid login credentials"})


@app.post("/auth/logout", status_code=204)
def logout(auth_data: dict = Depends(get_current_user)):
    try:
        supabase.auth.admin.sign_out(auth_data["token"])
    except Exception:
        pass
    return Response(status_code=204)


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def protected_profile(auth_data: dict = Depends(get_current_user)):
    user = auth_data["user"]
    return {
        "id": user.id,
        "email": user.email,
        "created_at": str(user.created_at),
        "role": user.role,
    }


@app.get("/protected/dashboard")
def protected_dashboard(auth_data: dict = Depends(get_current_user)):
    user = auth_data["user"]
    return {
        "message": f"Welcome to your protected dashboard, {user.email}!",
        "user_id": user.id,
    }