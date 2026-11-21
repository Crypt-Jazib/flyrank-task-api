from datetime import datetime, timezone
import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import secrets
import sqlite3

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF
import joblib
import numpy as np
import pandas as pd
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parent
MODEL_DIR = ROOT / "models"
ASSET_DIR = ROOT / "assets"
DB_PATH = Path(os.getenv("ONCOLENS_DB_PATH", str(ROOT / "oncolens.db")))

DEMO_USERNAME = os.getenv("ONCOLENS_USER", "researcher@oncolens.bio")
DEMO_PASSWORD = os.getenv("ONCOLENS_PASSWORD", "oncolens2026")
ACTIVE_TOKENS: dict[str, str] = {}

security = HTTPBearer(auto_error=False)

app = FastAPI(
    title="OncoLens Capstone API",
    version="2.0.0",
    description="Containerized bioinformatics gene-expression classification API with SQLite persistence, SHA-256 caching, Bearer auth, and PDF reporting.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000", "http://localhost"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=ASSET_DIR), name="assets")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                samples_analysed INTEGER NOT NULL,
                class_distribution TEXT NOT NULL,
                results_json TEXT NOT NULL,
                created_by TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_hash ON analysis_runs(file_hash)")


init_db()

try:
    model = joblib.load(MODEL_DIR / "oncolens_random_forest.joblib")
    feature_columns = list(joblib.load(MODEL_DIR / "feature_columns.joblib"))
    with open(MODEL_DIR / "metrics.json", encoding="utf-8") as f:
        metrics = json.load(f)
    gene_importance = pd.read_csv(MODEL_DIR / "gene_importance.csv")
except Exception as exc:
    raise RuntimeError(f"Could not load OncoLens model files: {exc}") from exc

if not feature_columns:
    raise RuntimeError("The saved feature list is empty.")


class LoginRequest(BaseModel):
    email: str
    password: str


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Bearer token. Log in via /api/auth/login first.",
        )
    user = ACTIVE_TOKENS.get(credentials.credentials)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid token. Please log in again.",
        )
    return user


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    if payload.email.strip().lower() != DEMO_USERNAME.lower() or payload.password != DEMO_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid researcher credentials.")
    token = secrets.token_urlsafe(32)
    ACTIVE_TOKENS[token] = payload.email.strip().lower()
    return {"access_token": token, "token_type": "bearer", "user": ACTIVE_TOKENS[token]}


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "database_ready": DB_PATH.exists(),
    }


@app.get("/api/metadata")
def metadata():
    top_genes = gene_importance.head(20).to_dict(orient="records")
    return {
        "classifier": "Random Forest",
        "gene_features": len(feature_columns),
        "dataset_samples": metrics.get("dataset_samples"),
        "train_samples": metrics.get("train_samples"),
        "test_samples": metrics.get("test_samples"),
        "accuracy": metrics.get("accuracy"),
        "macro_f1": metrics.get("macro_f1"),
        "classes": metrics.get("classes", []),
        "n_estimators": metrics.get("n_estimators"),
        "top_genes": top_genes,
    }


