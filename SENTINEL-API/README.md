# SENTINEL-API

## Setup & Run

```bash
# Backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (new terminal)
npm install
npm run dev

# CLI
python -m backend.cli.main --file path/to/openapi.yaml
python -m backend.cli.main --file "https://github.com/user/repo/blob/main/openapi.yaml"
```
