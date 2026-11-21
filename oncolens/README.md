@'
# OncoLens — Containerized Gene-Expression Classification Capstone

**OncoLens** is a full-stack bioinformatics prototype that classifies multi-sample gene-expression CSV datasets across five cancer categories (`BRCA`, `COAD`, `KIRC`, `LUAD`, `PRAD`) using a trained 20,531-feature Random Forest classifier, wrapped in a containerized FastAPI + React architecture.

> **Research Disclaimer:** Research prototype only. Outputs are experimental, not clinically validated, and must not be used for clinical diagnosis or treatment decisions.

## Implemented Capstone Concepts (6/5 Required)
1. **REST API Endpoints (`FastAPI`):** `GET /api/health`, `GET /api/metadata`, `POST /api/auth/login`, `POST /api/predict` (up to 200 MB CSV uploads), `GET /api/history`, and `GET /api/runs/{run_id}/report.pdf`.
2. **Relational Database (`SQLite`):** Persists every analysis run (`filename`, `file_hash`, `samples_analysed`, `class_distribution`, `results_json`, `created_by`, `created_at`) in `oncolens.db`.
3. **Authentication (`HTTPBearer` Token Auth):** Protects prediction, history, and PDF reporting routes behind Bearer token authentication with a one-click **Researcher Sign In** flow in the UI.
4. **Content-Addressable Caching (`SHA-256`):** Hashes every uploaded CSV dataset; identical datasets return cached predictions from SQLite immediately without re-running Random Forest inference.
5. **Automated PDF Reporting (`fpdf2`):** Generates downloadable multi-section bioinformatics summary PDF reports per analysis run.
6. **Containerized Deployment (`Docker Compose`):** Multi-container orchestration (`oncolens-backend` + Nginx-served `oncolens-frontend`) booting with a single command.