@app.get("/api/history")
def list_history(user: str = Depends(require_user)):
    with get_db() as conn:
        rows = conn.execute(
            """
            SELECT id, filename, file_hash, samples_analysed, class_distribution, created_by, created_at
            FROM analysis_runs
            ORDER BY id DESC
            LIMIT 25
            """
        ).fetchall()
    return [
        {
            "run_id": r["id"],
            "filename": r["filename"],
            "file_hash": r["file_hash"][:12],
            "samples_analysed": r["samples_analysed"],
            "class_distribution": json.loads(r["class_distribution"]),
            "created_by": r["created_by"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@app.post("/api/predict")
async def predict(file: UploadFile = File(...), user: str = Depends(require_user)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="The uploaded CSV is empty.")
    if len(raw) > 200 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File is larger than the 200 MB upload limit.")

    file_hash = hashlib.sha256(raw).hexdigest()

    with get_db() as conn:
        cached_row = conn.execute(
            """
            SELECT id, samples_analysed, class_distribution, results_json, created_at
            FROM analysis_runs
            WHERE file_hash = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (file_hash,),
        ).fetchone()

    if cached_row:
        return {
            "run_id": cached_row["id"],
            "filename": file.filename,
            "file_hash": file_hash[:12],
            "cached": True,
            "samples_analysed": cached_row["samples_analysed"],
            "class_distribution": json.loads(cached_row["class_distribution"]),
            "results": json.loads(cached_row["results_json"]),
        }

    try:
        data = pd.read_csv(BytesIO(raw))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read CSV: {exc}") from exc
    if data.empty:
        raise HTTPException(status_code=400, detail="The CSV contains no data rows.")
    if data.columns.duplicated().any():
        duplicates = data.columns[data.columns.duplicated()].tolist()
        raise HTTPException(status_code=400, detail=f"Duplicate column names found: {', '.join(map(str, duplicates[:8]))}")

    missing = [name for name in feature_columns if name not in data.columns]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"{len(missing):,} required gene features are missing. Examples: {', '.join(map(str, missing[:10]))}",
        )

    X = data.loc[:, feature_columns].apply(pd.to_numeric, errors="coerce")
    if X.isna().any().any():
        bad = X.columns[X.isna().any()].tolist()
        raise HTTPException(status_code=400, detail="Missing or non-numeric values found in: " + ", ".join(map(str, bad[:10])))
    if not np.isfinite(X.to_numpy()).all():
        raise HTTPException(status_code=400, detail="Infinite values were found in the gene-expression data.")

    try:
        predictions = model.predict(X)
        probabilities = model.predict_proba(X) if hasattr(model, "predict_proba") else None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc

    rows = []
    for index, prediction in enumerate(predictions):
        row = {"sample": f"Sample {index + 1}", "predicted_cancer_type": str(prediction)}
        if probabilities is not None:
            row["maximum_model_score"] = round(float(np.max(probabilities[index]) * 100), 2)
        rows.append(row)

    counts = pd.Series([str(x) for x in predictions]).value_counts().to_dict()
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO analysis_runs (filename, file_hash, samples_analysed, class_distribution, results_json, created_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (file.filename, file_hash, len(rows), json.dumps(counts), json.dumps(rows), user, created_at),
        )
        run_id = cur.lastrowid

    return {
        "run_id": run_id,
        "filename": file.filename,
        "file_hash": file_hash[:12],
        "cached": False,
        "samples_analysed": len(rows),
        "class_distribution": counts,
        "results": rows,
    }


@app.get("/api/runs/{run_id}/report.pdf")
def download_pdf_report(run_id: int, user: str = Depends(require_user)):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM analysis_runs WHERE id = ?", (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Analysis run not found.")

    distribution = json.loads(row["class_distribution"])
    results = json.loads(row["results_json"])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 10, "OncoLens Gene-Expression Analysis Report", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(
        0,
        6,
        "Research prototype only. Outputs are experimental and must not be used for clinical diagnosis.",
        new_x="LMARGIN",
        new_y="NEXT",
    )
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Run Metadata", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    meta_lines = [
        f"Run ID: #{row['id']}",
        f"Dataset Filename: {row['filename']}",
        f"SHA-256 Digest: {row['file_hash'][:16]}...",
        f"Samples Analysed: {row['samples_analysed']}",
        f"Analysed By: {row['created_by']}",
        f"Timestamp (UTC): {row['created_at']}",
    ]
    for line in meta_lines:
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Predicted Class Distribution", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    for cancer_type, count in distribution.items():
        pct = (count / row["samples_analysed"]) * 100 if row["samples_analysed"] else 0
        pdf.cell(0, 6, f"- {cancer_type}: {count} samples ({pct:.1f}%)", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, f"Sample Predictions (First {min(30, len(results))} of {len(results)})", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(45, 7, "Sample", border=1)
    pdf.cell(65, 7, "Predicted Type", border=1)
    pdf.cell(60, 7, "Max Model Score (%)", border=1, new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 9)
    for item in results[:30]:
        score = f"{item['maximum_model_score']:.2f}%" if item.get("maximum_model_score") is not None else "N/A"
        pdf.cell(45, 6, str(item["sample"]), border=1)
        pdf.cell(65, 6, str(item["predicted_cancer_type"]), border=1)
        pdf.cell(60, 6, score, border=1, new_x="LMARGIN", new_y="NEXT")

    pdf_bytes = bytes(pdf.output())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="oncolens_run_{run_id}_report.pdf"'},
    )
