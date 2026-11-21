# OncoLens React + FastAPI

React frontend and FastAPI backend for the existing gene-expression Random Forest classifier. The saved model, feature list, metrics and supplied visualisations are carried over unchanged from the Streamlit version.

## Requirements
- Python 3.11+ for the backend
- Node.js 20+ and npm for the frontend
- Docker Desktop (optional, for the production-like combined run)

## Run locally (two terminals)

### 1. Backend
```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
API docs: http://127.0.0.1:8000/docs

### 2. Frontend
Open a second terminal:
```powershell
cd frontend
npm install
npm run dev
```
Open the Vite URL, normally http://localhost:5173.

## Run both with Docker
From the project root:
```powershell
docker compose up --build
```
Open http://localhost. Stop with `Ctrl+C`, then optionally run `docker compose down`.

## Deploy on Vultr
1. Create a Vultr Ubuntu VPS with Docker Engine and the Docker Compose plugin installed.
2. Copy this project folder to the VPS.
3. From the project root, run `docker compose up -d --build`.
4. Allow inbound TCP port 80 in the Vultr firewall. Add HTTPS with a domain and a reverse proxy/TLS certificate before public production use.

## API
- `GET /api/health`
- `GET /api/metadata`
- `POST /api/predict` with multipart form field `file` containing a CSV.

## Important
OncoLens is an experimental research and educational prototype. It is not clinically validated and must not be used for diagnosis or treatment decisions. Model confidence scores are not clinical probabilities. Validate data provenance, split methodology, potential leakage and external performance before making model-performance claims.
