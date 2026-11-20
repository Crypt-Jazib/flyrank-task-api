import os
from dotenv import load_dotenv
from fastapi import FastAPI
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