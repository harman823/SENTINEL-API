# SENTINEL-API

## Live Links

- Production App: `https://sentinel-api-tau.vercel.app`
- API Health Check: `https://sentinel-api-tau.vercel.app/api/health`

## Setup & Run

### 1. Environment Setup
```bash
# Setup Backend Environment
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Setup Frontend
npm install
```

### 2. Run Both Frontend & Backend
```bash
npm run dev
```
The command above uses `concurrently` to start both the Next.js frontend (3000) and the FastAPI backend (8000) in a single terminal.

### Other Commands
```bash
# Run Backend only
npm run dev:backend

# Run Frontend only
npm run dev:frontend

# CLI Usage
python -m backend.cli.main --file path/to/openapi.yaml
```
